# scenario-uncertainty — uncertainty and quality conventions for scenario data (spec)

**Status:** draft 0.1 (2026-10-21). Not implemented in any tool yet; field names may still change before 1.0.

**Applies to:** FieldDataLab, ORBIT (with orbit-georef), SAVANT (markit, edit, trainit, savant_common), COSMO, and data-metrics (first adopter of the `metrics` profile).

**Structure:**
- **Part I — Core:** domain-neutral rules: the Q object, units, levels, dataprov conventions, missing values, compatibility.
- **Part II — Profiles:** the contracts between the tools of the drone-video → annotation → georeference → scenario chain.

**Repo contents (planned):** this spec, JSON Schemas, a small namespace ontology, and a zero-dependency Python package (`scenario_uncertainty`). The package will be MIT-licensed, so every tool can import it, whatever its licence (GPL, AGPL, MIT). Geometry maths stays in the tools: the homography Jacobian and covariance in orbit-georef, error-model fitting in trainit, propagation and smoothing in COSMO.

Keywords: **MUST** / **SHOULD** / **MAY**, as in RFC 2119.

---

# Part I — Core
## 1. Principles
1. **Two channels.**
   - **dataprov** carries summaries, warnings and links: §6.
   - **Data files and sidecars** carry the detail: §P1–§P6.
   - Arrays MUST NOT go into dataprov.
2. **Self-describing values.** Every quality number is either written as a Q object (§3), or has a fixed descriptor in the registry (§P1–§P6). The registry option is used where the host format can't carry descriptors, e.g. OpenLABEL `vec` values, which must be flat arrays.
3. **Missing means unknown, never perfect.** A reader that finds no value uses the documented default (§P7), records `basis: "assumed"` for whatever it derives, and emits a warning (§6.3).
4. **Additive and backward compatible** (§8). Old files stay readable; they just carry less information.
5. **Raw values are never overwritten.** Calibrated or derived values are added *next to* the originals, for example `p_exist` next to `confidence`.

## 2. Versioning
- **This spec:** `scenario-uncertainty/<major>.<minor>`, currently `scenario-uncertainty/0.1`. Breaking changes (renamed fields, changed meaning) bump the major version; additions bump the minor version.
- **Every file that carries quality data** MUST state which spec version it follows:
  - Sidecars and model files: top-level `"schema": "scenario-uncertainty/<profile>/<major>"`, e.g. `scenario-uncertainty/video/1`.
  - ORBIT georef: its own `"version"` (≥ 1.2), plus `"quality_spec": "scenario-uncertainty/0.1"`.
  - OpenLABEL: `openlabel.metadata.quality.spec` (§P3.1). The OpenLABEL `schema_version` stays `"1.1"`.
- **Unknown-version rule.** A reader that sees a `<profile>` major version it doesn't know MUST ignore the quality content and warn. It MUST NOT fail.

## 3. The Q object (quality value with descriptors)

Used wherever JSON allows nested objects: sidecars, georef, dataprov custom properties, and OpenLABEL `metadata.quality`.

```json
{"value": 0.74, "unit": "m", "stat": "sigma", "level": "image", "basis": "measured",
 "n": 17, "source": "orbit/2.3.0", "note": "deviation of RTK altitudes from best-fit plane"}
```

| Key | Required | Meaning |
|---|---|---|
| `value` | yes | Number, or a flat array of numbers. For `cov` and vectors, the component order is given by the field's registry entry. |
| `unit` | yes | §4.1 |
| `stat` | yes | §4.2 |
| `level` | yes | §5 |
| `basis` | yes | `measured` (from data), `derived` (propagated from other Q values), `assumed` (a prior, default or expert guess), or `unknown` (a placeholder: the value is meaningless and only marks that the quantity is unknown) |
| `n` | no | Number of samples behind the value |
| `source` | no | `<tool>/<version>` that produced it |
| `note` | no | Free text |

Shorthand used in this document: `Q(unit, stat, level[, basis])` means a Q object with those descriptors. In JSON examples, `Q` stands for a full Q object.

