"""Figure 06: is the seasonal shape stable across years?

Writes figures/06_seasonal_cycle_by_year.png from data/processed/no2_monthly_ub.csv.

One line per calendar year, x = month 1-12, UB_METRO only. Missing months break
the line; nothing is interpolated.

Colour: years without a coverage problem take a sequential light-to-dark ramp
in one hue, because year is an ordered variable. Years containing any month
below the display cut are drawn in the contrasting series colour so the
question -- do the collapsed years look structurally different -- can be
answered by eye. Every line is also directly labelled, so colour is never the
only carrier of identity.
"""

import sys

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D

import _figstyle as S

THIN_DISPLAY = 5.0
RAMP_LIGHT = "#bcd6f2"
RAMP_DARK = "#123f73"
AFFECTED = S.SERIES["UB_RURAL"]  # the contrasting hue, reused as a flag colour

MONTH_LABELS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def report(metro):
    print("=" * 78)
    print("FIGURE 06 -- seasonal cycle by year, UB_METRO")
    print("=" * 78)

    piv = metro.pivot(index="year", columns="month", values="no2_mol_m2")
    obs = metro.pivot(index="year", columns="month", values="n_obs")

    print("\nno2_mol_m2 by year x month:")
    with pd.option_context("display.width", 220, "display.float_format",
                           lambda v: f"{v:.2e}"):
        print(piv.to_string())
    print("\nn_obs by year x month:")
    with pd.option_context("display.width", 220, "display.float_format",
                           lambda v: f"{v:7.2f}"):
        print(obs.to_string())

    print("\nshape of the cycle, per year:")
    print(f"  {'year':<6}{'peak month':>12}{'peak value':>14}{'min value':>13}"
          f"{'peak/min':>11}{'months':>8}{'thin':>6}")
    for yr, row in piv.iterrows():
        vals = row.dropna()
        if vals.empty:
            continue
        thin = int((obs.loc[yr].dropna() < THIN_DISPLAY).sum())
        peak_m = int(vals.idxmax())
        print(f"  {yr:<6}{MONTH_LABELS[peak_m - 1]:>12}{vals.max():>14.2e}"
              f"{vals.min():>13.2e}{vals.max() / vals.min():>11.1f}"
              f"{len(vals):>8}{thin:>6}")

    print("\n  peak/min is a crude amplitude measure. Years with thin months carry")
    print("  an inflated peak, so their amplitude is not comparable to the rest.")

    clean_years = [yr for yr in piv.index
                   if int((obs.loc[yr].dropna() < THIN_DISPLAY).sum()) == 0]
    print(f"\nyears with no thin months: {clean_years}")
    winter_months, summer_months = [1, 2, 12], [6, 7, 8]
    print(f"  {'year':<6}{'winter mean':>14}{'summer mean':>14}{'ratio':>9}")
    for yr in clean_years:
        w = piv.loc[yr, [m for m in winter_months if m in piv.columns]].dropna()
        s = piv.loc[yr, [m for m in summer_months if m in piv.columns]].dropna()
        if w.empty or s.empty:
            continue
        print(f"  {yr:<6}{w.mean():>14.2e}{s.mean():>14.2e}{w.mean() / s.mean():>9.1f}")


def main():
    df = S.load()
    metro = df[df["box"] == "UB_METRO"].copy()
    report(metro)

    years = sorted(metro["year"].unique())
    thin_years = {
        yr for yr in years
        if (metro[(metro["year"] == yr)]["n_obs"] < THIN_DISPLAY).any()
    }
    clean_years = [yr for yr in years if yr not in thin_years]

    plt.rcParams.update(S.RCPARAMS)
    fig, ax = plt.subplots(figsize=(12, 7.4))

    ax.axhline(0, color=S.SPINE, lw=1, zorder=1)

    labels = []
    for yr in years:
        g = metro[metro["year"] == yr].sort_values("month")
        if yr in thin_years:
            color, lw, z = AFFECTED, 2.6, 5
        else:
            t = clean_years.index(yr) / max(len(clean_years) - 1, 1)
            color, lw, z = S.lerp_hex(RAMP_LIGHT, RAMP_DARK, t), 2.0, 4
        ax.plot(g["month"], g["no2_mol_m2"], color=color, lw=lw, zorder=z,
                solid_capstyle="round")

        # Hollow markers on months below the display cut.
        thin = g[g["n_obs"] < THIN_DISPLAY]
        if not thin.empty:
            ax.scatter(thin["month"], thin["no2_mol_m2"], s=52,
                       facecolors=S.SURFACE, edgecolors=color, linewidths=1.8,
                       zorder=6)

        last = g.dropna(subset=["no2_mol_m2"]).iloc[-1]
        labels.append([yr, float(last["month"]), float(last["no2_mol_m2"]), color])

    # Nudge labels apart where several years end at the same month, otherwise
    # 2021 and 2022 print on top of each other at December.
    span = metro["no2_mol_m2"].max() - metro["no2_mol_m2"].min()
    gap = 0.035 * span
    for month in {lab[1] for lab in labels}:
        group = sorted([lab for lab in labels if lab[1] == month], key=lambda r: r[2])
        for i in range(1, len(group)):
            if group[i][2] - group[i - 1][2] < gap:
                group[i][2] = group[i - 1][2] + gap

    for yr, mx, my, color in labels:
        ax.annotate(
            str(yr), xy=(mx, my), xytext=(6, 0), textcoords="offset points",
            fontsize=9, color=color, va="center", fontweight="bold",
            # Opaque halo: 2026 ends in July, so its label sits in the crowded
            # summer band where several lines cross.
            bbox=dict(facecolor=S.SURFACE, edgecolor="none", pad=1.2),
            zorder=8,
        )

    ax.set_title(
        "The collapsed years are not a different shape — they are the same shape with a broken winter",
        fontsize=13, color=S.INK, loc="left", pad=32, fontweight="bold",
    )
    ax.text(
        0, 1.012,
        "UB_METRO only. Hollow rings mark months with n_obs < 5, a display cut — "
        "nothing is excluded, smoothed, or filled.",
        transform=ax.transAxes, fontsize=9.5, color=S.INK_2,
    )
    ax.set_xlabel("month", color=S.INK_2)
    ax.set_ylabel("tropospheric NO$_2$ column (mol/m$^2$)", color=S.INK_2)
    ax.set_xticks(range(1, 13))
    ax.set_xticklabels(MONTH_LABELS)
    ax.set_xlim(0.7, 12.8)
    S.finish(ax)

    handles = [
        Line2D([0], [0], color=S.lerp_hex(RAMP_LIGHT, RAMP_DARK, 0.15), lw=2,
               label="year with full coverage (light $\\rightarrow$ dark = earlier $\\rightarrow$ later)"),
        Line2D([0], [0], color=AFFECTED, lw=2.6,
               label="year containing a collapsed month"),
        Line2D([0], [0], color=S.INK_3, lw=0, marker="o", ms=9,
               markerfacecolor=S.SURFACE, markeredgecolor=S.INK_3,
               markeredgewidth=1.8, label="month with n_obs < 5"),
    ]
    ax.legend(handles=handles, loc="upper center", frameon=False, fontsize=9.5,
              labelcolor=S.INK_2, handlelength=2.0, ncol=1)

    S.footnote(fig, y=-0.03)
    S.save(fig, "06_seasonal_cycle_by_year.png")
    return 0


if __name__ == "__main__":
    sys.exit(main())
