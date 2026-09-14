"""Stage 01 -- monthly mean tropospheric NO2 over two Ulaanbaatar boxes.

Reads COPERNICUS/S5P/OFFL/L3_NO2 and writes one row per box per calendar
month to data/processed/no2_monthly_ub.csv.

Units are left exactly as retrieved: mol/m^2, a tropospheric COLUMN density.
This is not a surface concentration and must never be described as one.

QA: no filtering is applied here, deliberately. The Earth Engine catalog
states the source is already filtered to drop pixels with qa_value < 0.75
during the harpconvert L2->L3 step, and the qa band does not survive that
conversion -- so a second filter is impossible, not merely redundant.

Run from anywhere; paths resolve relative to the repo root.
"""

import sys
from datetime import date
from pathlib import Path

import ee
import pandas as pd

PROJECT = "storied-depot-291800"
COLLECTION = "COPERNICUS/S5P/OFFL/L3_NO2"
BAND = "tropospheric_NO2_column_number_density"
SCALE = 1113.2  # L3 grid spacing. Native footprint is ~3.5 x 5.5 km.

# Region definitions are hardcoded so the analysis is auditable by reading
# this file. No shapefile upload. [W, S, E, N] in degrees.
BOXES = {
    "UB_METRO": [106.45, 47.70, 107.35, 48.10],
    "UB_RURAL": [106.55, 48.35, 107.45, 48.75],
}

START_YEAR, START_MONTH = 2018, 7  # TROPOMI record opens mid-2018

REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_PATH = REPO_ROOT / "data" / "processed" / "no2_monthly_ub.csv"

# Earth Engine returns null for a month with no usable data. Nulls do not
# survive Feature properties reliably, so the server substitutes this
# sentinel and the client converts it back to a missing value.
MISSING = -999.0


def month_list(end_year, end_month):
    """Explicit list of 'YYYY-MM-01' strings, inclusive of the end month.

    The months are enumerated here and mapped over one at a time. The whole
    collection is never averaged with a single .mean() -- that would silently
    weight months by how many images each happens to contain.
    """
    out = []
    y, m = START_YEAR, START_MONTH
    while (y, m) <= (end_year, end_month):
        out.append(f"{y}-{m:02d}-01")
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def month_feature(ms, coll, geom):
    """Server-side reduction for one month over one box.

    n_obs is the MEAN NUMBER OF VALID OBSERVATIONS PER GRID CELL, not a count
    of images. An image count cannot be used: harpconvert's bin_spatial writes
    every orbit onto a global grid, so each S5P L3 image carries a footprint of
    [-180,-90,180,90] and intersects every region on Earth. filterBounds is
    therefore a no-op and .size() returns the global orbit count (~430/month),
    identical for every box and blind to local coverage. Counting valid
    observations per cell is what actually reveals whether a month is usable.
    """
    start = ee.Date(ms)
    sub = coll.filterDate(start, start.advance(1, "month"))

    mean_d = sub.mean().reduceRegion(
        ee.Reducer.mean(), geom, SCALE, maxPixels=int(1e9)
    )
    # unmask(0) before averaging so the mean runs over EVERY cell in the box.
    # Without it the reduction averages only cells that hold >=1 observation,
    # which reports a month where 91 of 3600 cells were seen once as "1.0"
    # -- indistinguishable from full coverage at depth 1. Cells with nothing
    # are genuine zeros and must be counted as such.
    obs_d = (
        sub.count()
        .unmask(0)
        .reduceRegion(ee.Reducer.mean(), geom, SCALE, maxPixels=int(1e9))
    )

    return ee.Feature(
        None,
        {
            "ym": ms,
            "no2": ee.Algorithms.If(mean_d.contains(BAND), mean_d.get(BAND), MISSING),
            "n_obs": ee.Algorithms.If(obs_d.contains(BAND), obs_d.get(BAND), MISSING),
        },
    )


