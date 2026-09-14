"""Figure: the NO2 winter peaks are coverage artifacts.

Writes figures/02_coverage_and_signal.png from data/processed/no2_monthly_ub.csv.

This sits outside the numbered build order of PROJECT.md section 6. It depends
only on stage 01 output, not on stages 02 or 03, and it carries the headline
result recorded in section 1: the archive discontinuities.

The figure must read without a caption, so the panel titles state the finding
rather than naming the axes.

Version boundaries are hardcoded from scratch/probe_version_timeline.py, which
read ALGORITHM_VERSION off every month of the collection. Each transition spans
two months -- a mixed month, then the new version alone. The line is drawn at
the first month the new version appears.
"""

import sys
from datetime import datetime
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

REPO_ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = REPO_ROOT / "data" / "processed" / "no2_monthly_ub.csv"
OUT_PATH = REPO_ROOT / "figures" / "02_coverage_and_signal.png"

# Validated with the dataviz palette validator, light mode, surface #fcfcfb:
# CVD dE 24.7 (protan), normal-vision dE 33.6, both slots >= 3:1 contrast.
SERIES = {"UB_METRO": "#2a78d6", "UB_RURAL": "#eb6834"}
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
INK_3 = "#8a8984"
# The collapse bands are the load-bearing element of this figure: if they do
# not survive projection, the top panel reads as a real winter signal. Opaque
# enough to be obvious across a room, still light enough that the 2px series
# lines stay legible on top of them.
COLLAPSE = "#f4c2c2"
COLLAPSE_ALPHA = 0.85

BAN_DATE = datetime(2019, 5, 15)

# (first month the new version appears, label)
VERSION_BOUNDARIES = [
    ("2019-03", "1.3.0"),
    ("2020-11", "1.4.0"),
    ("2021-07", "1.5.0"),
    ("2022-07", "1.6.0"),
    ("2024-11", "1.7.0"),
    ("2025-11", "1.8.0"),
]

# Display cut only. Nothing is filtered, weighted, or dropped on this value,
# and the real exclusion threshold remains a decision reserved to the author.
THIN = 5.0


def ym_to_date(y, m):
    return datetime(int(y), int(m), 1)


def collapse_spans(df):
    """Contiguous month runs where EITHER box falls below the display cut.

    Derived from the data rather than typed in, so the shading cannot drift
    away from what the series actually shows.
    """
    worst = df.groupby(["year", "month"])["n_obs"].min().reset_index()
    worst["date"] = [ym_to_date(r.year, r.month) for r in worst.itertuples()]
    worst = worst.sort_values("date")

    spans, start, prev = [], None, None
    for r in worst.itertuples():
        thin = r.n_obs < THIN
        if thin and start is None:
            start = r.date
        elif not thin and start is not None:
            spans.append((start, prev))
            start = None
        prev = r.date
    if start is not None:
        spans.append((start, prev))

    # Pad each span by half a month at both ends. Points are plotted at the
    # first of the month, so an unpadded band would start exactly on the peak
    # it is meant to contain and the peak would read as sitting outside it.
    return [(a - pd.Timedelta(days=15), b + pd.Timedelta(days=15)) for a, b in spans]


