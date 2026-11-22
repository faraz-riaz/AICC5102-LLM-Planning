"""Tests for the heuristic-reliability workstream (experiments/heuristic_reliability/).

Three groups, all fast and offline (no LLM call, no long planner run):
1. Unit tests of the selection rules and statistics used in the analysis.
2. Integrity of the frozen trial heuristics and the training-only selection.
3. Consistency of the committed results with the raw data they come from.
"""
from __future__ import annotations

import csv
import hashlib
import math
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

import pytest

from test_astar import ROOT, load_task

RELIABILITY = ROOT / "experiments" / "heuristic_reliability"
SEARCH = ROOT / "experiments" / "search_algorithms"
PYPERPLAN = ROOT / "src" / "pyperplan"
for path in (str(RELIABILITY), str(SEARCH), str(PYPERPLAN)):
    if path not in sys.path:
        sys.path.insert(0, path)

import generate_and_select_heuristics as selection  # noqa: E402
import search_adapters  # noqa: E402
import trial_analysis  # noqa: E402

sys.path.remove(str(PYPERPLAN))

ARTIFACTS = ROOT / "artifacts" / "m3"
DERIVED = ROOT / "results" / "derived" / "heuristic_reliability"
SAMPLED = ROOT / "results" / "raw" / "sampled_states"
DOMAINS = ["blocksworld", "miconic", "transport"]
TRIALS = ["trial-01", "trial-02", "trial-03"]
EPS = 1e-9


