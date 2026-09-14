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

### Update — 2026-08-19: the headline result has changed

The framing above stands. What changed is what the worked example actually found.

Ingestion is complete (194 box-months, 2018-07 to 2026-07) and the reference data
does not support a clean before/after comparison. Two archive discontinuities,
both documented with evidence in section 6 under C3 and C4:

1. **A three-winter hole.** Coverage over Ulaanbaatar collapses from ~20
   observations per grid cell to near zero between December 2020 and February 2023,
   then recovers completely. The cause is identified: snow-covered scenes were
   assigned `qa_value` below the 0.75 cutoff and stripped upstream. Onset tracks the
   `ALGORITHM_VERSION` 1.3.0 to 1.4.0 boundary; recovery tracks the retirement of
   NISE, the snow/ice auxiliary input, in November 2023. The Gobi and Beijing are
   unaffected across the same months, so this is specific to persistently
   snow-covered surfaces, not a general outage.

2. **A retrieval-version break across the intervention.** The sole pre-ban winter
   is retrieved with ALGORITHM_VERSION 1.0.0; every post-ban period uses 1.3.0
   through 1.7.0. No reprocessed, version-homogeneous NO2 collection exists in the
   Earth Engine catalog — only OFFL and NRTI, and NRTI carries the same version
   split. A before/after step in this series cannot be attributed to the coal ban
   rather than to the retrieval changing underneath it.

**These discontinuities are the headline result.** The project set out to test
whether independent verification is possible without institutional budgets. It is —
and the first thing independent verification finds is that the reference archive has
a hole across three of the seven post-intervention winters and a processing break
across the intervention date. That is a concrete, reproducible MRV failure mode,
demonstrated rather than asserted, and it is a stronger contribution to that room
than a clean NO2 trend would have been.

This does not license abandoning the NO2 analysis. Stages 02 to 04 still run, and
the seasonal and before/after work still gets done and reported honestly — including
the possibility that it is uninformative. The change is to what the talk leads with,
not to what gets built.

One consequence to carry forward: the surviving pixels in collapsed months are not
merely few, they are unrepresentative. December 2020 in UB_METRO has n_obs 0.07 and
returns 1.37e-04 mol/m^2, the largest value anywhere in the series; UB_RURAL the same
month returns a negative column. Any figure plotting the raw monthly series will be
dominated by these artifacts unless coverage is shown alongside it.

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

#### Corrections to the stage 01 specification — 2026-08-19

The bullets above are left as originally written. The following supersede them.
Both corrections were made **before** any NO2 values were examined; they arose from
a coverage diagnostic (`scratch/check_coverage.py`), not from looking at results.

**C1 — Output columns.** Superseded by: `year, month, box, no2_mol_m2, n_obs`.

Two boxes are ingested rather than one, so a `box` column is required to
distinguish them:

- `UB_METRO = [106.45, 47.70, 107.35, 48.10]`
- `UB_RURAL = [106.55, 48.35, 107.45, 48.75]`

**C2 — `n_days` is renamed `n_obs`, and its definition changes.** It is now the
*mean number of valid observations per grid cell* in that box that month.

The original definition — "the number of images contributing to each month" — cannot
be computed. `harpconvert`'s `bin_spatial` writes every orbit onto a global grid, so
each S5P L3 image carries a footprint of `[-180,-90,180,90]` and intersects every
region on Earth. `filterBounds` is a no-op and `.size()` returns the global orbit
count (~430/month), identical for every box and blind to local coverage. Verified
directly: for 2024-01-05 the filtered and unfiltered collections both hold 15 images.
Observations per cell measures what the column was for — whether a month is usable.

**C3 — "Winter cloud and low solar elevation thin coverage badly at 47N" is wrong.**
Measured coverage runs the other way. Mean observations per grid cell, 2023–24:

| | UB_METRO | UB_RURAL |
|---|---|---|
| Dec 2023 | 29.1 | 30.3 |
| Jan 2024 | 37.6 | 36.8 |
| Feb 2024 | 33.1 | 33.7 |
| Jun 2023 | 23.5 | 25.8 |
| Jul 2023 | **15.2** | 21.8 |
| Aug 2023 | 25.6 | 29.4 |

Winter coverage exceeds summer by roughly 50% across the season. The thinnest month
in the record is **July**, coinciding with Ulaanbaatar's summer rainfall peak, not
any winter month. At 47.9N the December noon solar zenith angle stays near 71°, well
inside the usable retrieval range, and the winter Siberian high keeps skies dry and
clear.

