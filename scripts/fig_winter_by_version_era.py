"""Figure 05: do good-coverage winter values step at version boundaries?

Writes figures/05_winter_by_version_era.png from data/processed/no2_monthly_ub.csv.

A winter is Dec + Jan + Feb, named for the December that opens it, and is
included only if BOTH boxes have n_obs >= threshold in ALL THREE months. The
threshold is not chosen here: the figure is produced at three thresholds
(3, 5, 10), one panel each, so the sensitivity of any conclusion is visible.
Winters excluded at a given threshold keep their slot on the x-axis and are
labelled, so what dropped out is as legible as what stayed.

BOOTSTRAP CAVEAT, and it is a serious one: each winter mean rests on THREE
monthly values. Resampling three numbers with replacement gives a crude
interval -- it can only ever produce means drawn from those three values, and
it says nothing about the uncertainty within each monthly mean. Read the bars
as a rough spread across the three months, not as a confidence interval in any
inferential sense.
"""

import sys

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D

import _figstyle as S

THRESHOLDS = [3.0, 5.0, 10.0]  # chosen by the author, not by this script
N_BOOT = 10000
SEED = 20260827  # fixed so the intervals are reproducible


def winter_table(df):
    """One row per winter per box, carrying the three monthly values."""
    rows = []
    for box, g in df.groupby("box"):
        for r in g.itertuples():
            label = S.winter_label(int(r.year), int(r.month))
            if label is None or label not in S.WINTER_VERSION:
                continue
            rows.append({
                "winter": label, "box": box, "year": int(r.year),
                "month": int(r.month), "no2": r.no2_mol_m2, "n_obs": r.n_obs,
            })
    return pd.DataFrame(rows)


def boot_ci(values, rng):
    """Percentile bootstrap over the winter's monthly values. n = 3."""
    v = np.asarray([x for x in values if not np.isnan(x)], dtype=float)
    if len(v) == 0:
        return np.nan, np.nan, np.nan
    draws = rng.choice(v, size=(N_BOOT, len(v)), replace=True).mean(axis=1)
    return float(v.mean()), float(np.percentile(draws, 2.5)), float(np.percentile(draws, 97.5))


def assess(wt, thr):
    """Which winters pass, which fail, and why."""
    out = {}
    for winter in S.WINTER_VERSION:
        sub = wt[wt["winter"] == winter]
        if sub.empty:
            out[winter] = {"ok": False, "reason": "winter not in record"}
            continue
        expected = 3 * 2  # three months, two boxes
        if len(sub) != expected:
            out[winter] = {"ok": False,
                           "reason": f"incomplete ({len(sub)}/{expected} box-months)"}
            continue
        bad = sub[sub["n_obs"] < thr]
        if not bad.empty:
            worst = bad.loc[bad["n_obs"].idxmin()]
            out[winter] = {
                "ok": False,
                "reason": (f"{len(bad)} box-month(s) below {thr:g}; worst "
                           f"{worst['box']} {worst['year']}-{worst['month']:02d} "
                           f"n_obs={worst['n_obs']:.2f}"),
            }
            continue
        if sub["no2"].isna().any():
            out[winter] = {"ok": False, "reason": "contains a NaN value"}
            continue
        out[winter] = {"ok": True, "reason": ""}
    return out


def report(wt, results):
    print("=" * 78)
    print("FIGURE 05 -- winter means by version era")
    print("=" * 78)
    print("\nwinter -> ALGORITHM_VERSION (all three months version-pure):")
    for w, v in S.WINTER_VERSION.items():
        print(f"  {w}: {v}")

    print("\nmonthly values feeding each winter:")
    show = wt.copy()
    show["ym"] = [f"{y}-{m:02d}" for y, m in zip(show["year"], show["month"])]
    with pd.option_context("display.max_rows", None, "display.width", 200):
        print(show[["winter", "box", "ym", "no2", "n_obs"]].to_string(index=False))

    for thr, (verdicts, stats) in results.items():
        print("\n" + "-" * 78)
        print(f"THRESHOLD n_obs >= {thr:g}")
        print("-" * 78)
        kept = [w for w, v in verdicts.items() if v["ok"]]
        print(f"included {len(kept)} of {len(S.WINTER_VERSION)} winters: {', '.join(kept)}")
        for w, v in verdicts.items():
            if not v["ok"]:
                print(f"  EXCLUDED {w}: {v['reason']}")
        print(f"\n  {'winter':<9}{'ver':<8}{'box':<10}{'mean':>12}{'ci_lo':>12}{'ci_hi':>12}")
        for (w, box), (m, lo, hi) in stats.items():
            print(f"  {w:<9}{S.WINTER_VERSION[w]:<8}{box:<10}"
                  f"{m:>12.3e}{lo:>12.3e}{hi:>12.3e}")

        # The question: do values step at version boundaries?
        for box in S.SERIES:
            series = [(w, stats[(w, box)][0]) for w in kept if (w, box) in stats]
            if len(series) >= 2:
                print(f"\n  {box} winter means in version order:")
                for w, m in series:
                    print(f"    {w}  v{S.WINTER_VERSION[w]}  {m:.3e}")


