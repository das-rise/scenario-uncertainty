# scenario-uncertainty

Conventions and profiles for uncertainty and quality information in a scenario-based testing (SBT)
workflow. The scope is traffic-scenario data derived from recordings: video → annotation →
georeference → scenario (OpenLABEL, ASAM OSI / omega-prime).

> [!NOTE]
> Draft 0.1. The specification is available; the JSON Schemas, ontology and Python package are not
> written yet.

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

## Planned contents

- `SPEC.md`: the specification (available now).
- JSON Schemas for the Q object and the sidecar profiles.
- A small ontology for the `su` namespace.
- A zero-dependency Python package, `scenario_uncertainty`. It will provide:
  - a Q dataclass;
  - profile readers and writers, with defaults and handling of unknown versions;
  - a level-aware combiner;
  - helpers that produce dataprov properties and warnings.

Geometry and statistics specific to one tool stay in that tool.

## License

MIT. See [LICENSE](LICENSE).
