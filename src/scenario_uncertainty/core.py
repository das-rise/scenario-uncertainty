"""Core of the scenario-uncertainty spec (SPEC.md Part I): the Q object and its vocabulary."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any

SPEC_VERSION = "0.1"
SPEC_ID = f"scenario-uncertainty/{SPEC_VERSION}"
SCHEMA_PREFIX = "scenario-uncertainty"

_SCHEMA_ID = re.compile(rf"^{SCHEMA_PREFIX}/([a-z][a-z0-9_-]*)/(\d+)$")


class Unit(str, Enum):
    """Units of quality values (SPEC §4.1). Angles are always radians."""

    M = "m"
    M2 = "m2"
    M_S = "m/s"
    M_S2 = "m/s2"
    RAD = "rad"
    RAD2 = "rad2"
    PX = "px"
    PX2 = "px2"
    S = "s"
    ONE = "1"
    REL = "rel"


class Stat(str, Enum):
    """What a value states (SPEC §4.2). A sigma is a Gaussian 1-sigma."""

    SIGMA = "sigma"
    COV = "cov"
    RMS = "rms"
    MEAN = "mean"
    MAX = "max"
    P = "p"
    RATIO = "ratio"
    COUNT = "count"
    VALUE = "value"


class Level(str, Enum):
    """Error level: what a value is shared by (SPEC §5). Values on different levels are independent."""

    DATUM = "datum"
    IMAGE = "image"
    FRAME = "frame"
    OBJECT = "object"
    NONE = "none"


class Basis(str, Enum):
    """How a value was obtained (SPEC §3)."""

    MEASURED = "measured"
    DERIVED = "derived"
    ASSUMED = "assumed"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class Q:
    """A quality value with the descriptors every value must carry (SPEC §3)."""

    value: float | list[float] | None
    unit: Unit
    stat: Stat
    level: Level
    basis: Basis
    n: int | None = None
    source: str | None = None
    note: str | None = None

    def __post_init__(self):
        # Accept the string forms so callers and parsed JSON need no enum imports
        for name, kind in (("unit", Unit), ("stat", Stat), ("level", Level), ("basis", Basis)):
            object.__setattr__(self, name, kind(getattr(self, name)))

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {"value": self.value, "unit": self.unit.value, "stat": self.stat.value,
                               "level": self.level.value, "basis": self.basis.value}
        for key in ("n", "source", "note"):
            if getattr(self, key) is not None:
                out[key] = getattr(self, key)
        return out

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Q:
        return cls(value=data.get("value"), unit=data["unit"], stat=data["stat"], level=data["level"],
                   basis=data["basis"], n=data.get("n"), source=data.get("source"), note=data.get("note"))


def schema_id(profile: str, major: int) -> str:
    """The "schema" string of a profile file, e.g. scenario-uncertainty/video/1."""
    return f"{SCHEMA_PREFIX}/{profile}/{major}"


def parse_schema_id(value: str) -> tuple[str, int] | None:
    """(profile, major) of a schema string, or None if it is not a scenario-uncertainty schema."""
    match = _SCHEMA_ID.match(value or "")
    return (match.group(1), int(match.group(2))) if match else None