## 4. Units and statistics
### 4.1 Units
| Unit | Used for |
|---|---|
| `m` | Lengths and positions in world coordinates |
| `m2` | Variance and covariance of positions |
| `m/s`, `m/s2` | Speed and acceleration |
| `rad` | Angles. Never degrees in data; degrees are allowed only in `note`. |
| `rad2` | Angle variance |
| `px` | Pixel lengths |
| `px2` | Pixel variance |
| `s` | Time |
| `1` | Dimensionless: ratio, probability, count |
| `rel` | Relative to the box size, i.e. a fraction of `w` or `h` |

### 4.2 Statistics
| `stat` | Meaning |
|---|---|
| `sigma` | 1σ standard deviation |
| `cov` | Covariance matrix, flattened row-major |
| `rms` | Root mean square of residuals |
| `mean` | Mean (bias) of residuals |
| `max` | Maximum absolute residual |
| `p` | Probability in [0, 1] |
| `ratio` | Fraction in [0, 1] |
| `count` | Integer count |
| `value` | A plain value, not a statistic: e.g. altitude, or the magnitude of a correction |

A σ always means a Gaussian 1σ. Quantiles are not used in 0.1.

The pixel and world spaces used by the profiles are defined in §P0.1.

## 5. Error levels
Every value belongs to exactly one level. Values on the same level and scope are correlated; values on different levels are treated as independent.

| `level` | Generic definition: shared by | Examples in the drone-video chain | Cancels in |
|---|---|---|---|
| `datum` | Everything in a dataset or recording, including reference data aligned in the same way | Common shift, rotation or scale of the georeference; RTK datum. A map drawn on the same image shares it. | Distances between items, size, position relative to same-aligned reference data |
| `image` | Everything at the same location in the sensor field, constant over time | Residual lens distortion, deviation from the ground plane, homography misfit | Differences between items near each other |
| `frame` | Everything in one time step | Stabilisation residual | Distances between items in the same time step |
| `object` | One item in one time step | Detection noise, oblique/height bias, interpolation | Nothing |
| `none` | Not spatial | Existence probability, classification, VLM confidence, data-metrics assessments | — |

The level names come from the camera-based chain. A non-camera sensor uses the same levels with the generic meaning; for example, `image` means "sensor field position".

**Combination rules for consumers** (written for the chain; the same logic applies elsewhere):

| Quantity | Uncertainty to use |
|---|---|
| Absolute world position | datum + image(u) + frame(t) + object |
| Position relative to a map built from the same image | image(u), partly cancelling, + frame(t) + object |
| Distance between two objects in one frame | object for both, plus image only if they are far apart in the image |
| Size | object only |
| Speed and acceleration | object, plus frame if it changes between frames, propagated through the smoother |

- A `datum` covariance MUST be stated once per recording and MUST NOT be added to every sample.
- Writers SHOULD keep the levels separate and not pre-sum them.

## 6. dataprov conventions
### 6.1 Namespace
- Custom properties use the namespace prefix `su` with URI `https://das-rise.github.io/scenario-uncertainty/ns#`. Declare it via `custom_namespaces={"su": ...}`. It can sit alongside existing ones such as `savant`.
- Key format: `activity:su:<name>`. The value is a Q object, or a dict of Q objects for grouped summaries.

### 6.2 Quality files as outputs
- Quality sidecars are listed in `outputs`, with `output_formats` entry `scenario-uncertainty/<profile>/<major>`. dataprov then adds their SHA256 and size.
- Consumers find a quality file by that format string. They MUST check its SHA256 against the provenance record when both are available.
- Consumers get quality files through explicit CLI paths. They don't discover them by walking the provenance chain.

### 6.3 Warnings
- `warnings` stays free text. Each quality warning is one line: `[su:<code>] <message>`.
- Codes (extendable; unknown codes are shown as-is):

| Code | Meaning |
|---|---|
| `calib_resolution_mismatch` | Calibration and video resolution differ |
| `calib_scaled` | K was scaled to the video resolution |
| `frame_offset` | Output frames are not aligned with the SRT (states the offset) |
| `frame_offset_unknown` | Alignment is not known |
| `stabilization_failed_frames` / `stabilization_filled_frames` | Frames that failed stabilisation, or were filled from neighbours |
| `adjustment_exceeds_validation` | The ORBIT manual adjustment is larger than the RTK validation error |
| `adjustment_unknown` | The original clicks are lost, so the adjustment can't be separated |
| `nonplanar_terrain` | The plane residual of control-point altitudes exceeds a threshold |
| `transform_method_unknown` | The georef doesn't state its transform method |
| `default_used` | A §P7 default replaced a missing value (names the field) |
| `uncalibrated_confidence` | Raw detector scores were used as probabilities |

