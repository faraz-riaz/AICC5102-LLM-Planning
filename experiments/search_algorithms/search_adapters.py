"""Uniform algorithm/heuristic adapters for the search-algorithm workstream.

This module is the integration surface intended for the future shared runner
(Amina). It does **not** schedule experiments or enforce process limits; it
only maps an ``(algorithm, heuristic, weight)`` request onto the project search
functions and returns ``search.a_star.SearchResult``.

Algorithms (identifiers from ``configs/experiment.v2.toml``):

* ``gbfs``            -> upstream ``search.gbfs.gbfs_early_goal_test``, called
                         unmodified through counting/deadline proxies;
* ``astar``           -> ``search.a_star.astar_search_result``;
* ``weighted_astar``  -> ``search.a_star.weighted_astar_search_result``;
* ``ida_star``        -> ``search.ida_star.ida_star_search_result``.

Heuristics: built-in ``zero``, ``hmax``, ``hff`` or a Python heuristic file
(e.g. the archived DeepSeek R1 heuristics), loaded the way Pyperplan's CLI
loads ``-H path.py``.

Callers must put ``src/pyperplan`` on ``sys.path`` before importing this module.
"""

from __future__ import annotations

import hashlib
import importlib.util
import math
import time
from pathlib import Path

from heuristics.relaxation import hFFHeuristic, hMaxHeuristic
from heuristics.zero import ZeroHeuristic
from search.a_star import (
    SearchResult,
    astar_search_result,
    weighted_astar_search_result,
)
from search.gbfs import gbfs_early_goal_test
from search.ida_star import ida_star_search_result


ROOT = Path(__file__).resolve().parents[2]
ALGORITHMS = ("gbfs", "astar", "weighted_astar", "ida_star")
BUILTIN_HEURISTICS = {"zero": ZeroHeuristic, "hmax": hMaxHeuristic, "hff": hFFHeuristic}
# Admissibility under the unit-cost model. hFF and LLM heuristics are not
# admissible in general; "unknown" means no admissibility claim is made.
HEURISTIC_ADMISSIBILITY = {"zero": "admissible", "hmax": "admissible", "hff": "inadmissible"}
LLM_HEURISTIC_FILES = {
    "deepseek-r1": {
        "blocksworld": "artifacts/upstream/deepseek-r1/blocksworld9_10.py",
        "miconic": "artifacts/upstream/deepseek-r1/miconic11_10.py",
        "transport": "artifacts/upstream/deepseek-r1/transport7_10.py",
    }
}
LLM_HEURISTIC_SET_IDS = {"deepseek-r1": "zenodo-17400964-deepseek-r1-selected"}


class HeuristicConfigurationError(ValueError):
    """Raised for unknown heuristic IDs or missing/invalid heuristic files."""


def file_sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def heuristic_file_for(heuristic_id: str, domain: str) -> Path | None:
    """Return the archived file for an LLM heuristic ID, or None for built-ins."""
    if heuristic_id in BUILTIN_HEURISTICS:
        return None
    try:
        return ROOT / LLM_HEURISTIC_FILES[heuristic_id][domain]
    except KeyError as error:
        raise HeuristicConfigurationError(
            f"unknown heuristic {heuristic_id!r} for domain {domain!r}"
        ) from error


def load_heuristic_class(heuristic_id: str, heuristic_file: Path | None = None):
    if heuristic_id in BUILTIN_HEURISTICS:
        return BUILTIN_HEURISTICS[heuristic_id]
    if heuristic_file is None or not Path(heuristic_file).is_file():
        raise HeuristicConfigurationError(f"heuristic file not found: {heuristic_file}")
    path = Path(heuristic_file)
    spec = importlib.util.spec_from_file_location(f"heuristic_{path.stem}", path)
    if spec is None or spec.loader is None:
        raise HeuristicConfigurationError(f"cannot import heuristic file {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    classes = [
        getattr(module, name)
        for name in dir(module)
        if name.endswith("Heuristic") and name != "Heuristic" and not name.startswith("_")
    ]
    if len(classes) != 1:
        raise HeuristicConfigurationError(
            f"expected exactly one *Heuristic class in {path}, found {len(classes)}"
        )
    return classes[0]


class _DeadlineReached(Exception):
    pass


