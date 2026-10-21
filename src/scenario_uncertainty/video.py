"""Profile `video` (SPEC P1): quality sidecar of a preprocessed (undistorted/stabilised) video."""

from __future__ import annotations

import json
import math
import os
import tempfile
import warnings
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from .core import Basis, Level, Q, Stat, Unit, parse_schema_id, schema_id

PROFILE = "video"
MAJOR = 1
SCHEMA = schema_id(PROFILE, MAJOR)
SIDECAR_SUFFIX = ".quality.json"

# Per-frame arrays of the stabilization section; all have one entry per output frame (None if unknown)
PER_FRAME_KEYS = ("inliers", "inlier_ratio", "reproj_err_px", "corner_disp_px", "filled")


def sidecar_path(video: str | os.PathLike) -> Path:
    """<video stem>.quality.json next to the video."""
    video = Path(video)
    return video.with_name(video.stem + SIDECAR_SUFFIX)


def frame_index(n_frames: int, offset_vs_srt: int | None = 0, srt: str | None = None) -> dict[str, Any]:
    """Frame numbering: output frame f is SRT block f + offset_vs_srt (None if unknown)."""
    return {"base": 0, "n_frames": n_frames, "offset_vs_srt": offset_vs_srt, "srt": srt,
            "aligned": None if offset_vs_srt is None else offset_vs_srt == 0}


def calibration_section(file: str | None, calibrated_size: Sequence[int], video_size: Sequence[int],
                        k_raw_px: Sequence[Sequence[float]], distortion: Sequence[float],
                        new_k: Sequence[Sequence[float]] | None = None, roi: Sequence[int] | None = None,
                        alpha: float | None = None, rms_px: float | None = None, n_images: int | None = None,
                        holdout_rms_px: float | None = None, source: str | None = None) -> dict[str, Any]:
    """Lens calibration as applied to this video; k_raw_px is the camera matrix used (after any scaling)."""
    def rms(value):
        return None if value is None else Q(value, Unit.PX, Stat.RMS, Level.IMAGE, Basis.MEASURED,
                                            n=n_images, source=source).to_dict()
    return {"file": file, "calibrated_size": list(calibrated_size), "video_size": list(video_size),
            "K_scaled": list(calibrated_size) != list(video_size),
            "K_raw_px": _matrix(k_raw_px), "D": [float(v) for v in distortion],
            "new_K": None if new_k is None else _matrix(new_k), "roi": None if roi is None else list(roi),
            "alpha": alpha, "rms": rms(rms_px), "holdout_rms": rms(holdout_rms_px)}


def stabilization_section(per_frame: Mapping[str, Sequence[Any]], *, reference_frame: int, transform: str,
                          detector: str, smoothing: Mapping[str, Any], failed: int,
                          source: str | None = None) -> dict[str, Any]:
    """Stabilisation quality with a summary computed from the per-frame arrays.

    `failed` counts frames whose transform could neither be estimated nor filled from neighbours;
    `per_frame["filled"]` marks frames whose transform was interpolated.
    """
    lengths = {key: len(per_frame.get(key, ())) for key in PER_FRAME_KEYS}
    if len(set(lengths.values())) != 1:
        raise ValueError(f"per-frame arrays differ in length: {lengths}")
    reproj = [v for v in per_frame["reproj_err_px"] if v is not None and math.isfinite(v)]
    filled = sum(1 for v in per_frame["filled"] if v)

    def count(value):
        return Q(value, Unit.ONE, Stat.COUNT, Level.FRAME, Basis.MEASURED, source=source).to_dict()
    summary = {
        "failed": count(failed),
        "filled": count(filled),
        "reproj_err": Q(_rms(reproj), Unit.PX, Stat.RMS, Level.FRAME,
                        Basis.MEASURED if reproj else Basis.UNKNOWN, n=len(reproj), source=source).to_dict(),
    }
    return {"reference_frame": reference_frame, "transform": transform, "detector": detector,
            "smoothing": dict(smoothing), "summary": summary,
            "per_frame": {key: list(per_frame[key]) for key in PER_FRAME_KEYS}}


def build(video: str | os.PathLike, *, tool: str, frame_index: Mapping[str, Any],
          calibration: Mapping[str, Any] | None = None, stabilization: Mapping[str, Any] | None = None,
          sha256: str | None = None) -> dict[str, Any]:
    """A complete video quality document; sections that a tool did not run are None."""
    return {"schema": SCHEMA, "source": {"video": Path(video).name, "sha256": sha256, "tool": tool},
            "frame_index": dict(frame_index), "calibration": calibration, "stabilization": stabilization}


def write(path: str | os.PathLike, document: Mapping[str, Any]) -> Path:
    """Write atomically (temp file + rename), so a crash never leaves a truncated sidecar."""
    path = Path(path)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=path.name, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(document, f, separators=(",", ":"), allow_nan=False)
        # mkstemp creates the file private (0600); give it the permissions a normal open() would
        umask = os.umask(0)
        os.umask(umask)
        os.chmod(tmp, 0o666 & ~umask)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise
    return path


def read(path: str | os.PathLike) -> dict[str, Any] | None:
    """The document, or None if missing or of an unknown profile version (warns: missing = unknown)."""
    path = Path(path)
    if not path.exists():
        return None
    document = json.loads(path.read_text(encoding="utf-8"))
    parsed = parse_schema_id(document.get("schema", ""))
    if parsed != (PROFILE, MAJOR):
        warnings.warn(f"{path}: unsupported schema {document.get('schema')!r}, expected {SCHEMA}; ignored",
                      stacklevel=2)
        return None
    return document


def validate(document: Mapping[str, Any]) -> None:
    """Validate against the bundled JSON Schema (needs the `validate` extra: jsonschema)."""
    import jsonschema

    schema = json.loads((Path(__file__).parent / "schemas" / f"{PROFILE}-{MAJOR}.schema.json").read_text())
    jsonschema.validate(document, schema)


def _matrix(rows: Sequence[Sequence[float]]) -> list[list[float]]:
    return [[float(v) for v in row] for row in rows]


def _rms(values: Sequence[float]) -> float | None:
    return math.sqrt(sum(v * v for v in values) / len(values)) if values else None
