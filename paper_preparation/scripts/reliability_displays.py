"""Optional M3 analysis adapters; no experiments and no invented observations.

Inputs are normalized CSVs specified in RELIABILITY_INTEGRATION_SPEC.md. Import
summarize_state_errors for R6. CLI makes R8 and/or R9 displays only when the
corresponding real inputs are supplied. Run --help for arguments.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from build_paper_tables_and_figures import ROOT, table, save, COLORS, METHODS, attach_references

KEY = ["domain", "problem_id", "heuristic_set_id", "heuristic_trial_id"]


def summarize_state_errors(estimates: pd.DataFrame, exact: pd.DataFrame):
    """One task summary per heuristic; unknown/dead-end references stay excluded.

    estimates: KEY + state_id, h_value. exact: domain,problem_id,state_id,
    reference_status,h_star. Same frozen state inventory across heuristics.
    Returns task-level counts, frequency, signed/absolute/positive errors.
    """
    state_key = ["domain", "problem_id", "state_id"]
    assert not exact.duplicated(state_key).any()
    assert not estimates.duplicated(KEY + ["state_id"]).any()
    expected = set(map(tuple, exact[state_key].values))
    for _, group in estimates.groupby(["heuristic_set_id", "heuristic_trial_id"], dropna=False):
        assert set(map(tuple, group[state_key].values)) == expected, "Unequal frozen state inventories"
    joined = estimates.merge(exact, on=state_key, validate="many_to_one", how="left", indicator=True)
    assert joined._merge.eq("both").all()
    finite = joined.reference_status.eq("proven") & np.isfinite(joined.h_star)
    assert np.isfinite(joined.loc[finite, "h_value"]).all(), "Audit non-finite heuristic values separately"
    assert joined.loc[finite, "h_value"].ge(0).all(), "Audit invalid negative heuristic values separately"
    joined["eligible"] = finite
    joined["signed"] = (joined.h_value - joined.h_star).where(finite)
    joined["absolute"] = joined.signed.abs()
    joined["positive"] = joined.signed.clip(lower=0)
    joined["over"] = (joined.signed > 1e-9).where(finite)
    result = joined.groupby(KEY, dropna=False).agg(
        sampled_states=("state_id", "size"), eligible_states=("eligible", "sum"),
        overestimate_rate=("over", "mean"), signed_error_mean=("signed", "mean"),
        absolute_error_mean=("absolute", "mean"), positive_error_mean=("positive", "mean"))
    result["excluded_states"] = result.sampled_states-result.eligible_states
    return result.reset_index()


def trial_stability(runs: pd.DataFrame):
    """R8: complete matched scopes, exactly three trials, sample SD across trials."""
    required = KEY + ["algorithm_label", "difficulty", "status", "wall_time_s", "nodes_expanded",
                      "plan_cost", "plan_valid", "time_limit_s", "memory_limit_mib"]
    assert set(required) <= set(runs)
    assert not runs[required[:4]].isna().any().any()
    assert set(runs.heuristic_trial_id) == {"trial-01", "trial-02", "trial-03"}
    assert set(runs.algorithm_label) <= set(METHODS)
    assert runs.time_limit_s.eq(60).all() and runs.memory_limit_mib.eq(4096).all()
    assert runs.loc[runs.status.eq("success"), "plan_valid"].eq(True).all()
    refs = pd.read_csv(ROOT / "results/raw/optimal_costs.csv")
    runs = attach_references(runs, refs)
    manifest = pd.read_csv(ROOT / "benchmarks/manifest.csv")
    rows = []
    # Model/selection settings must be audited in a separate frozen manifest.
    for (set_id, method), group in runs.groupby(["heuristic_set_id", "algorithm_label"]):
        expected = manifest[manifest.difficulty == "easy"] if method == "ida_star" else manifest
        tasks = set(map(tuple, expected[["domain", "problem_id"]].values))
        assert set(group.heuristic_trial_id) == {"trial-01", "trial-02", "trial-03"}
        for trial, sub in group.groupby("heuristic_trial_id"):
            assert not sub.duplicated(["domain", "problem_id"]).any()
            assert set(map(tuple, sub[["domain", "problem_id"]].values)) == tasks
            solved = sub[sub.status == "success"]
            rows.append({"set": set_id, "method": method, "trial": trial,
                         "tested": len(sub), "solved": len(solved),
                         "solved_wall_median_s": solved.wall_time_s.median(),
                         "solved_expansion_median": solved.nodes_expanded.median(),
                         "gap_n": int(solved.gap_pct.notna().sum()),
                         "gap_mean_pct": solved.gap_pct.mean()})
    per_trial = pd.DataFrame(rows)
    summary = per_trial.groupby(["set", "method"]).agg(
        trials=("trial", "size"), tested_per_trial=("tested", "first"),
        coverage_mean=("solved", "mean"), coverage_sd=("solved", "std"),
        trial_wall_median_mean_s=("solved_wall_median_s", "mean"),
        trial_wall_median_sd_s=("solved_wall_median_s", "std"),
        trial_expansion_median_mean=("solved_expansion_median", "mean"),
        trial_expansion_median_sd=("solved_expansion_median", "std")).reset_index()
    table("M3_R8_per_trial", per_trial, note="Real supplied inputs only; solved-only effort is conditional on coverage.")
    table("M3_R8_summary", summary, note="Sample SD across 3 independent generation trials, ddof=1. Not variation across tasks.")
    archived = pd.read_csv(ROOT / "results/derived/history/three_workers/search_comparison/search_runs.csv")
    fig, ax = plt.subplots(figsize=(5.5, 2.4), layout="constrained")
    for i, row in enumerate(summary.itertuples()):
        observations = per_trial[(per_trial.set == row.set) & (per_trial.method == row.method)]
        ax.scatter(np.full(3, i)+[-.1, 0, .1], observations.solved, color=COLORS["deepseek-r1"], s=18)
        ax.errorbar(i, row.coverage_mean, yerr=row.coverage_sd, color="black", fmt="_", capsize=3)
        base = archived[(archived.heuristic_id == "deepseek-r1") & (archived.algorithm_label == row.method)]
        ax.scatter(i, base.status.eq("success").sum(), color=".35", marker="D", s=25)
    ax.set(xticks=range(len(summary)), xticklabels=[f"{r.set}\n{r.method}\nn={r.tested_per_trial}/trial" for r in summary.itertuples()],
           ylabel="Solved tasks", title="Dots: trials; bars: mean ± SD; diamonds: archived R1")
    save(fig, "F5_M3_trial_stability", "appendix")


def error_vs_quality(errors: pd.DataFrame, plans: pd.DataFrame):
    """R9: aggregate states before joining plans; never repeat a plan per state."""
    assert not errors.duplicated(KEY).any()
    assert not plans.duplicated(KEY + ["algorithm_label"]).any()
    refs = pd.read_csv(ROOT / "results/raw/optimal_costs.csv")
    joined = plans.merge(errors, on=KEY, validate="many_to_one", how="left")
    joined = joined.merge(refs[["domain", "problem_id", "optimality_proven", "optimal_cost"]],
                          on=["domain", "problem_id"], validate="many_to_one", how="left")
    ok = joined.status.eq("success") & joined.optimality_proven.eq(True) & (joined.optimal_cost > 0) & (joined.eligible_states > 0)
    eligible = joined[ok].copy()
    eligible["gap_pct"] = 100*(eligible.plan_cost-eligible.optimal_cost)/eligible.optimal_cost
    assert not (eligible.gap_pct < -1e-9).any()
    if eligible.empty:
        raise ValueError("No matched exact-reference observations; no R9 plot produced")
    eligible["included"] = True
    joined["exclusion"] = np.select(
        [~joined.status.eq("success"), ~joined.optimality_proven.eq(True) | ~(joined.optimal_cost > 0),
         ~(joined.eligible_states > 0)],
        ["not_solved", "no_positive_proven_task_reference", "no_eligible_state_error"], default="eligible")
    audit = joined.groupby(["heuristic_set_id", "heuristic_trial_id", "algorithm_label", "exclusion"]).agg(
        task_outcomes=("problem_id", "size")).reset_index()
    table("M3_R9_joined_eligible", eligible[KEY+["algorithm_label", "eligible_states", "positive_error_mean", "gap_pct"]], note="Task/heuristic/algorithm observations; dependence across algorithms/trials remains.")
    table("M3_R9_input_counts", audit, note="Compare with eligible table; exclusions include unsolved, missing task references and missing state references.")
    groups = list(eligible.groupby(["heuristic_set_id", "heuristic_trial_id", "algorithm_label"]))
    fig, axes = plt.subplots(len(groups), 1, figsize=(5.5, max(2.2, 1.6*len(groups))), squeeze=False, layout="constrained")
    for ax, (key, sub) in zip(axes.flat, groups):
        ax.scatter(sub.positive_error_mean, sub.gap_pct, s=20)
        ax.set(xlabel="Task mean positive heuristic error (actions)", ylabel="Gap (%)",
               title=f"{' / '.join(key)}; n={len(sub)} tasks")
    save(fig, "F6_M3_error_vs_quality", "appendix")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trials", type=Path, help="Normalized three-trial run CSV")
    parser.add_argument("--task-errors", type=Path, help="Output of summarize_state_errors")
    parser.add_argument("--plans", type=Path, help="Normalized plan outcomes, KEY + algorithm_label,status,plan_cost")
    args = parser.parse_args()
    if not args.trials and not args.task_errors and not args.plans:
        parser.error("Supply real M3 inputs; no placeholder plots are generated")
    if bool(args.task_errors) != bool(args.plans):
        parser.error("--task-errors and --plans must be supplied together")
    if args.trials:
        trial_stability(pd.read_csv(args.trials))
    if args.task_errors:
        error_vs_quality(pd.read_csv(args.task_errors), pd.read_csv(args.plans))


if __name__ == "__main__":
    main()