def fetch_box(name, geom, months, coll):
    """Fetch all months for one box, one request per calendar year.

    Chunking by year keeps each server-side computation small enough to
    return, while holding the number of round trips to roughly one per year
    rather than one per month.
    """
    rows = []
    years = sorted({int(m[:4]) for m in months})
    for yr in years:
        chunk = [m for m in months if int(m[:4]) == yr]
        fc = ee.FeatureCollection([month_feature(m, coll, geom) for m in chunk])
        feats = fc.getInfo()["features"]
        for f in feats:
            p = f["properties"]
            # A reduction can report absence either way: the band key missing
            # (-> sentinel) or present but null. Both mean no usable data.
            no2 = None if p["no2"] in (MISSING, None) else p["no2"]
            # n_obs is always recorded. Where the box held no valid pixel at
            # all the reduction cannot return a mean, but the true count is
            # zero observations per cell, so record 0.0 rather than a blank.
            n_obs = 0.0 if p["n_obs"] in (MISSING, None) else p["n_obs"]
            rows.append(
                {
                    "year": int(p["ym"][:4]),
                    "month": int(p["ym"][5:7]),
                    "box": name,
                    "no2_mol_m2": no2,
                    "n_obs": n_obs,
                }
            )
        got = len(feats)
        print(f"  {name} {yr}: requested {len(chunk)} months, returned {got}")
        if got != len(chunk):
            raise RuntimeError(
                f"{name} {yr}: asked for {len(chunk)} months, got {got}"
            )
    return rows


def main():
    ee.Initialize(project=PROJECT)
    print(f"ee.Initialize OK  (project={PROJECT})")

    # "Present" means the last COMPLETE calendar month. A partial month would
    # produce a mean over a different number of days than every other row.
    today = date.today()
    end_year, end_month = (today.year - 1, 12) if today.month == 1 else (
        today.year,
        today.month - 1,
    )
    months = month_list(end_year, end_month)
    print(
        f"months: {len(months)} from {months[0][:7]} to {months[-1][:7]} "
        f"(today {today.isoformat()}; current month excluded as incomplete)"
    )
    print(f"boxes: {len(BOXES)} -> expecting {len(months) * len(BOXES)} rows")
    print(f"band: {BAND}")
    print(f"scale: {SCALE} m")

    coll = ee.ImageCollection(COLLECTION).select(BAND)

    rows = []
    for name, coords in BOXES.items():
        print(f"\n{name} = {coords}")
        rows.extend(fetch_box(name, ee.Geometry.Rectangle(coords), months, coll))

    df = pd.DataFrame(rows, columns=["year", "month", "box", "no2_mol_m2", "n_obs"])
    df = df.sort_values(["box", "year", "month"]).reset_index(drop=True)
    print(f"\ndataframe shape: {df.shape}")
    print(df.groupby("box").size().to_string())

    # A month with no usable data is written as a NaN no2_mol_m2 with its
    # n_obs recorded, not dropped and never interpolated. The archive gaps are
    # a finding in their own right -- see PROJECT.md section 6, C3/C4 -- so the
    # series must carry them visibly rather than close over them.
    #
    # The boxes are independent: a month absent in one box says nothing about
    # the other, and no row is invalidated by its neighbour. Every box-month
    # in the range gets exactly one row.
    #
    # A row-count mismatch is still a hard failure. That is a structural bug
    # in this script, not a statement about the data.
    expected = len(months) * len(BOXES)
    if len(df) != expected:
        print(f"\nFAIL: expected {expected} rows, built {len(df)}", file=sys.stderr)
        return 1

    df["n_obs"] = df["n_obs"].round(2)

    missing = df[df["no2_mol_m2"].isna()]
    print(f"\nmonths with no usable NO2 ({len(missing)} of {len(df)} rows):")
    if missing.empty:
        print("  none")
    else:
        for _, r in missing.iterrows():
            print(
                f"  {r['box']} {int(r['year'])}-{int(r['month']):02d}"
                f"   n_obs {r['n_obs']}"
            )

    print("\nhead:")
    print(df.head(3).to_string(index=False))
    print("tail:")
    print(df.tail(3).to_string(index=False))

    print("\nno2_mol_m2 range per box:")
    for name, g in df.groupby("box"):
        print(f"  {name}: {g['no2_mol_m2'].min():.3e} to {g['no2_mol_m2'].max():.3e}")

    # Reported, not acted on. Which months are excluded for thin coverage,
    # and the threshold, is a decision reserved for the human author. The
    # value 5 below is a display cut for inspection only -- nothing in this
    # script filters, weights, or drops on it.
    thin = df[df["n_obs"] < 5][["box", "year", "month", "no2_mol_m2", "n_obs"]]
    print(f"\nrows with n_obs < 5 ({len(thin)}) -- shown for inspection, not excluded:")
    print(thin.to_string(index=False))

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT_PATH, index=False)
    print(f"\nwrote {len(df)} rows to {OUT_PATH.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
