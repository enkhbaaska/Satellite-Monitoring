"""Figure 04: does metro minus rural behave differently from raw metro?

Writes figures/04_metro_minus_rural.png from data/processed/no2_monthly_ub.csv.

The premise under test: an effect of the instrument or the retrieval should hit
both boxes and largely cancel in the difference, while a change in city
emissions should not. If that holds, the difference is a cleaner signal than
the raw metro series.

Months where either box is NaN are gaps. Nothing is interpolated or smoothed.

The ratio panel needs care: UB_RURAL Dec 2020 is negative, so metro/rural that
month is negative and meaningless as a ratio rather than merely extreme. It is
plotted, not dropped, but flagged, and off-scale points are drawn at the axis
edge with their true value labelled.
"""

import sys

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

import _figstyle as S

THIN_DISPLAY = 5.0
RATIO_LO, RATIO_HI = -2.0, 8.0
DIFF_COLOR = "#4a3aa7"
RATIO_COLOR = "#1baf7a"


def build(df):
    """Wide frame: one row per month with metro, rural, difference, ratio."""
    wide = df.pivot(index="date", columns="box",
                    values=["no2_mol_m2", "n_obs"]).sort_index()
    out = pd.DataFrame({
        "date": wide.index,
        "metro": wide[("no2_mol_m2", "UB_METRO")].values,
        "rural": wide[("no2_mol_m2", "UB_RURAL")].values,
        "n_metro": wide[("n_obs", "UB_METRO")].values,
        "n_rural": wide[("n_obs", "UB_RURAL")].values,
    })
    out["diff"] = out["metro"] - out["rural"]
    out["ratio"] = out["metro"] / out["rural"]
    out["thin"] = (out["n_metro"] < THIN_DISPLAY) | (out["n_rural"] < THIN_DISPLAY)
    return out


def cv(series):
    """Coefficient of variation, a scale-free spread measure."""
    s = series.dropna()
    return float(s.std() / abs(s.mean())) if len(s) and s.mean() != 0 else float("nan")


def report(w):
    print("=" * 78)
    print("FIGURE 04 -- metro minus rural")
    print("=" * 78)

    show = w.copy()
    show["month"] = [d.strftime("%Y-%m") for d in show["date"]]
    cols = ["month", "metro", "rural", "diff", "ratio", "n_metro", "n_rural", "thin"]
    print("\nfull series:")
    with pd.option_context("display.max_rows", None, "display.width", 200):
        print(show[cols].to_string(index=False))

    good = w[~w["thin"]]
    thin = w[w["thin"]]

    print("\nspread, raw metro vs difference (coefficient of variation):")
    print(f"  all months   metro CV {cv(w['metro']):.3f}   diff CV {cv(w['diff']):.3f}")
    print(f"  good months  metro CV {cv(good['metro']):.3f}   diff CV {cv(good['diff']):.3f}")
    print(f"  thin months  metro CV {cv(thin['metro']):.3f}   diff CV {cv(thin['diff']):.3f}")

    corr = w[["metro", "rural"]].dropna().corr().iloc[0, 1]
    corr_good = good[["metro", "rural"]].dropna().corr().iloc[0, 1]
    print(f"\nmetro vs rural correlation: all {corr:+.3f}   good-coverage only {corr_good:+.3f}")

    print("\nthin months -- does the artifact cancel in the difference?")
    t = thin.copy()
    t["month"] = [d.strftime("%Y-%m") for d in t["date"]]
    t["diff_vs_metro"] = t["diff"] / t["metro"]
    print(t[["month", "metro", "rural", "diff", "diff_vs_metro"]].to_string(index=False))
    print(
        "  diff_vs_metro near 1.0 means the difference kept the whole spike;\n"
        "  near 0.0 means it cancelled."
    )

    off = w[(w["ratio"] < RATIO_LO) | (w["ratio"] > RATIO_HI)].dropna(subset=["ratio"])
    if not off.empty:
        print(f"\nratio points outside the plotted range [{RATIO_LO}, {RATIO_HI}]:")
        for r in off.itertuples():
            print(f"  {r.date:%Y-%m}: ratio {r.ratio:+.2f}  (rural {r.rural:.3e})")

    neg = w[w["rural"] < 0].dropna(subset=["rural"])
    if not neg.empty:
        print("\nmonths where rural column is negative (ratio is meaningless, not just extreme):")
        for r in neg.itertuples():
            print(f"  {r.date:%Y-%m}: rural {r.rural:.3e}, ratio {r.ratio:+.2f}")

    gaps = w[w["metro"].isna() | w["rural"].isna()]
    print(f"\ngaps (either box NaN): {len(gaps)}")
    for r in gaps.itertuples():
        print(f"  {r.date:%Y-%m}: metro {r.metro}, rural {r.rural}")


