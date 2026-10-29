# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-10-29

First release.

### Specification (`SPEC.md`, spec version 0.1)
- **Core:**
  - the Q object (value, unit, statistic, error level, basis);
  - units and statistics;
  - error levels `datum` / `image` / `frame` / `object` / `none`, with combination rules;
  - "missing means unknown" and the backward-compatibility rules.
- **dataprov conventions:**
  - the `su` namespace;
  - quality files listed as outputs with output roles (needs dataprov ≥ 3.4.0);
  - `[su:code]` warnings;
  - drl.
- **Profiles:**
  - `video`: FieldDataLab sidecar;
  - `georef`: ORBIT georef JSON ≥ 1.2, including provenance for ORBIT;
  - `annotation`: SAVANT OpenLABEL, including the VLM agreement and sample count;
  - `model`: trainit error model;
  - `world`: COSMO companion OpenLABEL;
  - `metrics`: data-metrics (stub only);
  - defaults to use when information is missing.

### Python package `scenario_uncertainty` (no dependencies, Python ≥ 3.10)
- `core`: `Q`, the `Unit`/`Stat`/`Level`/`Basis` enums, `schema_id`/`parse_schema_id`.
- `provenance`: namespace helpers for `ProvenanceChain` (`namespaces`, `declare_namespace`), plus:
  - `custom_properties`;
  - `WarningCode`, `warning_line`/`join_warnings`;
  - `output_format`.
- `video`: build, write, read and validate the sidecar for video stabilisation and undistortion.
- JSON Schemas for the Q object and the `video` profile (`schemas/`).
- Only the `video` profile has helpers so far. The other profiles are implemented in the tools that produce them.

[0.1.0]: https://github.com/das-rise/scenario-uncertainty/releases/tag/v0.1.0