def read_csv(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def load_test_manifest() -> list[dict]:
    return read_csv(ROOT / "benchmarks" / "manifest.csv")


HEURISTIC_MANIFEST = read_csv(ARTIFACTS / "heuristic_manifest.csv")


# ---------------------------------------------------------------- 1. unit tests

VALID = '''
from heuristics.heuristic_base import Heuristic

class blocksworldLLMHeuristic(Heuristic):
    def __init__(self, task):
        self.goals = task.goals

    def __call__(self, node):
        return len(self.goals - node.state)
'''


@pytest.mark.parametrize(
    ("code", "reason"),
    [
        (VALID, None),
        ("", "no_code"),
        ("def f(:\n  pass", "syntax_error"),
        ("x = 1\n", "no_heuristic_class"),
        (VALID + "\nclass SecondHeuristic(Heuristic):\n    pass\n", "multiple_heuristic_classes"),
        ("from heuristics.relaxation import hFFHeuristic\n" + VALID, "extra_heuristic_names"),
        ("from heuristics.relaxation import *\n" + VALID, "star_import"),
    ],
)
def test_candidate_check_rejects_unusable_answers(code: str, reason: str | None) -> None:
    result = selection.check_code(code)
    if reason is None:
        assert result is None
    else:
        assert result is not None and result.startswith(reason)


def test_expansion_score_matches_the_authors_formula() -> None:
    def row(nodes, status="success"):
        return {"status": status, "nodes_expanded": nodes, "wall_time_s": "1"}

    assert selection.expansion_score(row(50, status="timeout")) == 0.0
    assert selection.expansion_score(row("")) == 0.0
    assert selection.expansion_score(row(100)) == 1.0
    assert selection.expansion_score(row(1000)) == pytest.approx(0.5)  # 1 - log(1e3)/log(1e6)
    assert selection.expansion_score(row(1_000_001)) == 0.0


def test_time_score_matches_the_authors_formula() -> None:
    def row(seconds, status="success"):
        return {"status": status, "nodes_expanded": "1", "wall_time_s": str(seconds)}

    assert selection.time_score(row(0.5, status="timeout")) == 0.0
    assert selection.time_score(row(0.9)) == 1.0
    assert selection.time_score(row(60)) == pytest.approx(1 - math.log(60) / math.log(1800))
    assert selection.time_score(row(1800)) == pytest.approx(0.0)


def test_spearman_handles_order_ties_and_degenerate_input() -> None:
    assert trial_analysis.spearman([1, 2, 3, 4], [10, 20, 30, 40]) == pytest.approx(1.0)
    assert trial_analysis.spearman([1, 2, 3, 4], [4, 3, 2, 1]) == pytest.approx(-1.0)
    # ties get average ranks: x ranks [1.5, 1.5, 3, 4] against y ranks [1, 2, 3, 4]
    assert trial_analysis.spearman([1, 1, 2, 3], [1, 2, 3, 4]) == pytest.approx(0.9486833)
    assert trial_analysis.spearman([1, 2], [1, 2]) is None  # fewer than 3 points
    assert trial_analysis.spearman([5, 5, 5], [1, 2, 3]) is None  # no variation


# --------------------------------------------- 2. frozen heuristics and selection

def test_nine_frozen_heuristics_one_per_trial_and_domain() -> None:
    pairs = Counter((row["heuristic_trial_id"], row["domain"]) for row in HEURISTIC_MANIFEST)
    assert pairs == Counter({(t, d): 1 for t in TRIALS for d in DOMAINS})


@pytest.mark.parametrize("row", HEURISTIC_MANIFEST, ids=lambda r: Path(r["selected_file"]).stem)
def test_frozen_heuristic_file_matches_its_manifest_hash(row: dict) -> None:
    data = (ROOT / row["selected_file"]).read_bytes()
    assert hashlib.sha256(data).hexdigest() == row["selected_sha256"]


@pytest.mark.parametrize("row", HEURISTIC_MANIFEST, ids=lambda r: Path(r["selected_file"]).stem)
def test_frozen_heuristic_solves_an_easy_test_task_with_a_valid_plan(row: dict) -> None:
    """Each frozen heuristic loads through the shared adapter and guides GBFS to a valid plan."""
    path = ROOT / row["selected_file"]
    heuristic_class = search_adapters.load_heuristic_class(path.stem, path)
    first_easy = min(r["problem_id"] for r in load_test_manifest()
                     if r["domain"] == row["domain"] and r["difficulty"] == "easy")
    task = load_task(row["domain"], f"{first_easy}.pddl")
    result = search_adapters.run_search("gbfs", task, heuristic_class(task), time_limit_s=30)
    valid, detail, _ = search_adapters.replay_plan(task, result.plan)
    assert valid, detail


def test_selection_used_training_tasks_only() -> None:
    allowed = set(selection.TRAINING_IDS)
    test_ids = {row["problem_id"] for row in load_test_manifest()}
    seen = set()
    for path in sorted((ARTIFACTS / "selection").rglob("*_training_runs.csv")):
        for run in read_csv(path):
            seen.add(run["problem_id"])
    assert seen == allowed
    assert not seen & test_ids


def test_each_selected_file_is_the_best_scored_candidate() -> None:
    """Winner = most solved, then highest expansion score, then time score, then lowest number."""
    for row in HEURISTIC_MANIFEST:
        scores = read_csv(ARTIFACTS / "selection" / row["heuristic_trial_id"] / f"{row['domain']}_scores.csv")
        ranked = sorted(
            scores,
            key=lambda s: (-int(s["solved"]), -float(s["expansion_score"]), -float(s["time_score"]), s["candidate"]),
        )
        winners = [s["candidate"] for s in scores if s["selected"] == "True"]
        assert winners == [ranked[0]["candidate"]], (row["heuristic_trial_id"], row["domain"])


# ------------------------------------------- 3. committed results are consistent

def test_trial_runs_cover_the_full_matrix_exactly_once() -> None:
    runs = read_csv(DERIVED / "trial_heuristic_runs.csv")
    tasks = {(r["domain"], r["problem_id"]): r["difficulty"] for r in load_test_manifest()}
    keys = Counter((r["heuristic_trial_id"], r["algorithm_label"], r["domain"], r["problem_id"]) for r in runs)
    assert len(runs) == 1170
    assert max(keys.values()) == 1
    for trial in TRIALS:
        for label in ["gbfs", "astar", "weighted_astar-w1.5", "weighted_astar-w2"]:
            assert sum(1 for k in keys if k[0] == trial and k[1] == label) == 90
        assert sum(1 for k in keys if k[0] == trial and k[1] == "ida_star") == 30
    assert all((r["domain"], r["problem_id"]) in tasks for r in runs)
    assert all(r["time_limit_s"] == "60.0" and r["memory_limit_mib"] == "4096" for r in runs)
    assert all(r["plan_valid"] == "True" for r in runs if r["status"] == "success")


def test_overestimation_summary_recomputes_from_states_and_exact_costs() -> None:
    h_star = {
        r["state_id"]: float(r["h_star"])
        for r in read_csv(SAMPLED / "sampled_state_optimal_costs.csv")
        if r["reference_status"] == "proven"
    }
    counts = defaultdict(lambda: [0, 0, 0])  # sampled, eligible, overestimated
    for est in read_csv(DERIVED / "sampled_state_estimates.csv"):
        key = (est["domain"], est["heuristic_trial_id"])
        counts[key][0] += 1
        if est["state_id"] in h_star:
            counts[key][1] += 1
            counts[key][2] += float(est["h_value"]) > h_star[est["state_id"]] + EPS
    summary = read_csv(DERIVED / "overestimation_summary.csv")
    assert len(summary) == 12  # 3 domains x (archived + 3 trials)
    for row in summary:
        sampled, eligible, over = counts[(row["domain"], row["heuristic_trial_id"])]
        assert (sampled, eligible, over) == (
            int(row["sampled_states"]), int(row["eligible_states"]), int(row["overestimated_states"])
        )
        assert float(row["overestimate_rate"]) == pytest.approx(over / eligible, abs=1e-4)


def test_trial_stability_summary_recomputes_from_per_trial_coverage() -> None:
    per_trial = read_csv(DERIVED / "coverage_per_trial.csv")
    solved = defaultdict(int)
    for row in per_trial:
        solved[(row["algorithm"], row["heuristic"])] += int(row["solved"])
    for row in read_csv(DERIVED / "trial_stability_summary.csv"):
        if row["scope"] != "all":
            continue
        counts = [int(row["trial_01"]), int(row["trial_02"]), int(row["trial_03"])]
        assert counts == [solved[(row["algorithm"], t)] for t in TRIALS]
        assert float(row["mean"]) == pytest.approx(statistics.mean(counts), abs=0.01)
        assert float(row["sd_ddof1"]) == pytest.approx(statistics.stdev(counts), abs=0.01)
        assert int(row["archived"]) == solved[(row["algorithm"], "archived")]