class _CountingTask:
    """Read-only proxy that counts GBFS expansions/generations.

    ``gbfs_early_goal_test`` calls ``get_successor_states`` exactly once per
    expanded state, so each call is one expansion and its returned list adds
    to the generated count (same definition as A*: every applicable successor,
    duplicates included). The proxy also enforces a cooperative deadline.
    """

    def __init__(self, task, deadline: float | None) -> None:
        self._task = task
        self._deadline = deadline
        self.initial_state = task.initial_state
        self.expanded = 0
        self.generated = 1

    def goal_reached(self, state) -> bool:
        return self._task.goal_reached(state)

    def get_successor_states(self, state):
        if self._deadline is not None and time.perf_counter() >= self._deadline:
            raise _DeadlineReached
        successors = self._task.get_successor_states(state)
        self.expanded += 1
        self.generated += len(successors)
        return successors

    def __getattr__(self, name):
        return getattr(self._task, name)


class _ObservingHeuristic:
    """Pass-through heuristic proxy: counts +inf values and checks the deadline.
    It never alters the value returned to GBFS."""

    def __init__(self, heuristic, deadline: float | None) -> None:
        self._heuristic = heuristic
        self._deadline = deadline
        self.infinite_values = 0

    def __call__(self, node):
        if self._deadline is not None and time.perf_counter() >= self._deadline:
            raise _DeadlineReached
        value = self._heuristic(node)
        if value == math.inf:
            self.infinite_values += 1
        return value

    def __getattr__(self, name):
        return getattr(self._heuristic, name)


def gbfs_search_result(task, heuristic, time_limit_s: float | None = None) -> SearchResult:
    """Run the paper's GBFS unmodified and report a ``SearchResult``.

    ``plan_cost`` is the sum of action costs (unit costs for Pyperplan tasks).
    ``nodes_reopened``/``stale_nodes_skipped`` are ``None`` (not applicable).
    Heuristic values are *not* validated, preserving baseline behaviour.
    """
    started_at = time.perf_counter()
    deadline = started_at + time_limit_s if time_limit_s is not None else None
    counting_task = _CountingTask(task, deadline)
    observed = _ObservingHeuristic(heuristic, deadline)
    status, plan, detail = "unsolved", None, None
    try:
        plan = gbfs_early_goal_test(counting_task, observed)
        status = "solved" if plan is not None else "unsolved"
    except _DeadlineReached:
        status, detail = "timeout", "cooperative time limit reached"
    except Exception as error:  # noqa: BLE001 - reported, not swallowed
        status, detail = "error", f"{type(error).__name__}: {error}"
    plan_cost = (
        float(sum(getattr(op, "cost", 1) for op in plan)) if plan is not None else None
    )
    return SearchResult(
        status=status,
        plan=plan,
        plan_length=len(plan) if plan is not None else None,
        plan_cost=plan_cost,
        nodes_generated=counting_task.generated,
        nodes_expanded=counting_task.expanded,
        nodes_reopened=None,
        stale_nodes_skipped=None,
        dead_ends_pruned=observed.infinite_values,
        wall_time_s=time.perf_counter() - started_at,
        failure_detail=detail,
    )


def run_search(
    algorithm: str,
    task,
    heuristic,
    *,
    weight: float | None = None,
    time_limit_s: float | None = None,
) -> SearchResult:
    """Dispatch one search. ``weight`` is required for (and only for) WA*."""
    if algorithm not in ALGORITHMS:
        raise ValueError(f"unknown algorithm {algorithm!r}; expected one of {ALGORITHMS}")
    if (algorithm == "weighted_astar") != (weight is not None):
        raise ValueError("weight must be given for weighted_astar and only for it")
    if algorithm == "gbfs":
        return gbfs_search_result(task, heuristic, time_limit_s)
    if algorithm == "astar":
        return astar_search_result(task, heuristic, time_limit_s=time_limit_s)
    if algorithm == "weighted_astar":
        return weighted_astar_search_result(
            task, heuristic, weight, time_limit_s=time_limit_s
        )
    return ida_star_search_result(task, heuristic, time_limit_s=time_limit_s)


def replay_plan(task, plan) -> tuple[bool, str, float | None]:
    """Independent STRIPS replay: (valid, detail, summed cost)."""
    if plan is None:
        return False, "no plan returned", None
    state = task.initial_state
    cost = 0.0
    for step, operator in enumerate(plan, start=1):
        if not operator.applicable(state):
            return False, f"step {step} is inapplicable: {operator.name}", None
        state = operator.apply(state)
        cost += float(getattr(operator, "cost", 1))
    if not task.goal_reached(state):
        return False, f"goal not reached after {len(plan)} steps", None
    return True, f"goal reached after {len(plan)} steps", cost
