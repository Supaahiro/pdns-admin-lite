"""HTTP endpoints exposed to the frontend.

Zone lifecycle (create/delete) is owned by this UI for the demo/dev zone —
or whatever zone you point it at and intend it to own — subject to
PROTECTED_ZONES; zones outside that set can be created and deleted here.
Records (rrsets) can always be mutated, except the apex NS of a protected
zone (see ensure_zone_mutable / the apex-NS check below).
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from core.auth import require_auth
from core.config import Settings
from core.models import RecordType, RecordUpsert, ZoneCreate, ZoneDetail, ZoneSummary
from core.pdns import (
    PdnsClient,
    PolicyError,
    canonicalize,
    ensure_zone_creatable,
    ensure_zone_mutable,
    is_protected_zone,
    validate_zone_name,
)

router = APIRouter()


def _client(request: Request) -> PdnsClient:
    return PdnsClient(request.app.state.http, request.app.state.settings.pdns_server_id)


def _settings(request: Request) -> Settings:
    return request.app.state.settings


def _to_rrset(zone_id: str, body: RecordUpsert, changetype: str) -> dict:
    return {
        "name": canonicalize(body.name, zone_id),
        "type": body.type.value,
        "ttl": body.ttl,
        "changetype": changetype,
        "records": [{"content": content, "disabled": False} for content in body.records],
    }


def _ensure_apex_ns_mutable(request: Request, zone_id: str, name: str, record_type: str) -> None:
    """Rewriting or deleting apex NS is functionally zone destruction — guard
    it like a zone-level op, but only for the protected zone itself (a
    subzone's own apex NS is a normal delegation record, left alone)."""
    is_apex = record_type == "NS" and name == canonicalize("@", zone_id)
    if is_apex and is_protected_zone(zone_id, _settings(request).protected_zones):
        raise PolicyError(
            403, f"Apex NS records for {zone_id} are protected", code="zone_protected"
        )


@router.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@router.get("/zones", response_model=list[ZoneSummary])
async def list_zones(request: Request) -> list[dict]:
    protected_zones = _settings(request).protected_zones
    zones = await _client(request).list_zones()
    for zone in zones:
        zone["protected"] = is_protected_zone(zone["name"], protected_zones)
    return zones


@router.get("/zones/{zone_id}", response_model=ZoneDetail)
async def get_zone(request: Request, zone_id: str) -> dict:
    zone = await _client(request).get_zone(zone_id)
    zone["protected"] = is_protected_zone(zone["name"], _settings(request).protected_zones)
    zone["rrsets"] = sorted(
        zone.get("rrsets", []), key=lambda rrset: (rrset["name"], rrset["type"])
    )
    return zone


@router.post("/zones", status_code=201, dependencies=[Depends(require_auth)])
async def create_zone(request: Request, body: ZoneCreate) -> dict:
    settings = _settings(request)
    name = validate_zone_name(body.name)
    ensure_zone_creatable(name, settings.protected_zones)
    zone = await _client(request).create_zone(name, [settings.default_ns])
    zone["protected"] = is_protected_zone(zone["name"], settings.protected_zones)
    return zone


@router.delete("/zones/{zone_id}", status_code=204, dependencies=[Depends(require_auth)])
async def delete_zone(request: Request, zone_id: str) -> None:
    ensure_zone_mutable(zone_id, _settings(request).protected_zones)
    await _client(request).delete_zone(zone_id)


@router.post("/zones/{zone_id}/records", status_code=201, dependencies=[Depends(require_auth)])
async def create_record(request: Request, zone_id: str, body: RecordUpsert) -> dict:
    client = _client(request)
    rrset = _to_rrset(zone_id, body, "REPLACE")
    _ensure_apex_ns_mutable(request, zone_id, rrset["name"], rrset["type"])
    zone = await client.get_zone(zone_id)
    # Not atomic (check-then-patch), acceptable for a single-user POC.
    for existing in zone.get("rrsets", []):
        if existing["name"] == rrset["name"] and existing["type"] == rrset["type"]:
            raise HTTPException(
                status_code=409,
                detail=f"Record set {rrset['name']}/{rrset['type']} already exists",
            )
    await client.patch_rrsets(zone_id, [rrset])
    return rrset


@router.put("/zones/{zone_id}/records", dependencies=[Depends(require_auth)])
async def upsert_record(request: Request, zone_id: str, body: RecordUpsert) -> dict:
    rrset = _to_rrset(zone_id, body, "REPLACE")
    _ensure_apex_ns_mutable(request, zone_id, rrset["name"], rrset["type"])
    await _client(request).patch_rrsets(zone_id, [rrset])
    return rrset


@router.delete("/zones/{zone_id}/records", status_code=204, dependencies=[Depends(require_auth)])
async def delete_record(
    request: Request,
    zone_id: str,
    name: str = Query(default=""),
    type: RecordType = Query(),
) -> None:
    fqdn = canonicalize(name, zone_id)
    _ensure_apex_ns_mutable(request, zone_id, fqdn, type.value)
    rrset = {
        "name": fqdn,
        "type": type.value,
        "changetype": "DELETE",
        "records": [],
    }
    await _client(request).patch_rrsets(zone_id, [rrset])
