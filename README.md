# scenario-uncertainty

Conventions and profiles for uncertainty and quality information in a scenario-based testing (SBT)
workflow. The scope is traffic-scenario data derived from recordings: video → annotation →
georeference → scenario (OpenLABEL, ASAM OSI / omega-prime).

> [!NOTE]
> Version 0.1, early. The spec and the Python package cover the core (Q object, error levels, dataprov
> conventions) and the `video` profile; the other profiles are specified but not implemented yet.

## What it defines

The specification is in [SPEC.md](SPEC.md). It has two parts.

**Part I — Core**, which is domain-neutral:
- The **Q object**: a value together with its unit, statistic (σ, RMS, covariance, …), error
  level, and whether it was measured or assumed.
- **Error levels** (`datum` / `image` / `frame` / `object` / `none`), and rules for combining them
  without double-counting shared errors.
- **Conventions for [dataprov](https://github.com/RI-SE/dataprov)**: headline numbers, warnings, and
  quality files listed as outputs.
- "**Missing means unknown**", and the backward-compatibility rules.

**Part II — Profiles**, the contracts between tools:

| Profile | Producer | Carried in |
|---|---|---|
| `video` | Video preprocessing (undistortion, stabilisation) | Sidecar JSON |
| `georef` | ORBIT / orbit-georef | Georef JSON ≥ 1.2 |
| `annotation` | SAVANT (markit, edit) | OpenLABEL |
| `model` | SAVANT trainit | `error_model.json` |
| `world` | COSMO | Companion OpenLABEL next to the omega-prime MCAP |
| `metrics` | data-metrics | Metrics JSON |

## Contents

| Path | What |
|---|---|
| `SPEC.md` | The specification |
| `src/scenario_uncertainty/` | Python package `scenario_uncertainty`; no dependencies, Python ≥ 3.10 |
| `src/scenario_uncertainty/schemas/` | JSON Schemas: `q.schema.json`, `video-1.schema.json` |

## Installation

```bash
pip install "scenario-uncertainty @ git+https://github.com/das-rise/scenario-uncertainty.git"
# with JSON Schema validation
pip install "scenario-uncertainty[validate] @ git+https://github.com/das-rise/scenario-uncertainty.git"
```

With uv, as a dependency of another project: `uv add "scenario-uncertainty @ git+https://github.com/das-rise/scenario-uncertainty.git"`.

## Usage

**Quality values** carry their descriptors (SPEC §3):

```python
from scenario_uncertainty import Q

rms = Q(0.57, unit="px", stat="rms", level="image", basis="measured", n=40)
rms.to_dict()  # {"value": 0.57, "unit": "px", "stat": "rms", "level": "image", "basis": "measured", "n": 40}
```

**Video quality sidecar** (profile `video`, written next to a preprocessed video as `<stem>.quality.json`):

```python
from scenario_uncertainty import video

doc = video.build(
    "VIDr_<ts>_D.mp4", tool="vidrectify/2.3.3",
    frame_index=video.frame_index(n_frames=29417, offset_vs_srt=0),
    calibration=video.calibration_section("calibration.json", (3840, 2160), (3840, 2160), K, D,
                                          new_k=new_K, roi=roi, alpha=1, rms_px=0.57, n_images=40),
    stabilization=video.stabilization_section(per_frame, reference_frame=0, transform="homography",
                                              detector="sift", smoothing={"type": "gaussian", "sigma_frames": 3},
                                              failed=0),
)
video.write(video.sidecar_path("VIDr_<ts>_D.mp4"), doc)
video.read("VIDr_<ts>_D.quality.json")   # None if missing or of an unknown version (with a warning)
video.validate(doc)                       # needs the [validate] extra
```

`per_frame` holds one entry per output frame for `inliers`, `inlier_ratio`, `reproj_err_px`,
`corner_disp_px` and `filled` (`None` where unknown); the summary (failed/filled counts, RMS reprojection
error) is computed from it.

**Provenance** ([dataprov](https://github.com/RI-SE/dataprov)), with plain dicts and strings and no dependency on dataprov:

```python
from scenario_uncertainty import provenance

provenance.declare_namespace(chain)                      # su prefix on a loaded chain
chain.add(...,
          outputs=[video_path, sidecar_path],
          output_formats=["MP4", provenance.output_format("video", 1)],
          warnings=provenance.join_warnings([provenance.warning_line("calib_scaled", "...")]),
          custom_properties=provenance.custom_properties({"stabilization": doc["stabilization"]["summary"]}))
```

## Development

```bash
uv run pytest -q
uv run ruff check .
```

## License

MIT. See [LICENSE](LICENSE).
