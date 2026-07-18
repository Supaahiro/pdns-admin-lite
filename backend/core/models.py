"""API schemas exchanged with the frontend."""

from enum import Enum

from pydantic import BaseModel, Field


class RecordType(str, Enum):
    """Record types the UI is allowed to manage."""

    A = "A"
    AAAA = "AAAA"
    CNAME = "CNAME"
    TXT = "TXT"
    MX = "MX"
    SRV = "SRV"
    NS = "NS"
    PTR = "PTR"


class ZoneSummary(BaseModel):
    id: str
    name: str
    kind: str
    serial: int
    protected: bool


class Record(BaseModel):
    content: str
    disabled: bool = False


class RRSet(BaseModel):
    name: str
    type: str
    ttl: int
    records: list[Record]


class ZoneDetail(ZoneSummary):
    rrsets: list[RRSet]


class ZoneCreate(BaseModel):
    """Shape-only: the name's syntax/policy validation lives in core.pdns
    (validate_zone_name), since policy needs to inspect the name anyway."""

    name: str = Field(min_length=1)


class RecordUpsert(BaseModel):
    """A single rrset to create or replace.

    `name` may be relative to the zone ("web"), "@" or "" for the apex
    (canonicalize() treats them the same), or a FQDN. Unconstrained length:
    "" is a legitimate apex form, not a missing value.
    """

    name: str
    type: RecordType
    ttl: int = Field(default=3600, ge=1)
    records: list[str] = Field(min_length=1)
