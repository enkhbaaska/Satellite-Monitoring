"""Shared style and constants for the diagnostic figures.

Imported by the fig_*.py scripts. Not a stage script; it produces nothing on
its own. Kept separate so the version boundaries and the palette are defined
once rather than drifting between figures.

NOTE: scripts/fig_coverage_and_signal.py (figure 02) predates this module and
still carries its own copy of these constants. They agree today. Unifying it
would mean editing a figure that is already approved, so it has been left
alone deliberately.

Palette provenance: the two series colours were validated with the dataviz
skill's validate_palette.js (light mode, surface #fcfcfb): CVD dE 24.7
protan, normal-vision dE 33.6, both slots >= 3:1 contrast. The season and
year-ramp colours below could NOT be re-validated -- the skill's script was
no longer on disk when these figures were built -- so figures that use them
encode the same variable redundantly (panel position, or line labels) and
never rely on colour alone.
"""

from datetime import datetime
from pathlib import Path

import matplotlib.dates as mdates
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = REPO_ROOT / "data" / "processed" / "no2_monthly_ub.csv"
FIG_DIR = REPO_ROOT / "figures"

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
INK_3 = "#8a8984"
GRID = "#e6e5e0"
SPINE = "#d8d7d2"

SERIES = {"UB_METRO": "#2a78d6", "UB_RURAL": "#eb6834"}

COLLAPSE = "#f4c2c2"
COLLAPSE_ALPHA = 0.85

# Meteorological seasons. DJF is named for the January it ends in.
SEASONS = {
    "winter (DJF)": (12, 1, 2),
    "spring (MAM)": (3, 4, 5),
    "summer (JJA)": (6, 7, 8),
    "autumn (SON)": (9, 10, 11),
}
SEASON_COLORS = {
    "winter (DJF)": "#2a78d6",
    "spring (MAM)": "#1baf7a",
    "summer (JJA)": "#eb6834",
    "autumn (SON)": "#4a3aa7",
}

BAN_DATE = datetime(2019, 5, 15)

# First month in which each new ALGORITHM_VERSION appears, read off every
# month of the collection by scratch/probe_version_timeline.py. Each
# transition spans two months: a mixed month, then the new version alone.
VERSION_BOUNDARIES = [
    ("2019-03", "1.3.0"),
    ("2020-11", "1.4.0"),
    ("2021-07", "1.5.0"),
    ("2022-07", "1.6.0"),
    ("2024-11", "1.7.0"),
    ("2025-11", "1.8.0"),
]

# Which ALGORITHM_VERSION each Dec-Jan-Feb winter ran under, derived from the
# boundaries above. A winter is named for the December that opens it. Every
# winter listed is version-pure across all three of its months.
WINTER_VERSION = {
    "2018-19": "1.0.0",
    "2019-20": "1.3.0",
    "2020-21": "1.4.0",
    "2021-22": "1.5.0",
    "2022-23": "1.6.0",
    "2023-24": "1.6.0",
    "2024-25": "1.7.0",
    "2025-26": "1.8.0",
}

RCPARAMS = {
    "font.size": 10,
    "text.color": INK,
    "axes.labelcolor": INK_2,
    "xtick.color": INK_2,
    "ytick.color": INK_2,
    "figure.facecolor": SURFACE,
    "axes.facecolor": SURFACE,
    "savefig.facecolor": SURFACE,
}

FOOTNOTE = (
    "COPERNICUS/S5P/OFFL/L3_NO2, tropospheric_NO2_column_number_density. "
    "Monthly means, qa >= 0.75 applied upstream. Gaps are gaps: no interpolation, "
    "no smoothing. Column density, not surface concentration."
)


def load():
    """The stage 01 output, with a datetime column and a season label."""
    if not CSV_PATH.exists():
        raise SystemExit(f"FAIL: {CSV_PATH} not found -- run 01_ingest_no2.py first")
    df = pd.read_csv(CSV_PATH)
    df["date"] = [datetime(int(r.year), int(r.month), 1) for r in df.itertuples()]
    df["season"] = [season_of(int(m)) for m in df["month"]]
    return df.sort_values(["box", "date"]).reset_index(drop=True)


def season_of(month):
    for name, months in SEASONS.items():
        if month in months:
            return name
    raise ValueError(month)


def winter_label(year, month):
    """Winter label for a Dec/Jan/Feb month, else None.

    December belongs to the winter it opens; January and February to the
    winter that opened the previous December.
    """
    if month == 12:
        return f"{year}-{str(year + 1)[2:]}"
    if month in (1, 2):
        return f"{year - 1}-{str(year)[2:]}"
    return None


def ym_date(ym):
    return datetime(int(ym[:4]), int(ym[5:7]), 1)


def draw_version_lines(axes, label_ax=None, label_y=1.005):
    """Dashed ALGORITHM_VERSION boundaries on every axis given."""
    for ym, label in VERSION_BOUNDARIES:
        x = ym_date(ym)
        for ax in axes:
            ax.axvline(x, color=INK_3, lw=0.9, ls=(0, (4, 3)), zorder=1)
        if label_ax is not None:
            label_ax.text(
                x, label_y, f"v{label}",
                transform=label_ax.get_xaxis_transform(),
                fontsize=8, color=INK_3, ha="center", va="bottom",
            )


def draw_ban(axes):
    for ax in axes:
        ax.axvline(BAN_DATE, color=INK, lw=1.7, zorder=2)


def collapse_spans(df, thin):
    """Contiguous month runs where EITHER box falls below `thin`.

    Derived from the data so the shading cannot drift from the series. Padded
    half a month each side: points sit at the first of the month, so an
    unpadded band would begin exactly on the peak it is meant to contain.
    """
    worst = df.groupby(["year", "month"])["n_obs"].min().reset_index()
    worst["date"] = [datetime(int(r.year), int(r.month), 1) for r in worst.itertuples()]
    worst = worst.sort_values("date")

    spans, start, prev = [], None, None
    for r in worst.itertuples():
        below = r.n_obs < thin
        if below and start is None:
            start = r.date
        elif not below and start is not None:
            spans.append((start, prev))
            start = None
        prev = r.date
    if start is not None:
        spans.append((start, prev))
    pad = pd.Timedelta(days=15)
    return [(a - pad, b + pad) for a, b in spans]


def shade_collapse(axes, spans):
    for a, b in spans:
        for ax in axes:
            ax.axvspan(a, b, color=COLLAPSE, alpha=COLLAPSE_ALPHA, zorder=0, lw=0)


def finish(ax, yaxis_grid=True):
    if yaxis_grid:
        ax.grid(axis="y", color=GRID, lw=0.8, zorder=0)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(SPINE)


def time_axis(ax, lo=datetime(2018, 6, 1), hi=datetime(2026, 10, 1)):
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.xaxis.set_minor_locator(mdates.MonthLocator(bymonth=(1, 4, 7, 10)))
    ax.set_xlim(lo, hi)


def footnote(fig, y=-0.075, x=0.008):
    fig.text(x, y, FOOTNOTE, fontsize=7.5, color=INK_3)


def lerp_hex(c1, c2, t):
    """Blend two hex colours. Used for the year ramp in figure 06."""
    a = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * t):02x}" for x, y in zip(a, b))


def save(fig, name):
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    path = FIG_DIR / name
    fig.savefig(path, dpi=200, bbox_inches="tight")
    print(f"\nwrote {path.relative_to(REPO_ROOT)}")
    return path
