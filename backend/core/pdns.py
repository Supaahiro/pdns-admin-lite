"""Thin async client for the PowerDNS Authoritative REST API.

All upstream failures are raised as PdnsError; a single FastAPI exception
handler (see main.py) turns them into JSON error responses. Client-attributable
upstream statuses (400/404/409/422) pass through unchanged, anything else —
including auth/config problems and network failures — surfaces as 502.

PolicyError is PdnsError's sibling for failures that never reach PowerDNS at
all (auth, zone protection): same {detail, code} shape, same exception
handler, distinct type so the frontend can eventually branch differently.
"""

import re

import httpx

PASSTHROUGH_STATUSES = {400, 404, 409, 422}

# One or more LDH labels, each 1-63 chars, dot-terminated. Rejects raw
# Unicode by construction (the char class is ASCII-only) — punycode
# (xn--...) passes through as an ordinary LDH label.
_LDH_ZONE_RE = re.compile(r"([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.)+")


class PdnsError(Exception):
    def __init__(self, status_code: int, detail: str, code: str = "pdns_error") -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail
        self.code = code


class PolicyError(Exception):
    """Raised by locally-enforced policy (auth, zone protection), not PowerDNS."""

    def __init__(self, status_code: int, detail: str, code: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail
        self.code = code


def canonicalize(name: str, zone_id: str) -> str:
    """Turn a record name into the FQDN (trailing dot) PowerDNS expects.

    "@" or the empty string mean the zone apex; a name already ending with a
    dot is taken as-is; a name already ending with the zone is only given the
    trailing dot; anything else is treated as relative to the zone.
    """
    zone_fqdn = zone_id if zone_id.endswith(".") else f"{zone_id}."
    zone_bare = zone_fqdn.rstrip(".")
    name = name.strip()
    if name in ("", "@"):
        return zone_fqdn
    if name.endswith("."):
        return name
    if name == zone_bare or name.endswith(f".{zone_bare}"):
        return f"{name}."
    return f"{name}.{zone_fqdn}"


def canonical_zone(name: str) -> str:
    """Lowercase, stripped, exactly one trailing dot.

    'EXAMPLE.TEST' -> 'example.test.'; 'example.test..' -> 'example.test.'.
    Used everywhere a zone name is compared for protection: a Unicode
    homoglyph canonicalizes to a different string and therefore names a
    different (and non-LDH, so uncreatable) zone, not the protected one.
    """
    return name.strip().rstrip(".").lower() + "."


def _is_subzone_of_protected(zone: str, protected_zones: set[str]) -> bool:
    """True for a strict child of a protected zone, false for an exact match."""
    return any(zone.endswith(f".{p}") for p in protected_zones)


def is_protected_zone(zone_id: str, protected_zones: set[str]) -> bool:
    return canonical_zone(zone_id) in protected_zones


def ensure_zone_mutable(zone_id: str, protected_zones: set[str]) -> None:
    """Guards zone-level destructive ops: deleting a protected zone or any of
    its subzones (a delegated child is part of the protected estate; it was
    provisioned outside this tool and is removed the same way)."""
    zone = canonical_zone(zone_id)
    if zone in protected_zones or _is_subzone_of_protected(zone, protected_zones):
        raise PolicyError(403, f"Zone {zone} is protected", code="zone_protected")


def ensure_zone_creatable(name: str, protected_zones: set[str]) -> None:
    """Guards zone creation: only subzones of a protected zone are refused.

    Creating the protected zone's exact name is left to PowerDNS's own 409 —
    the protected zone is assumed to already exist (it is the real zone the
    homelab resolves against), so this never shadows it.
    """
    if _is_subzone_of_protected(name, protected_zones):
        raise PolicyError(
            403,
            f"Zone {name} is nested under a protected zone and cannot be created",
            code="zone_protected",
        )


def validate_zone_name(name: str) -> str:
    """Canonicalizes and validates a zone name for creation.

    LDH syntax only and <=253 octets — the one place local validation beats
    pass-through, because PowerDNS's parse errors for bad names are
    unhelpful and policy needs to inspect the name anyway (zone protection).
    """
    zone = canonical_zone(name)
    if not _LDH_ZONE_RE.fullmatch(zone):
        raise PolicyError(
            422,
            f"Invalid zone name '{name}': use LDH labels only (letters, digits, "
            "hyphens); punycode (xn--...) for internationalized names",
            code="invalid_zone_name",
        )
    if len(zone.encode()) > 253:
        raise PolicyError(422, f"Zone name '{zone}' exceeds 253 octets", code="invalid_zone_name")
    return zone


class PdnsClient:
    def __init__(self, http: httpx.AsyncClient, server_id: str) -> None:
        self._http = http
        self._base = f"/servers/{server_id}"

    async def list_zones(self) -> list[dict]:
        resp = await self._request("GET", f"{self._base}/zones")
        return resp.json()

    async def get_zone(self, zone_id: str) -> dict:
        resp = await self._request("GET", f"{self._base}/zones/{zone_id}")
        return resp.json()

    async def patch_rrsets(self, zone_id: str, rrsets: list[dict]) -> None:
        await self._request(
            "PATCH",
            f"{self._base}/zones/{zone_id}",
            json={"rrsets": rrsets},
        )

    async def create_zone(self, name: str, nameservers: list[str]) -> dict:
        try:
            resp = await self._request(
                "POST",
                f"{self._base}/zones",
                json={
                    "name": name,
                    "kind": "Native",
                    "soa_edit_api": "DEFAULT",
                    "nameservers": nameservers,
                },
            )
        except PdnsError as exc:
            if exc.status_code == 409:
                raise PdnsError(409, exc.detail, code="zone_exists") from exc
            raise
        return resp.json()

    async def delete_zone(self, zone_id: str) -> None:
        try:
            await self._request("DELETE", f"{self._base}/zones/{zone_id}")
        except PdnsError as exc:
            if exc.status_code == 404:
                raise PdnsError(404, exc.detail, code="zone_not_found") from exc
            raise

    async def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        try:
            resp = await self._http.request(method, path, **kwargs)
        except httpx.TransportError as exc:
            raise PdnsError(
                502, f"PowerDNS unreachable: {exc}", code="pdns_unavailable"
            ) from exc
        if resp.is_error:
            status = resp.status_code if resp.status_code in PASSTHROUGH_STATUSES else 502
            raise PdnsError(status, self._error_detail(resp))
        return resp

    @staticmethod
    def _error_detail(resp: httpx.Response) -> str:
        try:
            detail = resp.json().get("error")
        except ValueError:
            detail = None
        detail = detail or f"PowerDNS returned HTTP {resp.status_code}"
        return f"PowerDNS returned an error: {detail}"