Scope of this correction: it concerns *data availability only*. It does not claim
winter retrievals are equally **accurate** — column retrievals under strong
wintertime surface inversions carry their own biases, and that remains an open
caveat for the README. The evidence is also a single year (2023–24); `n_obs` is
recorded for every month precisely so the full record can be checked rather than
assumed. Whether any month is excluded, and on what threshold, remains a decision
reserved for the human author under section 7.

#### C3 IS RETRACTED — 2026-08-19, same day

C3 is wrong. It is left above, unedited, because the mistake is instructive and
because silently deleting it would be the same failure it came from.

C3 generalised from **one winter, 2023–24**, which the full record now shows is one
of the *good* ones. Running the same measurement across the entire archive
(`scratch/probe_gap.py`) gives, for UB_METRO, mean observations per grid cell:

| year | Jan | Feb | Mar | Apr | May | Jun | Jul | Aug | Sep | Oct | Nov | Dec |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2018 | | | | | | 18.6 | 20.1 | 21.9 | 33.0 | 31.2 | 22.8 | |
| 2019 | 27.4 | 30.1 | 33.8 | 21.6 | 26.7 | 20.2 | 15.5 | 22.0 | 32.8 | 33.5 | 14.0 | 19.7 |
| 2020 | 42.6 | 35.7 | 36.3 | 34.7 | 18.9 | 16.5 | 22.3 | 17.3 | 26.2 | 30.4 | 19.7 | **1.2** |
| 2021 | **1.6** | **1.9** | 12.0 | 16.9 | 14.5 | 18.5 | 19.3 | 18.0 | 22.9 | 22.8 | 20.3 | **2.9** |
| 2022 | **4.9** | **3.3** | 16.0 | 25.4 | 26.2 | 21.6 | 22.6 | 24.3 | 32.0 | 23.8 | **4.3** | **1.1** |
| 2023 | **1.7** | **2.3** | 23.4 | 20.6 | 16.4 | 23.6 | 15.5 | 25.6 | 20.7 | 37.8 | 15.8 | 29.3 |
| 2024 | 37.9 | 33.3 | 36.3 | 25.4 | 26.9 | 21.1 | 23.0 | 19.9 | 23.3 | 28.6 | 23.3 | 17.5 |
| 2025 | 23.5 | 26.9 | 23.9 | 33.9 | 23.0 | 17.3 | 25.7 | 21.8 | 23.3 | 24.3 | 22.8 | 22.2 |
| 2026 | 24.7 | 24.5 | 28.2 | 27.3 | 20.3 | 13.9 | 20.0 | | | | | |

UB_RURAL shows the same shape. **Three consecutive winters — 2020-21, 2021-22,
2022-23 — are effectively empty in both boxes**, falling from ~20 obs/cell in
Nov 2020 to ~1 in Dec 2020 and not recovering until Dec 2023. January 2021 in
UB_RURAL has *zero* valid cells out of 3600, on all 31 days.

The pattern is neither "winter is thin" (2018-19, 2019-20, 2023-24, 2024-25 and
2025-26 winters are all fine) nor "winter is fine" (three winters are unusable).
It is **era-dependent**, and no seasonal generalisation covers it.

The collapse is specific to this latitude. Measuring the same winters at three
latitudes (`scratch/probe_mechanism.py`):

| month | UB 47.9N | Gobi 43.5N | Beijing 40.0N |
|---|---|---|---|
| 2019-01 | 27.4 | 36.0 | 29.5 |
| 2020-01 | 42.6 | 30.5 | 28.0 |
| 2020-12 | **1.2** | 12.8 | 34.0 |
| 2021-01 | **1.6** | 26.0 | 34.5 |
| 2021-12 | **2.9** | 27.4 | 34.9 |
| 2022-12 | **1.1** | 32.3 | 34.4 |
| 2023-01 | **1.7** | 18.8 | 34.3 |
| 2024-01 | 37.9 | 22.6 | 28.4 |
| 2025-01 | 23.5 | 33.7 | 36.0 |

Gobi and Beijing are unaffected throughout, which rules out a global processing
outage and points at the retrieval's handling of persistent snow cover — TROPOMI
lowers `qa_value` over bright snow/ice scenes, and the upstream `qa >= 0.75`
filter then removes them.

**Mechanism, from image metadata (`scratch/probe_version.py`):** the collapse and
the recovery each coincide with a named boundary in the product itself.