def main():
    df = S.load()
    wt = winter_table(df)
    rng = np.random.default_rng(SEED)

    results = {}
    for thr in THRESHOLDS:
        verdicts = assess(wt, thr)
        stats = {}
        for w, v in verdicts.items():
            if not v["ok"]:
                continue
            for box in S.SERIES:
                vals = wt[(wt["winter"] == w) & (wt["box"] == box)]["no2"].tolist()
                stats[(w, box)] = boot_ci(vals, rng)
        results[thr] = (verdicts, stats)

    report(wt, results)

    plt.rcParams.update(S.RCPARAMS)
    winters = list(S.WINTER_VERSION)
    x = np.arange(len(winters))
    width = 0.36

    fig, axes = plt.subplots(
        len(THRESHOLDS), 1, figsize=(13, 11), sharex=True, sharey=True,
        gridspec_kw={"hspace": 0.22},
    )

    for ax, thr in zip(axes, THRESHOLDS):
        verdicts, stats = results[thr]
        for k, (box, color) in enumerate(S.SERIES.items()):
            offs = (k - 0.5) * width
            for i, w in enumerate(winters):
                if (w, box) not in stats:
                    continue
                m, lo, hi = stats[(w, box)]
                ax.bar(x[i] + offs, m, width, color=color, zorder=3,
                       edgecolor=S.SURFACE, linewidth=1.2)
                ax.errorbar(x[i] + offs, m, yerr=[[m - lo], [hi - m]],
                            fmt="none", ecolor=S.INK_2, elinewidth=1.3,
                            capsize=4, zorder=5)

        for i, w in enumerate(winters):
            if not verdicts[w]["ok"]:
                ax.text(x[i], 0.04, "excluded", transform=ax.get_xaxis_transform(),
                        fontsize=8.5, color=S.INK_3, ha="center", rotation=90,
                        va="bottom", style="italic")

        kept = sum(1 for v in verdicts.values() if v["ok"])
        ax.set_title(
            f"n_obs $\\geq$ {thr:g} in all three months, both boxes "
            f"— {kept} of {len(winters)} winters qualify",
            fontsize=11.5, color=S.INK, loc="left", pad=8, fontweight="bold",
        )
        ax.set_ylabel("winter mean NO$_2$\n(mol/m$^2$)", color=S.INK_2)
        S.finish(ax)

    axes[-1].set_xticks(x)
    axes[-1].set_xticklabels(
        [f"{w}\nv{S.WINTER_VERSION[w]}" for w in winters], fontsize=9.5,
    )
    axes[-1].set_xlim(-0.7, len(winters) - 0.3)

    fig.suptitle(
        "Winter means, good-coverage winters only, labelled by retrieval version",
        fontsize=13.5, color=S.INK, x=0.008, ha="left", y=0.995, fontweight="bold",
    )
    fig.text(
        0.008, 0.965,
        "Error bars are a percentile bootstrap over each winter's THREE monthly "
        "values — a crude spread, not an inferential confidence interval.",
        fontsize=9.5, color=S.INK_2,
    )
    handles = [Line2D([0], [0], color=c, lw=7, label=b) for b, c in S.SERIES.items()]
    fig.legend(handles=handles, loc="lower center", bbox_to_anchor=(0.5, -0.022),
               frameon=False, fontsize=10, ncol=2, labelcolor=S.INK_2,
               handlelength=1.6, columnspacing=2.4)
    S.footnote(fig, y=-0.052)
    S.save(fig, "05_winter_by_version_era.png")
    return 0


if __name__ == "__main__":
    sys.exit(main())
