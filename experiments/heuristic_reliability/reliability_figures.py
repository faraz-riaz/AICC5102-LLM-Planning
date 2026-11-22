"""M3 figures: R6 overestimation, R7 difficulty scaling, R8 trial stability, R9 error vs gap.

Reads only files already in the repository (nothing is re-run):
  results/raw/sampled_states/sampled_state_optimal_costs.csv                      exact h*(s) per sampled state
  results/derived/heuristic_reliability/sampled_state_estimates.csv h(s) per heuristic and state
  results/derived/heuristic_reliability/coverage_by_difficulty.csv
  results/derived/heuristic_reliability/trial_stability_summary.csv
  results/derived/heuristic_reliability/error_vs_gap_by_task.csv

Writes PDF + PNG to results/figures/heuristic_reliability/:
  overestimation   (a) overestimation rate per domain, (b) signed error h - h*
  coverage_by_difficulty          coverage by difficulty tier, one panel per algorithm
  trial_stability  coverage of the 3 trials, mean +/- sample SD, archived baseline
  error_vs_gap     task mean positive error vs plan gap (descriptive only)

R6 uses only states whose h* is proven (unknown_timeout states are excluded and
counted). Errors use a symmetric-log axis because transport_trial03 adds 100,000
per undelivered package, so its errors are several orders of magnitude larger.

Usage (from the repository root):
  uv run --frozen python experiments/heuristic_reliability/reliability_figures.py
"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
M3 = ROOT / "results" / "derived" / "heuristic_reliability"
REFS = ROOT / "results" / "raw" / "sampled_states" / "sampled_state_optimal_costs.csv"
OUT = ROOT / "results" / "figures" / "heuristic_reliability"

HEURISTICS = ["archived", "trial-01", "trial-02", "trial-03"]
LABELS = {"archived": "Archived R1", "trial-01": "Trial 1", "trial-02": "Trial 2",
          "trial-03": "Trial 3", "hmax": "hmax"}
# Okabe-Ito colour-blind-safe palette; archived matches the paper's F1/F2 blue.
COLORS = {"archived": "#0072B2", "trial-01": "#E69F00", "trial-02": "#009E73",
          "trial-03": "#CC79A7", "hmax": "#D55E00"}
DOMAINS = ["blocksworld", "miconic", "transport"]
METHODS = ["gbfs", "astar", "weighted_astar-w1.5", "weighted_astar-w2", "ida_star"]
METHOD_LABELS = {"gbfs": "GBFS", "astar": "A*", "weighted_astar-w1.5": "WA* (w=1.5)",
                 "weighted_astar-w2": "WA* (w=2)", "ida_star": "IDA* (easy only)"}
EPS = 1e-9

plt.rcParams.update({"font.size": 8, "axes.spines.top": False, "axes.spines.right": False})


def save(fig, name: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(OUT / f"{name}.{ext}", dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"  wrote {OUT.relative_to(ROOT)}/{name}.pdf/.png")


def overestimation_study() -> None:
    est = pd.read_csv(M3 / "sampled_state_estimates.csv")
    refs = pd.read_csv(REFS)[["state_id", "h_star", "reference_status"]]
    data = est.merge(refs, on="state_id", how="left", validate="many_to_one")
    assert data.reference_status.notna().all(), "state without a reference row"
    assert (data.eval_status == "ok").all(), "heuristic evaluation errors must be audited first"
    data = data[(data.reference_status == "proven") & np.isfinite(data.h_star)].copy()
    data["signed"] = data.h_value - data.h_star
    data["over"] = data.signed > EPS

    fig, (ax_rate, ax_err) = plt.subplots(1, 2, figsize=(7.0, 2.6), layout="constrained")
    width = 0.2
    for i, h in enumerate(HEURISTICS):
        sub = data[data.heuristic_trial_id == h]
        rates = [sub[sub.domain == d].over.mean() * 100 for d in DOMAINS]
        x = np.arange(len(DOMAINS)) + (i - 1.5) * width
        bars = ax_rate.bar(x, rates, width, color=COLORS[h], label=LABELS[h])
        ax_rate.bar_label(bars, fmt="%.0f", fontsize=6, padding=1)
    n = [data[(data.domain == d) & (data.heuristic_trial_id == "archived")].shape[0] for d in DOMAINS]
    ax_rate.set_xticks(range(len(DOMAINS)), [f"{d}\n(n={k} states)" for d, k in zip(DOMAINS, n)])
    ax_rate.set(ylabel="States overestimated (%)", ylim=(0, 112), title="(a) Overestimation rate, h(s) > h*(s)")
    fig.legend(*ax_rate.get_legend_handles_labels(), frameon=False, ncol=4, loc="outside lower center", fontsize=7)

    positions, values, colors = [], [], []
    for j, d in enumerate(DOMAINS):
        for i, h in enumerate(HEURISTICS):
            positions.append(j + (i - 1.5) * width)
            values.append(data[(data.domain == d) & (data.heuristic_trial_id == h)].signed.to_numpy())
            colors.append(COLORS[h])
    parts = ax_err.boxplot(values, positions=positions, widths=width * 0.85, patch_artist=True,
                           showfliers=True, flierprops={"markersize": 2}, medianprops={"color": "black"})
    for box, c in zip(parts["boxes"], colors):
        box.set(facecolor=c, alpha=0.8)
    ax_err.axhline(0, color="black", lw=0.8, ls="--")
    ax_err.set_yscale("symlog", linthresh=10)
    ax_err.set_ylim(bottom=-10)
    ax_err.set_xticks(range(len(DOMAINS)), DOMAINS)
    ax_err.set(ylabel="Signed error h(s) - h*(s)\n(symmetric log scale)",
               title="(b) Error distribution (above 0 = overestimate)")
    save(fig, "overestimation")
    excluded = (pd.read_csv(REFS).reference_status != "proven").sum()
    print(f"    R6: {data.state_id.nunique()} states with proven h*, {excluded} excluded (unknown h*)")


def r7_scaling() -> None:
    cov = pd.read_csv(M3 / "coverage_by_difficulty.csv")
    tiers = ["easy", "medium", "hard"]
    methods = METHODS[:4]  # IDA* was run on easy tasks only, so it has no curve
    fig, axes = plt.subplots(1, len(methods), figsize=(7.0, 2.2), sharey=True, layout="constrained")
    for ax, m in zip(axes, methods):
        for h in HEURISTICS + ["hmax"]:
            sub = cov[(cov.algorithm == m) & (cov.heuristic == h)].set_index("difficulty").reindex(tiers)
            ax.plot(tiers, sub.solved, marker="o", ms=3, color=COLORS[h], label=LABELS[h],
                    ls="--" if h in ("archived", "hmax") else "-")
        ax.set(title=METHOD_LABELS[m], ylim=(-1, 31))
    axes[0].set_ylabel("Solved (of 30 per tier)")
    fig.legend(*axes[0].get_legend_handles_labels(), frameon=False, ncol=5, loc="outside lower center", fontsize=7)
    save(fig, "coverage_by_difficulty")


def r8_trial_stability() -> None:
    agg = pd.read_csv(M3 / "trial_stability_summary.csv")
    agg = agg[agg.scope == "all"].set_index("algorithm").reindex(METHODS)
    fig, ax = plt.subplots(figsize=(5.5, 2.3), layout="constrained")
    for i, (m, row) in enumerate(agg.iterrows()):
        trials = [row.trial_01, row.trial_02, row.trial_03]
        for k, (t, v) in enumerate(zip(HEURISTICS[1:], trials)):
            ax.scatter(i + (k - 1) * 0.08, v, color=COLORS[t], s=18, zorder=3,
                       label=LABELS[t] if i == 0 else None)
        ax.errorbar(i + 0.25, row["mean"], yerr=row.sd_ddof1, fmt="_", color="black", capsize=3,
                    label="Mean ± SD (3 trials)" if i == 0 else None)
        ax.scatter(i - 0.25, row.archived, marker="D", color=COLORS["archived"], s=22,
                   label=LABELS["archived"] if i == 0 else None)
    ax.set_xticks(range(len(METHODS)), [f"{METHOD_LABELS[m]}\nn={int(agg.loc[m, 'tested_per_trial'])}" for m in METHODS])
    ax.set(ylabel="Solved tasks")
    ax.legend(frameon=False, fontsize=7, ncol=3, loc="lower left")
    save(fig, "trial_stability")


def r9_error_vs_gap() -> None:
    joined = pd.read_csv(M3 / "error_vs_gap_by_task.csv")
    joined = joined[joined.task_mean_positive_error.notna()]
    fig, axes = plt.subplots(1, len(METHODS), figsize=(7.0, 2.4), sharey=True, sharex=True, layout="constrained")
    short = {"gbfs": "GBFS", "astar": "A*", "weighted_astar-w1.5": "WA* 1.5",
             "weighted_astar-w2": "WA* 2", "ida_star": "IDA* (easy)"}
    for ax, m in zip(axes, METHODS):
        sub = joined[joined.algorithm == m]
        for h in HEURISTICS:
            s = sub[sub.heuristic == h]
            ax.scatter(s.task_mean_positive_error, s.gap_percent, s=10, alpha=0.8,
                       color=COLORS[h], label=LABELS[h])
        ax.set_xscale("symlog", linthresh=1)
        ax.set_yscale("symlog", linthresh=10)
        ax.set_xticks([0, 1, 100, 10**4])
        ax.set(title=f"{short[m]} (n={len(sub)})")
    fig.supxlabel("Task mean positive error h(s) - h*(s), sampled states (symmetric log scale)", fontsize=8)
    axes[0].set_ylabel("Plan gap (%)\n(symmetric log scale)")
    fig.legend(*axes[0].get_legend_handles_labels(), frameon=False, ncol=4, loc="outside upper center", fontsize=7)
    save(fig, "error_vs_gap")


def main() -> None:
    overestimation_study()
    r7_scaling()
    r8_trial_stability()
    r9_error_vs_gap()


if __name__ == "__main__":
    main()