| month | ALGORITHM_VERSION | PROCESSOR_VERSION | STATUS_NISE__ | UB n_obs |
|---|---|---|---|---|
| 2019-12 | 1.3.0 | 1.3.2 | Nominal | 19.7 |
| 2020-01 | 1.3.0 | 1.3.2 | Nominal | 42.6 |
| 2020-11 | 1.3.0 x398, 1.4.0 x27 | mixed | Nominal | 19.7 |
| 2020-12 | **1.4.0** | 1.4.0 | Nominal | **1.2** |
| 2021-01 | 1.4.0 | 1.4.0 | Nominal | **1.6** |
| 2021-12 | 1.5.0 | 2.3.1 | Nominal | **2.9** |
| 2022-12 | 1.6.0 | 2.4.0 | Nominal | **1.1** |
| 2023-11 | 1.6.0 | 2.5.0 / 2.6.0 | Nominal x355, **Retired** x70 | 15.8 |
| 2023-12 | 1.6.0 | 2.6.0 | **Retired** | **29.3** |
| 2024-01 | 1.6.0 | 2.6.0 | Retired | 37.9 |

Onset is the `ALGORITHM_VERSION` 1.3.0 → **1.4.0** boundary in Nov/Dec 2020.
Recovery is the retirement of **NISE** (NSIDC's Near-real-time Ice and Snow Extent,
the snow/ice auxiliary input) in Nov/Dec 2023 — coverage returns in the very month
`STATUS_NISE__` flips to `Retired`. The collapse persisted across two intervening
processor upgrades (2.3.1, 2.4.0) and ended only when the snow/ice input changed,
which is what identifies the snow/ice flag rather than the processor generally.

This is a defensible, checkable story: coverage over Ulaanbaatar was destroyed for
three winters by how snow-covered scenes were flagged, not by cloud or solar
elevation. It is arguably a better MRV finding than the NO2 series itself.

**Note on the n_obs figures in the C3 tables.** Those tables were produced before
`01_ingest_no2.py` was corrected to `unmask(0)` prior to averaging. They average
only over cells holding at least one observation, so they *understate* the collapse:
a month where 91 of 3600 cells were seen once reads as 1.0 there but 0.07 in the
CSV, which averages over every cell in the box. The CSV carries the correct figure.
The tables are left as-is because their shape — which winters collapse, and when —
is unaffected, and they are the evidence the mechanism was identified from.

#### C4 — the retrieval version is NOT homogeneous across the ban date

New finding, 2026-08-19, from the same metadata. This affects section 2, not just
section 6, and is the most serious issue found so far.

The archive has not been uniformly reprocessed. Across the 15 May 2019 intervention:

| period | ALGORITHM_VERSION | PROCESSOR_VERSION |
|---|---|---|
| 2018-12 (sole pre-ban winter) | 1.0.0 | 1.2.2 |
| 2019-01 (pre-ban) | 1.0.0 | 1.2.2 |
| 2019-12 / 2020-01 (post-ban) | 1.3.0 | 1.3.2 |
| 2023-12 / 2024-01 (post-ban) | 1.6.0 | 2.6.0 |
| 2025-01 (post-ban) | 1.7.0 | 2.8.0 |

The pre-ban baseline is retrieved with a **different algorithm version** from every
post-ban period it would be compared against. TROPOMI v2.x is documented to shift
retrieved tropospheric NO2 columns relative to v1.x, and the shift is not uniform —
it is largest in polluted, high-albedo, low-sun conditions, which is precisely
wintertime Ulaanbaatar.

**A before/after step change in this series cannot currently be attributed to the
coal ban rather than to the retrieval version changing underneath it.** The two are
confounded by construction. This is not a caveat to soften in the README; it may be
the finding.

Not yet done, and required before any before/after claim: quantify the version
effect against the S5P product release notes, and check whether a PAL/reprocessed
homogeneous series covering 2018-2019 exists in the catalog. No magnitude for the
version shift is asserted here because none has been verified.

**Consequences for the analysis, all reserved to the author under section 7:**

- The ban took effect 15 May 2019. Usable winters are 2018-19 (the single pre-ban
  winter), 2019-20, then a three-winter hole, then 2023-24 onward. Any before/after
  window straddles that gap.
- A gap of this size is not a nuisance to be interpolated across. It is a finding
  about MRV — an independent verifier hits exactly this, and saying so is worth
  more than a clean-looking series.
- `01_ingest_no2.py` currently refuses to write the CSV because UB_RURAL 2021-01
  has no data at all. How missing months are represented is an open decision.

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
