"""dataprov conventions (SPEC §6): namespace, custom properties, quality warnings, quality-file formats.

Returns plain dicts and strings, so this package does not depend on dataprov.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from .core import Q, schema_id

NAMESPACE_PREFIX = "su"
NAMESPACE_URI = "https://das-rise.github.io/scenario-uncertainty/ns#"


class WarningCode:
    """Codes of quality warnings (SPEC §6.3); unknown codes are allowed and shown as-is."""

    CALIB_RESOLUTION_MISMATCH = "calib_resolution_mismatch"
    CALIB_SCALED = "calib_scaled"
    FRAME_OFFSET = "frame_offset"
    FRAME_OFFSET_UNKNOWN = "frame_offset_unknown"
    STABILIZATION_FAILED_FRAMES = "stabilization_failed_frames"
    STABILIZATION_FILLED_FRAMES = "stabilization_filled_frames"
    ADJUSTMENT_EXCEEDS_VALIDATION = "adjustment_exceeds_validation"
    ADJUSTMENT_UNKNOWN = "adjustment_unknown"
    NONPLANAR_TERRAIN = "nonplanar_terrain"
    TRANSFORM_METHOD_UNKNOWN = "transform_method_unknown"
    DEFAULT_USED = "default_used"
    UNCALIBRATED_CONFIDENCE = "uncalibrated_confidence"
    METRIC_FAILED = "metric_failed"


def namespaces() -> dict[str, str]:
    """For ProvenanceChain.create(custom_namespaces=...)."""
    return {NAMESPACE_PREFIX: NAMESPACE_URI}


def declare_namespace(chain: Any) -> None:
    """Declare the su prefix on an existing (loaded) dataprov chain.

    dataprov only declares namespaces when a chain is created; a loaded chain keeps its registry in
    `chain.namespaces`, which is the dict saved as the file's "prefix" section.
    """
    chain.namespaces.setdefault(NAMESPACE_PREFIX, NAMESPACE_URI)
    data = getattr(chain, "data", None)
    if isinstance(data, dict):
        data.setdefault("prefix", chain.namespaces).setdefault(NAMESPACE_PREFIX, NAMESPACE_URI)


def custom_properties(summary: Mapping[str, Any], target: str = "activity") -> dict[str, Any]:
    """dataprov custom_properties for headline quality values: {"<target>:su:<name>": ...}.

    Each value is a Q, a Q dict, or a mapping of names to those (a grouped summary).
    """
    return {f"{target}:{NAMESPACE_PREFIX}:{name}": _as_q_dicts(value) for name, value in summary.items()}


def _as_q_dicts(value: Any) -> Any:
    if isinstance(value, Q):
        return value.to_dict()
    if isinstance(value, Mapping) and "unit" in value:
        return Q.from_dict(value).to_dict()  # validates the descriptors
    if isinstance(value, Mapping):
        return {key: _as_q_dicts(item) for key, item in value.items()}
    raise TypeError(f"expected a Q, a Q dict or a mapping of them, got {type(value).__name__}")


def warning_line(code: str, message: str) -> str:
    """One quality warning line: [su:<code>] <message>."""
    return f"[{NAMESPACE_PREFIX}:{code}] {message}"


def join_warnings(lines: Iterable[str]) -> str:
    """dataprov `warnings` text from warning lines (one per line)."""
    return "\n".join(line for line in lines if line)


def output_format(profile: str, major: int) -> str:
    """dataprov output_formats entry that identifies a quality file of a profile."""
    return schema_id(profile, major)
