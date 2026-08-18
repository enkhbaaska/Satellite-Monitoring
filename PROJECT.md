# Tsenher — Satellite MRV for Ulaanbaatar

Independent satellite monitoring of Ulaanbaatar's air quality, built to test whether
the city's 2019 raw coal ban produced a measurable atmospheric effect.

**Hard deadline: 25 August 2026.** This work is presented at the GECCI Pavilion,
UNCCD COP17, Ulaanbaatar. Every claim in the output must be defensible in live
questioning by an audience that includes atmospheric scientists and policy delegates.

---

## 1. What this project actually argues

Parties to UN environmental conventions largely self-report progress. Independent
verification is scarce and is widely assumed to require institutional budgets.

The argument is that it does not. The evidence is a worked example: open satellite
data, open tools, no funding, applied to a real dated policy intervention.

The argument survives whether or not the coal ban shows a clear effect. A null or
ambiguous result is a valid outcome and must be reported as such. **Do not tune the
analysis toward a positive finding.**

## 2. Non-negotiable honesty constraints

These shape the code and must not be quietly optimised away.

- **NO2 is a weak proxy for this intervention.** The 2019 ban targeted *household raw
  coal for heating*. Coal combustion emits mainly SO2 and particulates. Urban NO2 in
  Ulaanbaatar comes substantially from traffic and power plants, which the ban did not
  touch. This limitation is stated prominently in the README and in the talk. It is not
  a flaw to hide; it is a genuine MRV problem worth demonstrating.
- **The pre-ban record is short.** TROPOMI data begin mid-2018; the ban took effect
  15 May 2019. That leaves roughly one pre-ban winter. Any before/after comparison
  rests on a thin baseline and must carry uncertainty that reflects this.
- **No parameter is chosen after seeing results.** Bounding box, date ranges, and
  seasonal model form are fixed and documented before fitting. If any is changed
  later, the change and its reason are recorded in the README.
- **Units stay as retrieved** (mol/m^2). No conversion to surface concentration.
  Column density is not surface concentration and must never be described as such.

## 3. Data source (verified against the Earth Engine catalog)

- Collection: `COPERNICUS/S5P/OFFL/L3_NO2`
- Band: `tropospheric_NO2_column_number_density` (mol/m^2)
- Native pixel size: 1113.2 m
- **QA filtering already applied upstream.** Earth Engine removes pixels with
  qa_value < 0.75 for this band before ingestion. Do not implement a second QA filter.
  Do state in the README that filtering happened upstream rather than not at all.
- Coverage: mid-2018 to present. OFFL (offline, reprocessed) — not NRTI.

Earth Engine project ID: `storied-depot-291800`

## 4. Environment

Windows 11, PowerShell 5.1, VS Code. **PowerShell does not support `&&`, `printf`,
or brace expansion** — write Windows-native commands only.

Python venv at `.venv/`. Dependencies: `earthengine-api`, `pandas`, `matplotlib`.
Nothing else without asking.

## 5. Repository layout

```
tsenher/
  data/raw/          # gitignored — intermediates only
  data/processed/    # COMMITTED — small aggregated CSVs, so the repo is reproducible
  scripts/           # numbered, run in order, each does one thing
  notebooks/         # exploration only; nothing load-bearing lives here
  figures/           # PNG output for slides
  README.md          # the actual deliverable alongside the figures
```

## 6. Build order

Each stage produces a committed artifact. Do not start a stage before the previous
one has output on disk.

| # | Script | Output |
|---|--------|--------|
| 01 | `01_ingest_no2.py` | `data/processed/no2_monthly_ub.csv` |
| 02 | `02_seasonal.py` | seasonal fit + residual series |
| 03 | `03_baseline.py` | pre/post comparison with bootstrap CIs |
| 04 | `04_figures.py` | three PNGs in `figures/` |

### Stage 01 specification

Monthly mean tropospheric NO2 over Ulaanbaatar, 2018-07-01 to present.

- Region: explicit `ee.Geometry.Rectangle` with hardcoded coordinates in the script.
  No shapefile upload — the region must be auditable by reading the file.
- Aggregate by mapping over an explicit month list. Do not call `.mean()` across the
  whole collection.
- Per month: `reduceRegion(ee.Reducer.mean(), region, scale=1113.2)`.
- **Also record `n_days`** — the number of images contributing to each month. Winter
  cloud and low solar elevation thin coverage badly at 47N. This column is required,
  not optional; it determines whether winter months are usable at all.
- Output columns exactly: `year, month, no2_mol_m2, n_days`.
- Fail loudly on missing months. Do not silently drop or interpolate.

## 7. Decisions reserved for the human author

Claude Code must **stop and ask** rather than choose these. They are the decisions
the author will be questioned on, and answering "the AI picked it" is not survivable
in that room.

- Bounding box extent (tight urban vs wide regional — a real signal/noise tradeoff)
- Seasonal model form and whether to fit in log space
- Which months, if any, are excluded for insufficient coverage, and the threshold
- Whether the before/after window is symmetric, and its width
- Every claim in the README about what the data show

## 8. Non-goals for this deadline

Explicitly out of scope before 25 August. Do not build these.

- Web dashboard or any deployed frontend (conference wifi is a failure mode; static
  figures cannot break)
- Machine learning of any kind
- SO2 or aerosol index analysis (worth attempting later; NO2 must land first)
- Multi-city comparison

## 9. Working style

- Small commits, one concept each.
- Every script runs standalone from the repo root.
- Print intermediate shapes and row counts; silent success is not success.
- If something cannot be verified, say so in the output rather than assuming.