### 6.4 drl
Optional. A step SHOULD NOT raise `drl` above its input's value while it emits `[su:*]` warnings about known defects.

## 7. Missing values

A reader that finds no value MUST use the default documented for that field by the relevant profile (§P7), set `basis: "assumed"` on whatever it derives, list the field in `defaults_used` where the profile has one, and emit `[su:default_used]` (§6.3).

## 8. Compatibility rules
- **Additive only.** Never rename, remove or re-type an existing key or `vec` name. New things are optional.
- **Readers** ignore unknown keys and entries, except where §P3.6 requires them to be preserved. They treat missing ones as unknown (§P7).
- **Semantic fixes** to an existing field (e.g. ORBIT's `rmse_pixels`, which before georef 1.2 was a round trip and ≈ 0 by construction) need a format-version bump. Readers decide which meaning applies by the version.
- **Legacy defects** are handled by detection plus warning, never silently:
  - frame offset (§P7);
  - calibration mismatch: `[su:calib_resolution_mismatch]`, image term unknown;
  - lost ORBIT clicks: `H_fit = null`, `adjustment.method = "unknown"`.
- **Regression fixture per repo.** One current-format sample must keep loading and converting. Where no new information exists, outputs must be identical.

---

# Part II — Profiles

Each profile is a contract owned by this spec. The producing tool implements it; consumers depend on the spec, not on the producer.

## P0. Shared conventions of the chain

### P0.1 Pixel and world spaces
- **`px` without qualification** means pixels of the **delivered video**: VIDr/VIDp, i.e. undistorted and stabilised to its reference frame. This is the space SAVANT annotates in and ORBIT clicks in.
- **Raw camera pixels**, used only in FieldDataLab calibration, are named explicitly (`*_raw_px`).
- **World coordinates** use the projected CRS of the georef `proj_string`, as E/N/U in metres. If COSMO writes a local frame, the offset is recorded, as `proj_frame_offset` already is.
- **Heading** follows OSI: rad, counter-clockwise from +E.
- **Image angles** follow SAVANT `rbbox`: rad.

## P1. Profile `video` — FieldDataLab sidecar
- **File:** `<video stem>.quality.json`, next to the delivered VIDr/VIDp.
- **Schema:** `scenario-uncertainty/video/1`.
- Columnar per-frame data MAY instead go in `<stem>.quality.frames.parquet` (or `.csv`), with the columns named as below; `per_frame` then points to that file.

```json
{
  "schema": "scenario-uncertainty/video/1",
  "source": {"video": "VIDr_….mp4", "sha256": "…", "tool": "vidrectify/x.y"},
  "frame_index": {"base": 0, "n_frames": 29417, "offset_vs_srt": 0, "srt": "VIDc_….srt", "aligned": true},
  "calibration": {
    "file": "calibration_mavic3pro_standard.json",
    "calibrated_size": [3840, 2160], "video_size": [3840, 2160], "K_scaled": false,
    "K_raw_px": [[...]], "D": [...], "new_K": [[...]], "roi": [x, y, w, h], "alpha": 1,
    "rms": {"value": 0.57, "unit": "px", "stat": "rms", "level": "image", "basis": "measured", "n": 40},
    "holdout_rms": null
  },
  "stabilization": {
    "reference_frame": 0, "transform": "homography", "detector": "sift",
    "smoothing": {"type": "gaussian", "sigma_frames": 3},
    "summary": {
      "failed": {"value": 0, "unit": "1", "stat": "count", "level": "frame", "basis": "measured"},
      "filled": {"value": 0, "unit": "1", "stat": "count", "level": "frame", "basis": "measured"},
      "reproj_err": {"value": 0.0, "unit": "px", "stat": "rms", "level": "frame", "basis": "measured"}
    },
    "per_frame": {
      "inliers": [...], "inlier_ratio": [...], "reproj_err_px": [...],
      "corner_disp_px": [...], "filled": [...]
    }
  }
}
```

**Field definitions:**
- `frame_index.offset_vs_srt` = k means that output frame f corresponds to SRT block f + k. `aligned` is true iff k = 0.
- `per_frame.*` arrays have length `n_frames`, indexed by output frame (base 0):
  - `inliers`, `inlier_ratio`: RANSAC result against the reference frame.
  - `reproj_err_px`: RMS reprojection error of the inliers under the raw transform.
  - `corner_disp_px`: maximum displacement of the four image corners between the raw and the applied (smoothed) transform.
  - `filled`: boolean, true when the transform was interpolated.
- **Interpretation:** `reproj_err_px` together with `corner_disp_px` gives the `frame`-level σ. The consumer converts it to metres through the georef Jacobian.

## P2. Profile `georef` — ORBIT georef JSON ≥ 1.2

The existing keys are kept unchanged. `transformation_matrix` remains the matrix to use, i.e. `H_final`. The new keys are below.

| Key | Content |
|---|---|
| `quality_spec` | `"scenario-uncertainty/0.1"` |
| `control_points[].altitude_m` | RTK altitude, or null |
| `control_points[].sigma_h_m`, `sigma_v_m` | RTK σ, or null |
| `control_points[].sigma_px` | Pick precision (§P0.1 px), from zoom and the per-type human σ |
| `control_points[].point_type` | From the RTK CSV, if present |
| `control_points[].residual_m` | `[dE, dN]` of H_final(pixel) − RTK, for training and validation points |
| `control_points[].residual_px` | H_final⁻¹(RTK) − clicked pixel (a true residual; before 1.2 this was a pixel→geo→pixel round trip) |
| `control_points[].pixel_clicked` | `[x, y]` before any adjustment, or null if lost |
| `H_fit` | 3×3 matrix fitted to `pixel_clicked`, or null |
| `adjustment` | `{"A": 3×3, "params": {...}, "method": "keyboard"\|"pairs"\|"none"\|"unknown", "magnitude": Q(m, value, image)}` |
| `validation` | `{"rms": Q, "datum": {...}, "internal": Q}`, see below |
| `terrain` | `{"plane": [a, b, c], "residual": Q(m, sigma, image), "n": …}` from the control-point altitudes |
| `covariance` | Optional: `{"H_cov": 8×8 flattened, "basis": …}` or `{"grid": …}` |

- **`validation.datum`** is the Helmert (2D similarity) fit between H_final(validation pixels) and RTK. It holds `shift_m` [E, N], `rotation_rad`, `scale` and their covariance (4×4, order E, N, rot, scale) as Q objects, level `datum`.
- **`validation.internal`** is the RMS left after removing the similarity, level `image`. With fewer than 5 validation points it SHOULD be computed leave-one-out, and `note` says so.
- **`rmse_pixels` from version 1.2 on** is a true residual (H_final⁻¹(RTK) − clicked pixel), not the earlier round trip. Readers MUST ignore `rmse_pixels` in files with `version` < 1.2.
- **orbit-georef API** should expose:
  - `jacobian(u, v)`: 2×2, m/px;
  - `position_covariance(u, v)`: returns `{"datum": 2×2, "image": 2×2}` in m².

## P3. Profile `annotation` — SAVANT OpenLABEL

OpenLABEL `vec` values must be flat arrays of numbers or strings, and object-level `vec` values must be strings. So the descriptors of these fields are fixed by this registry, not written per value.

### P3.1 Run level: `openlabel.metadata.quality`
```json
{"spec": "scenario-uncertainty/0.1",
 "error_model": {"file": "error_model.json", "sha256": "…", "basis": "measured"},
 "score_calibration": {"file": "…", "method": "isotonic", "ece": Q},
 "defaults_used": ["sigma_px"],
 "share_interpolated": Q(1, ratio, none), "share_reviewed": Q(1, ratio, none)}
```
- `error_model` is null when no error model exists. Then `sigma_px` is either absent or comes from §P7 defaults, and is listed in `defaults_used`.

### P3.2 Per box: `frames[f].objects[id].object_data.vec`

| `name` | `val` | Unit / stat / level / basis |
|---|---|---|
| `annotator`, `confidence` | Unchanged (existing): history lists, newest first | `confidence`: raw score, *not* a probability |
| `origin` | `[string]`, newest first, aligned with `annotator` | Vocabulary in §P3.4 |
| `gap_distance` | `[int]` | Frames to the nearest `detected`/`manual` box of the same object; 0 for those boxes themselves |
| `sigma_px` | `[σcx, σcy, σw, σh, σr]` | px, px, px, px, rad / sigma / object / basis from `metadata.quality.error_model` |
| `p_exist` | `[p]` | 1 / p / none / derived (calibrated from the raw score) |
| `quality_flags` | `[string, …]` | Any of `suddenappear`, `suddendisappear`, `size_step`, `jitter`, `edge_clipped`, `static` |

- New entries are appended to `vec`. Readers find entries by `name`, never by position.
- `origin` is a history list like `annotator`: index 0 is the newest, and it has the same length as `annotator` when both are present.

### P3.3 Per object: `objects[id].object_data`
- Scalars go in OpenLABEL `num` entries (`{"name", "val": number}`), because object-level `vec` is string-only.
- `sigma_h_m`, `sigma_v_m` (`vec` of strings, one per corner, aligned with `arucoID`/`markerID` like `lat`/`long`/`alt`):
  RTK σ of ArUco and visual markers (m / sigma / datum / measured). `"inf"` marks a corner without a value.
- `review`: `vec` of strings `["<annotator>", "<ISO-8601 time>"]`, the latest review.

### P3.4 Origin vocabulary
| Value | Meaning |
|---|---|
| `detected` | Detector output in this frame |
| `tracked` | Tracker coasted without a detection |
| `interpolated` | Synthesized between real boxes |
| `merged` | Moved over from a removed duplicate |
| `manual` | Drawn or changed by a human |
| `manual_interpolated` | Interpolated by edit |
| `manual_tracked` | Tracked by edit |
| `reviewed` | A human confirmed the box without changing it |

Postprocessing passes that only adjust geometry (smoothing, rotation, spline, outlier) keep the existing origin; the change is already recorded in `annotator`.

### P3.5 VLM (tags and contexts)
- Add `<field>_n_samples` (`num`, count) and `<field>_agreement` (`num`, ratio, none) next to the existing `<field>_confidence`.
- `<field>_confidence` keeps its meaning: self-reported and uncalibrated.

### P3.6 Requirement on all readers and writers of SAVANT OpenLABEL
- Unknown `vec` and `num` entries, unknown `metadata` keys and unknown `frame_properties` keys MUST be preserved on load and save.
- edit currently drops or rejects them: its `vec` Literal union, `OpenLabelMetadata` and `FrameProperties`. This must be fixed **before** any writer emits §P3 fields (the SAVANT editor must be updated first).

## P4. Profile `model` — trainit error model
- **File:** `error_model.json` next to `best.pt`.
- **Schema:** `scenario-uncertainty/model/1`.

```json
{"schema": "scenario-uncertainty/model/1",
 "model": {"file": "best.pt", "sha256": "…"}, "dataset": {"manifest": "…", "split": "chunked", "val_frames": …},
 "localization": {"by_class": {"car": {"sigma": {"cx": [a, b], "cy": [a, b], "w": [a, b], "h": [a, b], "r": [a, b]}, "n": …}},
                  "model_form": "sigma = a + b*size_px", "size_px": "sqrt(w*h)", "iou_match": 0.5},
 "score_calibration": {"method": "isotonic", "x": [...], "y": [...], "ece": Q, "n": …},
 "metrics": {"map50": Q, "map50_95": Q, "per_class": {...}}}
```
- σ for the angle uses rad. All other σ values use px.
- Origin inflation is applied by markit, not stored here: σ² = σ_det² + q·k², with k = `gap_distance`. The value of q is recorded in markit's `metadata.quality`.

## P5. Profile `world` — COSMO companion OpenLABEL

This is a SAVANT-style OpenLABEL file with `coordinate_systems.world = {"type": "geo", "proj_string": …}`, written alongside the omega-prime MCAP. The MCAP itself is unchanged.

- **Run level:** `metadata.quality` (§P3.1 keys) plus:
  - `datum`: Q(m2, cov, datum), 4×4 in the order E, N, rot, scale, or 2×2 for E, N only;
  - `inputs`: spec version and sha256 of each quality input;
  - `frame_offset_applied`.
- **Per object** (`num`):
  - `size_mean_l`, `size_mean_w`: m, value;
  - `size_std_l`, `size_std_w`: m, sigma, object, measured;
  - `path_residual_rms`: m, rms, object, measured;
  - `h_eff`: m, value, derived;
  - `share_interpolated`: 1, ratio.
- **Per frame and object** (`vec`, variant B only):

  | `name` | Content | Unit / stat / level / basis |
  |---|---|---|
  | `cuboid` | World cuboid `[X, Y, Z, rx, ry, rz, L, W, H]` (OpenLABEL `cuboid` attribute) | — |
  | `velocity`, `acceleration` | `[vx, vy]`, `[ax, ay]` | m/s, m/s² |
  | `position_cov_rel` | `[EE, EN, NE, NN]` | m², cov, object + image + frame, derived |
  | `sigma_heading` | — | rad, sigma |
  | `sigma_size` | `[σL, σW]` | m |
  | `velocity_cov`, `acceleration_cov` | — | — |
  | `size_deviation` | `[dL, dW]` | m, value |
  | `oblique` | `[method, shift_m, h_used]`, as strings | — |
  | `origin`, `p_exist` | Copied from the input | — |

- `position_cov_rel` deliberately excludes `datum`. Absolute uncertainty = `position_cov_rel` + `metadata.quality.datum`.
- The optional OSI SensorData topic MAY be written; its mapping is defined later (0.2).

## P6. Profile `metrics` — data-metrics (stub)

File-level and dataset-level quality *assessments* from `data-metrics` (das-rise). They answer "is this file usable?", not "how wrong is each value?", but use the same Q object and dataprov conventions.

- **Schema:** `scenario-uncertainty/metrics/1`, declared as a top-level `"schema"` in each output JSON. The existing keys stay unchanged.
- **Each metric becomes a Q object:** `stat` is `ratio`, `p` or `count`, and `level` is `none`. It also gets `"threshold"` and `"passes"` keys. Example: `"temporal_completeness": {"value": 0.998, "unit": "1", "stat": "ratio", "level": "none", "basis": "measured", "threshold": 0.95, "passes": true}`.
- **dataprov:**
  - Outputs are listed with `output_formats` `scenario-uncertainty/metrics/1`.
  - A failed threshold becomes `[su:metric_failed] <metric>`.
- **Consumption, later:**
  - Video metrics MAY report the `video` profile's stabilisation summary.
  - Trajectory plausibility and `traffic-density` MAY use the `world` profile's `position_cov_rel`, e.g. for the off-lane snap tolerance.
- Field list to be defined from data-metrics' current output schema.

## P7. Defaults when information is missing (all `basis: "assumed"`)

These are placeholders until measured values exist. Consumers MUST list every default they used in `defaults_used` and emit `[su:default_used]` (§7).

| Quantity | Default | Notes |
|---|---|---|
| `sigma_px` for `detected` | cx, cy: 0.02·√(w·h); w, h: 0.04·√(w·h); r: 0.05 rad | Rough guess, to be replaced by a measured error model (§P4) |
| `sigma_px` for `manual` / `reviewed` | 0.5 × the detected value | |
| `sigma_px` for `interpolated` / `tracked` | detected value × (1 + 0.1·k), k = `gap_distance` or 15 if unknown | |
| `origin` when absent | `markit_housekeeping(gap)` → `interpolated`; other `markit_*` → `detected`; any other annotator → `manual` | Legacy inference |
| Georef `image` term | `validation_error.rmse_meters` (isotropic), else `reprojection_error.rmse_meters` × 2 | Training RMSE underestimates |
| Georef `datum` term | Same value as the image term | Unknown split |
| `frame` term (stabilisation) | 0, with `[su:default_used]` | Unknown, *not* zero error; flagged |
| Frame offset vs SRT | 0 if provenance says aligned; 1 if VIDr has one frame fewer than VIDc; else unknown → 0 with `[su:frame_offset_unknown]` | |
| Vehicle height h | COSMO `DEFAULT_VEHICLE_HEIGHTS`, σ = 15 % of h | |
| RTK σ | 0.02 m horizontal, 0.03 m vertical | |

---

## 9. Open points for 0.2
- OSI SensorData mapping (DetectedMovingObject fields).
- Per-image-location `image` covariance grid format (from orbit-georef).
- Whether `rel` units are needed in data, or only in the error model.
- A JSON Schema for the `video` and `model` sidecars.