def main():
    df = S.load()
    w = build(df)
    report(w)

    plt.rcParams.update(S.RCPARAMS)
    fig, (ax_d, ax_r) = plt.subplots(
        2, 1, figsize=(13, 8), sharex=True,
        gridspec_kw={"height_ratios": [1.25, 1], "hspace": 0.16},
    )

    spans = S.collapse_spans(df, THIN_DISPLAY)
    S.shade_collapse([ax_d, ax_r], spans)
    S.draw_version_lines([ax_d, ax_r], label_ax=ax_d)
    S.draw_ban([ax_d, ax_r])

    ax_d.axhline(0, color=S.SPINE, lw=1, zorder=1)
    ax_d.plot(w["date"], w["diff"], color=DIFF_COLOR, lw=2, zorder=4,
              solid_capstyle="round")
    ax_d.set_ylabel("metro $-$ rural\n(mol/m$^2$)", color=S.INK_2)

    # Ratio, with off-scale points pinned to the edge and labelled.
    ax_r.axhline(1, color=S.SPINE, lw=1, zorder=1)
    ax_r.plot(w["date"], w["ratio"], color=RATIO_COLOR, lw=2, zorder=4,
              solid_capstyle="round")
    ax_r.set_ylim(RATIO_LO, RATIO_HI)
    ax_r.set_ylabel("metro $\\div$ rural", color=S.INK_2)

    off = w.dropna(subset=["ratio"])
    off = off[(off["ratio"] < RATIO_LO) | (off["ratio"] > RATIO_HI)]
    for r in off.itertuples():
        edge = RATIO_HI if r.ratio > RATIO_HI else RATIO_LO
        ax_r.plot([r.date], [edge], marker="^" if r.ratio > RATIO_HI else "v",
                  color=RATIO_COLOR, ms=9, zorder=6, clip_on=False)
        # Labels go INSIDE the axes: outside, they landed on the panel title
        # above and the year ticks below.
        ax_r.annotate(
            f"{r.ratio:+.1f}", xy=(r.date, edge),
            xytext=(0, -15 if r.ratio > RATIO_HI else 12),
            textcoords="offset points", fontsize=8.5, color=S.INK,
            ha="center", fontweight="bold",
        )

    ax_d.set_title(
        "The difference does NOT cancel the coverage artifacts",
        fontsize=13, color=S.INK, loc="left", pad=26, fontweight="bold",
    )
    ax_r.set_title(
        "...and the ratio is worse: it divides by a rural value that is itself unreliable",
        fontsize=12, color=S.INK, loc="left", pad=8, fontweight="bold",
    )

    handles = [
        Line2D([0], [0], color=DIFF_COLOR, lw=2, label="metro $-$ rural"),
        Line2D([0], [0], color=RATIO_COLOR, lw=2, label="metro $\\div$ rural"),
        Line2D([0], [0], color=S.INK, lw=1.7, label="raw coal ban (15 May 2019)"),
        Line2D([0], [0], color=S.INK_3, lw=0.9, ls=(0, (4, 3)),
               label="ALGORITHM_VERSION change"),
        Patch(facecolor=S.COLLAPSE, alpha=S.COLLAPSE_ALPHA,
              label=f"coverage collapse (n_obs < {THIN_DISPLAY:.0f})"),
    ]
    fig.legend(handles=handles, loc="lower center", bbox_to_anchor=(0.5, -0.035),
               frameon=False, fontsize=9.5, ncol=5, labelcolor=S.INK_2,
               handlelength=1.8, columnspacing=2.2)

    for ax in (ax_d, ax_r):
        S.finish(ax)
        ax.margins(x=0.01)
    S.time_axis(ax_r)
    S.footnote(fig)
    S.save(fig, "04_metro_minus_rural.png")
    return 0


if __name__ == "__main__":
    sys.exit(main())
