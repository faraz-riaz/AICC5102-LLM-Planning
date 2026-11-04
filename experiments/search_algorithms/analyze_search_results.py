#!/usr/bin/env python3
"""Optimality-gap and trade-off analysis from real run outputs (M2-08).

Inputs: one or more extended run CSVs written by ``run_faraz_pilot.py`` (or
records with the same columns from the shared runner) and the task-level
reference table ``results/raw/faraz_optimal_refs.csv``.

Definitions (denominators are always reported):

* **coverage** = runs with status ``success`` (valid plan) / runs attempted;
* **optimality gap** (%) = 100 * (L - L*) / L*, computed only for successful
  runs on tasks whose reference is ``proven`` with L* > 0 (tasks with L* = 0
  are counted separately and excluded from gap statistics);
* **common-solved** = tasks solved by *every* compared method of a heuristic
  group; efficiency and gap comparisons are reported on this paired set as
  well as on each method's own solved set.

Outputs (never overwritten): CSV + Markdown tables under
``results/derived/<config_id>/<tag>/`` and figures R3/R4/R5 under
``results/figures/<config_id>/<tag>/``. Every figure is stamped with the
input scope so pilot data cannot be mistaken for final results.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib
import matplotlib.ticker

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]

STATUSES = [
    "success", "invalid_plan", "unsolved", "timeout", "memory_limit",
    "planner_error", "configuration_error", "validator_error", "interrupted",
]
# Reference categorical palette (dataviz skill, light mode), fixed slot order
# per algorithm so a method keeps its colour in every figure.
ALGORITHM_ORDER = ["gbfs", "astar", "weighted_astar-w1", "weighted_astar-w1.5", "weighted_astar-w2", "ida_star"]
ALGORITHM_COLORS = {
    "gbfs": "#2a78d6",
    "astar": "#eb6834",
    "weighted_astar-w1": "#6250d6",
    "weighted_astar-w1.5": "#1baf7a",
    "weighted_astar-w2": "#eda100",
    "ida_star": "#e87ba4",
}
ALGORITHM_NAMES = {
    "gbfs": "GBFS",
    "astar": "A*",
    "weighted_astar-w1": "WA* w=1",
    "weighted_astar-w1.5": "WA* w=1.5",
    "weighted_astar-w2": "WA* w=2",
    "ida_star": "IDA*",
}
HEURISTIC_NAMES = {"deepseek-r1": "DeepSeek-R1 (LLM)", "hmax": "hmax", "hff": "hFF", "zero": "zero"}
SURFACE, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
GAP_BINS = [(-0.001, 0.0, "0 (optimal)"), (0.0, 5.0, "(0,5]"), (5.0, 10.0, "(5,10]"),
            (10.0, 25.0, "(10,25]"), (25.0, 50.0, "(25,50]"), (50.0, np.inf, ">50")]


def load_runs(paths: list[Path]) -> pd.DataFrame:
    frames = [pd.read_csv(path) for path in paths]
    runs = pd.concat(frames, ignore_index=True)
    runs["method"] = runs["algorithm_label"]
    return runs


def attach_references(runs: pd.DataFrame, refs: pd.DataFrame) -> pd.DataFrame:
    keep = refs[["domain", "problem_id", "optimal_cost", "optimality_proven", "reference_status"]].rename(
        columns={"optimal_cost": "L_star", "optimality_proven": "ref_proven", "reference_status": "ref_status"}
    )
    merged = runs.merge(keep, on=["domain", "problem_id"], how="left")
    merged["ref_proven"] = merged["ref_proven"].fillna(False).astype(bool)
    ok = (merged["status"] == "success") & merged["ref_proven"] & (merged["L_star"] > 0)
    merged["gap_pct"] = np.where(ok, 100.0 * (merged["plan_cost"] - merged["L_star"]) / merged["L_star"], np.nan)
    merged["zero_cost_task"] = merged["ref_proven"] & (merged["L_star"] == 0)
    return merged


def ordered_methods(frame: pd.DataFrame) -> list[str]:
    present = list(frame["method"].unique())
    return [m for m in ALGORITHM_ORDER if m in present] + sorted(m for m in present if m not in ALGORITHM_ORDER)


def coverage_table(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (heuristic, method), group in df.groupby(["heuristic_id", "method"]):
        row = {"heuristic": heuristic, "method": method, "attempted": len(group)}
        for status in STATUSES:
            row[status] = int((group["status"] == status).sum())
        row["coverage_pct"] = 100.0 * row["success"] / row["attempted"]
        rows.append(row)
    return pd.DataFrame(rows)


def quality_table(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (heuristic, method), group in df.groupby(["heuristic_id", "method"]):
        solved = group[group["status"] == "success"]
        gaps = solved["gap_pct"].dropna()
        rows.append({
            "heuristic": heuristic,
            "method": method,
            "attempted": len(group),
            "solved_valid": len(solved),
            "invalid_plans": int((group["status"] == "invalid_plan").sum()),
            "mean_plan_cost": solved["plan_cost"].mean(),
            "median_plan_cost": solved["plan_cost"].median(),
            "gap_n": len(gaps),
            "solved_without_proven_ref": int((~solved["ref_proven"]).sum()),
            "zero_cost_tasks_solved": int(solved["zero_cost_task"].sum()),
            "gap_mean_pct": gaps.mean() if len(gaps) else np.nan,
            "gap_median_pct": gaps.median() if len(gaps) else np.nan,
            "gap_max_pct": gaps.max() if len(gaps) else np.nan,
            "optimal_n": int((gaps == 0).sum()),
            "median_search_time_s": solved["search_time_s"].median(),
            "mean_search_time_s": solved["search_time_s"].mean(),
            "median_nodes_expanded": solved["nodes_expanded"].median(),
            "median_nodes_generated": solved["nodes_generated"].median(),
        })
    return pd.DataFrame(rows)


def common_solved_table(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    rows, sizes = [], {}
    for heuristic, group in df.groupby("heuristic_id"):
        methods = ordered_methods(group)
        solved_sets = [
            set(map(tuple, group[(group["method"] == m) & (group["status"] == "success")][["domain", "problem_id"]].values))
            for m in methods
        ]
        common = set.intersection(*solved_sets) if solved_sets else set()
        sizes[heuristic] = len(common)
        for method in methods:
            sub = group[(group["method"] == method) & (group["status"] == "success")]
            sub = sub[[(d, p) in common for d, p in zip(sub["domain"], sub["problem_id"])]]
            gaps = sub["gap_pct"].dropna()
            rows.append({
                "heuristic": heuristic,
                "method": method,
                "common_solved_n": len(common),
                "gap_n": len(gaps),
                "gap_mean_pct": gaps.mean() if len(gaps) else np.nan,
                "gap_median_pct": gaps.median() if len(gaps) else np.nan,
                "optimal_n": int((gaps == 0).sum()),
                "median_nodes_expanded": sub["nodes_expanded"].median(),
                "median_nodes_generated": sub["nodes_generated"].median(),
                "median_search_time_s": sub["search_time_s"].median(),
                "total_nodes_expanded": sub["nodes_expanded"].sum(),
            })
    return pd.DataFrame(rows), sizes


def gap_distribution(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (heuristic, method), group in df.groupby(["heuristic_id", "method"]):
        gaps = group["gap_pct"].dropna()
        row = {"heuristic": heuristic, "method": method, "gap_n": len(gaps)}
        for low, high, label in GAP_BINS:
            row[label] = int(((gaps > low) & (gaps <= high)).sum())
        rows.append(row)
    return pd.DataFrame(rows)


def to_markdown(frame: pd.DataFrame, floatfmt: str = ".3g") -> str:
    def fmt(value):
        if isinstance(value, float):
            return "—" if np.isnan(value) else format(value, floatfmt)
        return str(value)

    header = "| " + " | ".join(frame.columns) + " |"
    sep = "|" + "|".join("---" for _ in frame.columns) + "|"
    body = ["| " + " | ".join(fmt(v) for v in row) + " |" for row in frame.itertuples(index=False)]
    return "\n".join([header, sep, *body])


def _style(ax) -> None:
    ax.set_facecolor(SURFACE)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)
    ax.tick_params(colors=INK2, labelsize=8)
    ax.yaxis.label.set_color(INK2)
    ax.xaxis.label.set_color(INK2)


def _stamp(fig, scope: str) -> None:
    fig.text(0.01, 0.005, scope, fontsize=7, color=INK2, ha="left", va="bottom")


def figure_r3(coverage: pd.DataFrame, path: Path, scope: str) -> None:
    heuristics = [h for h in HEURISTIC_NAMES if h in set(coverage["heuristic"])]
    fig, axes = plt.subplots(1, len(heuristics), figsize=(3.6 * len(heuristics), 3.4), sharey=True, facecolor=SURFACE)
    axes = np.atleast_1d(axes)
    for ax, heuristic in zip(axes, heuristics):
        sub = coverage[coverage["heuristic"] == heuristic].set_index("method")
        methods = [m for m in ALGORITHM_ORDER if m in sub.index]
        x = np.arange(len(methods))
        values = [sub.loc[m, "coverage_pct"] for m in methods]
        ax.bar(x, values, width=0.7, color=[ALGORITHM_COLORS[m] for m in methods],
               edgecolor=SURFACE, linewidth=2)
        for xi, m in zip(x, methods):
            ax.text(xi, sub.loc[m, "coverage_pct"] + 2, f"{sub.loc[m, 'success']}/{sub.loc[m, 'attempted']}",
                    ha="center", va="bottom", fontsize=7, color=INK)
        ax.set_xticks(x, [ALGORITHM_NAMES.get(m, m) for m in methods], rotation=35, ha="right")
        ax.set_ylim(0, 112)
        ax.set_title(HEURISTIC_NAMES.get(heuristic, heuristic), fontsize=9, color=INK)
        ax.grid(axis="y", color=GRID, linewidth=0.6)
        ax.set_axisbelow(True)
        _style(ax)
    axes[0].set_ylabel("Valid-plan coverage (%)")
    fig.suptitle("R3 · Coverage by search algorithm (label = solved / attempted)", fontsize=10, color=INK, x=0.01, ha="left")
    _stamp(fig, scope)
    fig.tight_layout(rect=(0, 0.04, 1, 0.95))
    fig.savefig(path, dpi=200, facecolor=SURFACE)
    plt.close(fig)


def figure_r4(df: pd.DataFrame, path: Path, scope: str) -> None:
    data = df.dropna(subset=["gap_pct"])
    heuristics = [h for h in HEURISTIC_NAMES if h in set(data["heuristic_id"])]
    if not heuristics:
        return
    fig, axes = plt.subplots(1, len(heuristics), figsize=(3.6 * len(heuristics), 3.4), sharey=True, facecolor=SURFACE)
    axes = np.atleast_1d(axes)
    rng = np.random.default_rng(5102)
    for ax, heuristic in zip(axes, heuristics):
        sub = data[data["heuristic_id"] == heuristic]
        methods = [m for m in ALGORITHM_ORDER if m in set(sub["method"])]
        for xi, method in enumerate(methods):
            gaps = sub[sub["method"] == method]["gap_pct"].to_numpy()
            jitter = rng.uniform(-0.22, 0.22, size=len(gaps))
            ax.scatter(np.full(len(gaps), xi) + jitter, gaps, s=16, color=ALGORITHM_COLORS[method],
                       edgecolor=SURFACE, linewidth=0.8, zorder=3)
            median = float(np.median(gaps))
            ax.plot([xi - 0.3, xi + 0.3], [median, median], color=INK, linewidth=1.5, zorder=4)
        labels = [
            f"{ALGORITHM_NAMES.get(m, m)}\n(n={int((sub['method'] == m).sum())})" for m in methods
        ]
        ax.set_xticks(range(len(methods)), labels, fontsize=7)
        ax.set_title(HEURISTIC_NAMES.get(heuristic, heuristic), fontsize=9, color=INK)
        ax.grid(axis="y", color=GRID, linewidth=0.6)
        ax.set_axisbelow(True)
        _style(ax)
    axes[0].set_ylabel("Optimality gap (%) vs proven L*")
    fig.suptitle("R4 · Optimality-gap distribution (dots = tasks, bar = median)", fontsize=10, color=INK, x=0.01, ha="left")
    _stamp(fig, scope)
    fig.tight_layout(rect=(0, 0.04, 1, 0.95))
    fig.savefig(path, dpi=200, facecolor=SURFACE)
    plt.close(fig)


def _place_labels(fig, ax, groups: dict) -> None:
    """Direct-label points, trying offsets until a label overlaps no other."""
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    frame = ax.get_window_extent(renderer)
    placed = []
    candidates = [(6, 5), (6, -12), (-6, 5), (-6, -12), (6, 16), (6, -23), (-6, 16), (-6, -23)]
    for (x, y), methods in sorted(groups.items(), key=lambda item: (item[0][0], item[0][1])):
        text = " / ".join(ALGORITHM_NAMES.get(m, m) for m in methods)
        for dx, dy in candidates:
            label = ax.annotate(text, (x, y), textcoords="offset points", xytext=(dx, dy),
                                fontsize=7, color=INK, ha="left" if dx > 0 else "right")
            box = label.get_window_extent(renderer).expanded(1.05, 1.15)
            inside = frame.x0 <= box.x0 and box.x1 <= frame.x1 and frame.y0 <= box.y0 and box.y1 <= frame.y1
            if inside and not any(box.overlaps(other) for other in placed):
                placed.append(box)
                break
            label.remove()
        else:  # every candidate collides: keep the first position
            label = ax.annotate(text, (x, y), textcoords="offset points", xytext=candidates[0],
                                fontsize=7, color=INK)
            placed.append(label.get_window_extent(renderer))


def figure_r5(common: pd.DataFrame, path: Path, scope: str, sizes: dict) -> None:
    heuristics = [h for h in HEURISTIC_NAMES if h in set(common["heuristic"]) and sizes.get(h, 0) > 0]
    if not heuristics:
        return
    fig, axes = plt.subplots(1, len(heuristics), figsize=(3.8 * len(heuristics), 3.5), facecolor=SURFACE)
    axes = np.atleast_1d(axes)
    for ax, heuristic in zip(axes, heuristics):
        sub = common[(common["heuristic"] == heuristic) & common["gap_mean_pct"].notna()]
        low, high = sub["median_nodes_expanded"].min(), sub["median_nodes_expanded"].max()
        use_log = high / max(low, 1) > 10
        # Points at identical coordinates share one merged label.
        groups: dict[tuple, list[str]] = {}
        for _, row in sub.iterrows():
            ax.scatter(row["median_nodes_expanded"], row["gap_mean_pct"], s=48,
                       color=ALGORITHM_COLORS.get(row["method"], INK2), edgecolor=SURFACE, linewidth=2, zorder=3)
            key = (round(row["median_nodes_expanded"], 6), round(row["gap_mean_pct"], 6))
            groups.setdefault(key, []).append(row["method"])
        if use_log:
            ax.set_xscale("log")
            ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:,.0f}"))
            ax.xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
            ax.set_xlim(low / 1.6, high * 2.5)
        else:
            pad = max((high - low) * 0.15, 2.0)
            ax.set_xlim(low - pad, high + 3 * pad)
        ax.set_xlabel("Median nodes expanded (common-solved" + (", log)" if use_log else ")"))
        y_low, y_high = sub["gap_mean_pct"].min(), sub["gap_mean_pct"].max()
        y_pad = max((y_high - y_low) * 0.18, 1.0)
        ax.set_ylim(y_low - y_pad, y_high + y_pad)
        _place_labels(fig, ax, groups)
        ax.set_title(f"{HEURISTIC_NAMES.get(heuristic, heuristic)} (n={sizes[heuristic]} common tasks)", fontsize=9, color=INK)
        ax.grid(color=GRID, linewidth=0.6)
        ax.set_axisbelow(True)
        _style(ax)
    axes[0].set_ylabel("Mean optimality gap (%)")
    fig.suptitle("R5 · Search effort vs plan quality on common-solved tasks", fontsize=10, color=INK, x=0.01, ha="left")
    _stamp(fig, scope)
    fig.tight_layout(rect=(0, 0.04, 1, 0.95))
    fig.savefig(path, dpi=200, facecolor=SURFACE)
    plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--runs", nargs="+", type=Path, required=True)
    parser.add_argument("--refs", type=Path, default=ROOT / "results" / "raw" / "faraz_optimal_refs.csv")
    parser.add_argument("--tag", required=True)
    parser.add_argument("--scope", required=True, help="text stamped on every figure, e.g. 'PILOT: easy tier only'")
    parser.add_argument("--config-id", default="pre-experiment-v2")
    args = parser.parse_args()

    derived = ROOT / "results" / "derived" / args.config_id / args.tag
    figures = ROOT / "results" / "figures" / args.config_id / args.tag
    own_outputs = [derived / f"{n}.csv" for n in ("coverage", "quality", "common_solved", "gap_distribution")]
    own_outputs += [derived / "summary.md", figures / "R3_coverage.png", figures / "R4_gap_distribution.png",
                    figures / "R5_effort_vs_quality.png"]
    if any(path.exists() for path in own_outputs):
        raise SystemExit(f"refusing to overwrite existing output for tag {args.tag!r}")
    derived.mkdir(parents=True, exist_ok=True)
    figures.mkdir(parents=True, exist_ok=True)

    df = attach_references(load_runs(args.runs), pd.read_csv(args.refs))
    coverage = coverage_table(df)
    quality = quality_table(df)
    common, sizes = common_solved_table(df)
    distribution = gap_distribution(df)
    for name, frame in (("coverage", coverage), ("quality", quality), ("common_solved", common), ("gap_distribution", distribution)):
        frame.to_csv(derived / f"{name}.csv", index=False)

    figure_r3(coverage, figures / "R3_coverage.png", args.scope)
    figure_r4(df, figures / "R4_gap_distribution.png", args.scope)
    figure_r5(common, figures / "R5_effort_vs_quality.png", args.scope, sizes)

    lines = [
        f"# Search analysis: {args.tag}",
        "",
        f"Scope: {args.scope}",
        f"Inputs: {', '.join(p.as_posix() for p in args.runs)}; references: {args.refs.as_posix()}",
        f"Runs: {len(df)}; tasks: {df[['domain', 'problem_id']].drop_duplicates().shape[0]}",
        "",
        "## Coverage",
        to_markdown(coverage[["heuristic", "method", "attempted", "success", "invalid_plan", "unsolved", "timeout", "memory_limit", "planner_error", "coverage_pct"]]),
        "",
        "## Quality on each method's own solved set",
        to_markdown(quality[["heuristic", "method", "solved_valid", "gap_n", "optimal_n", "gap_mean_pct", "gap_median_pct", "gap_max_pct", "median_search_time_s", "median_nodes_expanded"]]),
        "",
        "## Paired comparison on common-solved tasks",
        to_markdown(common[["heuristic", "method", "common_solved_n", "gap_n", "optimal_n", "gap_mean_pct", "median_nodes_expanded", "median_search_time_s"]]),
        "",
        "## Gap distribution (counts)",
        to_markdown(distribution),
    ]
    (derived / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {derived} and {figures}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
