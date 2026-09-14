"""Figure 03: does low coverage produce extreme values?

Writes figures/03_coverage_vs_signal.png from data/processed/no2_monthly_ub.csv.

Scatter of n_obs against no2_mol_m2, with no time axis, so the relationship
between coverage and value stands on its own.

Layout: rows are boxes, columns are seasons. Season is encoded by panel
position AND by colour, deliberately redundantly -- a four-colour categorical
set in a scatter needs all-pairs colourblind separation, and the dataviz
validator was not available to certify one, so colour is never load-bearing
here.

y is linear, not log: the series contains a negative value (UB_RURAL Dec 2020)
which log cannot show, and the extreme highs are the entire point -- log would
compress exactly what the figure exists to reveal.
"""

import sys

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd

import _figstyle as S

THIN_DISPLAY = 5.0  # display cut for the guide line only; nothing is filtered


def report(df):
    """Print the numbers behind the figure."""
    print("=" * 78)
    print("FIGURE 03 -- coverage vs signal")
    print("=" * 78)

    for box, g in df.groupby("box"):
        g = g.dropna(subset=["no2_mol_m2"])
        # Spearman = Pearson on ranks. Computed from ranks directly so no
        # dependency beyond pandas is needed.
        rho = g["n_obs"].rank().corr(g["no2_mol_m2"].rank())
        print(f"\n{box}  (n = {len(g)} months with a value)")
        print(f"  Spearman rank correlation n_obs vs no2: {rho:+.3f}")

        lo = g[g["n_obs"] < THIN_DISPLAY]
        hi = g[g["n_obs"] >= THIN_DISPLAY]
        for label, part in (("n_obs <  5", lo), ("n_obs >= 5", hi)):
            if part.empty:
                print(f"  {label}: none")
                continue
            print(
                f"  {label}: n={len(part):>3}  "
                f"mean={part['no2_mol_m2'].mean():.3e}  "
                f"median={part['no2_mol_m2'].median():.3e}  "
                f"min={part['no2_mol_m2'].min():.3e}  "
                f"max={part['no2_mol_m2'].max():.3e}"
            )
        if not lo.empty and not hi.empty:
            print(
                f"  ratio of means (thin / covered): "
                f"{lo['no2_mol_m2'].mean() / hi['no2_mol_m2'].mean():.2f}x"
            )

        top = g.nlargest(8, "no2_mol_m2")[["year", "month", "no2_mol_m2", "n_obs"]]
        print(f"  8 highest values in {box}:")
        print("    " + top.to_string(index=False).replace("\n", "\n    "))
        n_thin_in_top = int((top["n_obs"] < THIN_DISPLAY).sum())
        print(f"    -> {n_thin_in_top} of those 8 come from months with n_obs < 5")

    print("\nper-season counts of thin months (n_obs < 5):")
    thin = df[df["n_obs"] < THIN_DISPLAY]
    print(thin.groupby(["box", "season"]).size().to_string())


def main():
    df = S.load()
    report(df)

    plt.rcParams.update(S.RCPARAMS)
    boxes = list(S.SERIES)
    seasons = list(S.SEASONS)

    fig, axes = plt.subplots(
        len(boxes), len(seasons), figsize=(14, 7.2),
        sharex=True, sharey=True,
        gridspec_kw={"hspace": 0.18, "wspace": 0.08},
    )

    for i, box in enumerate(boxes):
        for j, season in enumerate(seasons):
            ax = axes[i][j]
            g = df[(df["box"] == box) & (df["season"] == season)]
            g = g.dropna(subset=["no2_mol_m2"])

            ax.axvline(THIN_DISPLAY, color=S.INK_3, lw=1, ls=(0, (2, 3)), zorder=1)
            ax.axhline(0, color=S.SPINE, lw=1, zorder=1)
            ax.scatter(
                g["n_obs"], g["no2_mol_m2"],
                s=44, color=S.SEASON_COLORS[season],
                edgecolors=S.SURFACE, linewidths=0.7, zorder=4, alpha=0.95,
            )

            if i == 0:
                ax.set_title(season, fontsize=11, color=S.INK, pad=8)
            if j == 0:
                ax.set_ylabel(
                    f"{box}\ntropospheric NO$_2$\n(mol/m$^2$)",
                    fontsize=9.5, color=S.INK_2,
                )
            if i == len(boxes) - 1:
                ax.set_xlabel("observations per grid cell", fontsize=9.5,
                              color=S.INK_2)
            S.finish(ax)

    # The single worst artifact, called out where it lives.
    metro_winter = df[(df["box"] == "UB_METRO") & (df["season"] == "winter (DJF)")]
    worst = metro_winter.loc[metro_winter["no2_mol_m2"].idxmax()]
    ax = axes[0][0]
    ax.annotate(
        f"Dec 2020\n{worst['no2_mol_m2']:.2e} mol/m$^2$\nfrom {worst['n_obs']:.2f} obs/cell",
        xy=(worst["n_obs"], worst["no2_mol_m2"]),
        xytext=(14, worst["no2_mol_m2"] * 0.99),
        fontsize=9, color=S.INK, va="top",
        arrowprops=dict(arrowstyle="->", color=S.INK_2, lw=1.1,
                        connectionstyle="arc3,rad=0.2"),
    )
    axes[0][0].text(
        THIN_DISPLAY + 1.2, 0.04, "n_obs = 5",
        transform=axes[0][0].get_xaxis_transform(),
        fontsize=8, color=S.INK_3, va="bottom",
    )

    fig.suptitle(
        "The extreme values live at the left edge: they come from months the satellite barely saw",
        fontsize=13.5, color=S.INK, x=0.008, ha="left", y=0.99, fontweight="bold",
    )
    fig.text(
        0.008, 0.938,
        "Each point is one month. Rows are boxes, columns are seasons. "
        "Vertical dashes mark n_obs = 5, a display cut only -- nothing is excluded.",
        fontsize=9.5, color=S.INK_2,
    )
    S.footnote(fig, y=-0.045)
    S.save(fig, "03_coverage_vs_signal.png")
    return 0


if __name__ == "__main__":
    sys.exit(main())