def main():
    if not CSV_PATH.exists():
        print(f"FAIL: {CSV_PATH} not found -- run 01_ingest_no2.py first", file=sys.stderr)
        return 1

    df = pd.read_csv(CSV_PATH)
    df["date"] = [ym_to_date(r.year, r.month) for r in df.itertuples()]
    df = df.sort_values(["box", "date"])
    print(f"loaded {len(df)} rows, {df['date'].min():%Y-%m} to {df['date'].max():%Y-%m}")
    print(f"NaN no2_mol_m2: {int(df['no2_mol_m2'].isna().sum())} (left as gaps)")

    spans = collapse_spans(df)
    print(f"collapse spans (n_obs < {THIN}): {[(a.strftime('%Y-%m'), b.strftime('%Y-%m')) for a, b in spans]}")

    plt.rcParams.update({
        "font.size": 10,
        "text.color": INK,
        "axes.labelcolor": INK_2,
        "xtick.color": INK_2,
        "ytick.color": INK_2,
        "figure.facecolor": SURFACE,
        "axes.facecolor": SURFACE,
        "savefig.facecolor": SURFACE,
    })

    fig, (ax_top, ax_bot) = plt.subplots(
        2, 1, figsize=(13, 8.5), sharex=True,
        gridspec_kw={"height_ratios": [2.1, 1], "hspace": 0.13},
    )

    # --- shading first, so data marks sit above it -------------------------
    for a, b in spans:
        for ax in (ax_top, ax_bot):
            ax.axvspan(a, b, color=COLLAPSE, alpha=COLLAPSE_ALPHA, zorder=0, lw=0)

    # --- version boundaries and the ban ------------------------------------
    for ym, label in VERSION_BOUNDARIES:
        x = datetime(int(ym[:4]), int(ym[5:7]), 1)
        for ax in (ax_top, ax_bot):
            ax.axvline(x, color=INK_3, lw=0.9, ls=(0, (4, 3)), zorder=1)
        ax_top.text(
            x, 1.005, f"v{label}", transform=ax_top.get_xaxis_transform(),
            fontsize=8, color=INK_3, ha="center", va="bottom",
        )

    for ax in (ax_top, ax_bot):
        ax.axvline(BAN_DATE, color=INK, lw=1.7, zorder=2)

    # --- data --------------------------------------------------------------
    for box, color in SERIES.items():
        g = df[df["box"] == box]
        ax_top.plot(g["date"], g["no2_mol_m2"], color=color, lw=2, zorder=4,
                    solid_capstyle="round")
        ax_bot.plot(g["date"], g["n_obs"], color=color, lw=2, zorder=4,
                    solid_capstyle="round")

    ax_bot.axhline(THIN, color=INK_3, lw=1, ls=(0, (2, 3)), zorder=3)
    ax_bot.text(
        datetime(2025, 9, 1), THIN + 0.9, f"n_obs = {THIN:.0f}",
        fontsize=8, color=INK_3, va="bottom",
    )

    # --- the point of the figure, said in the panel titles ------------------
    ax_top.set_title(
        "Every winter spike in the shaded bands is an artifact of missing data",
        fontsize=13, color=INK, loc="left", pad=26, fontweight="bold",
    )
    ax_bot.set_title(
        "...because in exactly those months the satellite saw almost nothing",
        fontsize=12, color=INK, loc="left", pad=8, fontweight="bold",
    )

    ax_top.set_ylabel("tropospheric NO$_2$ column\n(mol/m$^2$)", color=INK_2)
    ax_bot.set_ylabel("observations\nper grid cell", color=INK_2)

    # --- annotate the worst artifact ---------------------------------------
    worst = df.loc[df["no2_mol_m2"].idxmax()]
    ax_top.annotate(
        f"{worst['box']} Dec 2020\n{worst['no2_mol_m2']:.2e} mol/m$^2$ "
        f"-- the highest value\nin the record, from {worst['n_obs']:.2f} obs/cell",
        xy=(worst["date"], worst["no2_mol_m2"]),
        xytext=(datetime(2021, 4, 15), worst["no2_mol_m2"] * 1.0),
        fontsize=9, color=INK, va="top",
        arrowprops=dict(arrowstyle="->", color=INK_2, lw=1.1,
                        connectionstyle="arc3,rad=0.15"),
    )

    # The gap is a coverage fact, so it is annotated on the coverage panel,
    # where the collapse leaves empty space to put it in.
    gap = df[df["no2_mol_m2"].isna()]
    if not gap.empty:
        gd = gap.iloc[0]
        ax_bot.annotate(
            "UB_RURAL Jan 2021: 0 of 3600 cells, all 31 days",
            xy=(gd["date"], 0.4), xytext=(datetime(2018, 6, 25), 9.2),
            fontsize=9, color=INK, va="center",
            arrowprops=dict(arrowstyle="->", color=INK_2, lw=1.1,
                            connectionstyle="arc3,rad=-0.12"),
        )

    # --- the ban / version-change collision --------------------------------
    ax_top.annotate(
        "raw coal ban\n15 May 2019",
        xy=(BAN_DATE, 0.97), xycoords=("data", "axes fraction"),
        xytext=(6, 0), textcoords="offset points",
        fontsize=9.5, color=INK, va="top", fontweight="bold",
    )
    ax_top.annotate(
        "retrieval switched 1.0.0$\\rightarrow$1.3.0\nsix weeks earlier",
        xy=(datetime(2019, 3, 1), 0.62), xycoords=("data", "axes fraction"),
        xytext=(datetime(2018, 8, 15), 0.72), textcoords=("data", "axes fraction"),
        fontsize=8.5, color=INK_2,
        arrowprops=dict(arrowstyle="->", color=INK_3, lw=1,
                        connectionstyle="arc3,rad=0.2"),
    )

    # --- direct labels at the series ends, plus a legend --------------------
    for box, color in SERIES.items():
        g = df[df["box"] == box].dropna(subset=["no2_mol_m2"])
        last = g.iloc[-1]
        ax_top.annotate(
            box, xy=(last["date"], last["no2_mol_m2"]),
            xytext=(6, 0), textcoords="offset points",
            fontsize=9, color=color, va="center", fontweight="bold",
        )

    handles = [Line2D([0], [0], color=c, lw=2, label=b) for b, c in SERIES.items()]
    handles += [
        Line2D([0], [0], color=INK, lw=1.7, label="raw coal ban (15 May 2019)"),
        Line2D([0], [0], color=INK_3, lw=0.9, ls=(0, (4, 3)),
               label="ALGORITHM_VERSION change"),
        Patch(facecolor=COLLAPSE, alpha=COLLAPSE_ALPHA,
              label=f"coverage collapse (n_obs < {THIN:.0f})"),
    ]
    # The legend lives below the axes: inside the top panel it collided with
    # the annotation pointing at the Dec 2020 artifact, and that annotation is
    # the whole point of the figure.
    fig.legend(
        handles=handles, loc="lower center", bbox_to_anchor=(0.5, -0.035),
        frameon=False, fontsize=9.5, ncol=5, labelcolor=INK_2,
        handlelength=1.8, columnspacing=2.2,
    )

    # --- axes finish --------------------------------------------------------
    for ax in (ax_top, ax_bot):
        ax.grid(axis="y", color="#e6e5e0", lw=0.8, zorder=0)
        ax.set_axisbelow(True)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        for side in ("left", "bottom"):
            ax.spines[side].set_color("#d8d7d2")
        ax.margins(x=0.01)

    ax_bot.xaxis.set_major_locator(mdates.YearLocator())
    ax_bot.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax_bot.xaxis.set_minor_locator(mdates.MonthLocator(bymonth=(1, 4, 7, 10)))
    ax_bot.set_xlim(datetime(2018, 6, 1), datetime(2026, 10, 1))
    ax_bot.set_ylim(bottom=0)

    # The negative UB_RURAL column in Dec 2020 is real retrieval noise off a
    # near-empty month, and it is evidence. Give it headroom rather than
    # letting the axis clip it out of sight.
    lo = float(df["no2_mol_m2"].min())
    hi = float(df["no2_mol_m2"].max())
    ax_top.set_ylim(lo - 0.10 * (hi - lo), hi + 0.06 * (hi - lo))
    print(f"top panel y-range: {lo:.3e} to {hi:.3e} (min is negative: {lo < 0})")

    fig.text(
        0.008, -0.075,
        "COPERNICUS/S5P/OFFL/L3_NO2, tropospheric_NO2_column_number_density. "
        "Monthly means, qa >= 0.75 applied upstream. Gaps are gaps: no interpolation. "
        "Column density, not surface concentration.",
        fontsize=7.5, color=INK_3,
    )

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_PATH, dpi=200, bbox_inches="tight")
    print(f"wrote {OUT_PATH.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
