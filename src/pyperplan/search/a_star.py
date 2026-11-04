#
# This file is part of pyperplan.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""A*, weighted A*, and greedy best-first search over grounded tasks.

The original Pyperplan-compatible ``astar_search`` entry point still returns a
plan or ``None``.  ``astar_search_result`` is the instrumented project API for
validation and future experiment-runner integration.
"""

from __future__ import annotations

import heapq
import logging
import math
import time
from dataclasses import dataclass
from numbers import Real
from typing import Callable, Literal

from search import searchspace


SearchStatus = Literal["solved", "unsolved", "timeout", "error"]


@dataclass(frozen=True)
class SearchResult:
    """Structured outcome from an instrumented best-first search.

    ``nodes_generated`` includes the root and every applicable successor node
    constructed, including duplicates. ``nodes_expanded`` counts best-g nodes
    whose successors are enumerated; a popped goal is not expanded.
    """

    status: SearchStatus
    plan: list[object] | None
    plan_length: int | None
    plan_cost: float | None
    nodes_generated: int
    nodes_expanded: int
    nodes_reopened: int
    stale_nodes_skipped: int
    dead_ends_pruned: int
    wall_time_s: float
    failure_detail: str | None = None

    @property
    def solved(self) -> bool:
        return self.status == "solved"


class SearchError(RuntimeError):
    """Raised by the legacy adapter when structured search reports an error."""


class InvalidHeuristicError(ValueError):
    """Raised when a heuristic returns an unusable value."""


class InvalidActionCostError(ValueError):
    """Raised when an operator exposes an invalid path cost."""


def ordered_node_astar(node, h, node_tiebreaker):
    """Return the stable A* frontier tuple ``(g+h, h, FIFO, node)``."""
    return (node.g + h, h, node_tiebreaker, node)


def ordered_node_weighted_astar(weight):
    """Return an inherited weighted-A* frontier-entry factory."""
    return lambda node, h, node_tiebreaker: (
        node.g + weight * h,
        h,
        node_tiebreaker,
        node,
    )


def ordered_node_greedy_best_first(node, h, node_tiebreaker):
    """Return the inherited greedy best-first tuple ``(h, h, FIFO, node)``."""
    return (h, h, node_tiebreaker, node)


def _heuristic_value(heuristic, node) -> float:
    raw_value = heuristic(node)
    if isinstance(raw_value, bool) or not isinstance(raw_value, Real):
        raise InvalidHeuristicError(
            f"heuristic returned non-numeric {raw_value!r} for state {node.state!r}"
        )
    value = float(raw_value)
    if math.isnan(value) or value == -math.inf:
        raise InvalidHeuristicError(
            f"heuristic returned invalid value {raw_value!r} for state {node.state!r}"
        )
    if value < 0:
        raise InvalidHeuristicError(
            f"heuristic returned negative value {raw_value!r} for state {node.state!r}"
        )
    # Positive infinity is Pyperplan's established dead-end signal. The core
    # flags it through dead_ends_pruned instead of silently coercing the value.
    return value


def _action_cost(action) -> float:
    raw_cost = getattr(action, "cost", 1)
    if isinstance(raw_cost, bool) or not isinstance(raw_cost, Real):
        raise InvalidActionCostError(
            f"operator {getattr(action, 'name', action)!r} has non-numeric cost "
            f"{raw_cost!r}"
        )
    cost = float(raw_cost)
    if not math.isfinite(cost) or cost < 0:
        raise InvalidActionCostError(
            f"operator {getattr(action, 'name', action)!r} has invalid cost "
            f"{raw_cost!r}"
        )
    return cost


def _make_result(
    *,
    status: SearchStatus,
    started_at: float,
    plan: list[object] | None,
    plan_cost: float | None,
    nodes_generated: int,
    nodes_expanded: int,
    nodes_reopened: int,
    stale_nodes_skipped: int,
    dead_ends_pruned: int,
    failure_detail: str | None = None,
) -> SearchResult:
    return SearchResult(
        status=status,
        plan=plan,
        plan_length=len(plan) if plan is not None else None,
        plan_cost=plan_cost,
        nodes_generated=nodes_generated,
        nodes_expanded=nodes_expanded,
        nodes_reopened=nodes_reopened,
        stale_nodes_skipped=stale_nodes_skipped,
        dead_ends_pruned=dead_ends_pruned,
        wall_time_s=time.perf_counter() - started_at,
        failure_detail=failure_detail,
    )


def _log_result(result: SearchResult) -> None:
    logging.info("Search status: %s", result.status)
    logging.info("%d Nodes generated", result.nodes_generated)
    logging.info("%d Nodes expanded", result.nodes_expanded)
    logging.info("%d Nodes reopened", result.nodes_reopened)
    logging.info("Search wall time: %.6f", result.wall_time_s)
    if result.solved:
        logging.info("Plan length: %d", result.plan_length)
        logging.info("Plan cost: %s", result.plan_cost)
    if result.failure_detail:
        logging.info("Search detail: %s", result.failure_detail)


def greedy_best_first_search(task, heuristic, use_relaxed_plan=False):
    """Run the inherited generic best-first core with greedy ordering."""
    return astar_search(
        task, heuristic, ordered_node_greedy_best_first, use_relaxed_plan
    )


def weighted_astar_search(task, heuristic, weight=5, use_relaxed_plan=False):
    """Run the inherited generic best-first core with weighted-A* ordering."""
    return astar_search(
        task, heuristic, ordered_node_weighted_astar(weight), use_relaxed_plan
    )


def astar_search_result(
    task,
    heuristic,
    make_open_entry: Callable = ordered_node_astar,
    use_relaxed_plan: bool = False,
    time_limit_s: float | None = None,
) -> SearchResult:
    """Run best-first search and return a structured, instrumented result.

    With ``ordered_node_astar``, nodes are ordered by ``g + h``. Best known
    g-values provide duplicate detection; a strictly better path updates the
    state and reopens it even after expansion. The first popped goal is optimal
    only when the heuristic and cost-model assumptions required by A* hold.

    ``time_limit_s`` is a cooperative monotonic-clock guard. The future shared
    runner must still enforce the configured process-tree timeout and memory
    cap externally.

    Timing uses ``time.perf_counter`` (monotonic, sub-microsecond resolution)
    rather than ``time.monotonic``, whose Windows resolution is ~15.6 ms and
    reports 0 s for most small searches.
    """
    started_at = time.perf_counter()
    if time_limit_s is not None:
        if not isinstance(time_limit_s, Real) or not math.isfinite(time_limit_s):
            raise ValueError("time_limit_s must be a finite positive number")
        if time_limit_s <= 0:
            raise ValueError("time_limit_s must be a finite positive number")
        deadline = started_at + float(time_limit_s)
    else:
        deadline = None

    frontier = []
    best_g = {task.initial_state: 0.0}
    expanded_g: dict[object, float] = {}
    node_tiebreaker = 0
    nodes_generated = 1
    nodes_expanded = 0
    nodes_reopened = 0
    stale_nodes_skipped = 0
    dead_ends_pruned = 0

    def finish(
        status: SearchStatus,
        *,
        plan: list[object] | None = None,
        plan_cost: float | None = None,
        failure_detail: str | None = None,
    ) -> SearchResult:
        result = _make_result(
            status=status,
            started_at=started_at,
            plan=plan,
            plan_cost=plan_cost,
            nodes_generated=nodes_generated,
            nodes_expanded=nodes_expanded,
            nodes_reopened=nodes_reopened,
            stale_nodes_skipped=stale_nodes_skipped,
            dead_ends_pruned=dead_ends_pruned,
            failure_detail=failure_detail,
        )
        _log_result(result)
        return result

    try:
        root = searchspace.make_root_node(task.initial_state)
        init_h = _heuristic_value(heuristic, root)
        logging.info("Initial h value: %s", init_h)
        if init_h == math.inf:
            dead_ends_pruned += 1
            return finish(
                "unsolved",
                failure_detail="initial state flagged as a dead end (h=+inf)",
            )
        heapq.heappush(
            frontier, make_open_entry(root, init_h, node_tiebreaker)
        )

        while frontier:
            if deadline is not None and time.perf_counter() >= deadline:
                return finish("timeout", failure_detail="cooperative time limit reached")

            _priority, _h, _tie, node = heapq.heappop(frontier)
            state = node.state
            if node.g != best_g.get(state):
                stale_nodes_skipped += 1
                continue

            if task.goal_reached(state):
                plan = node.extract_solution()
                return finish("solved", plan=plan, plan_cost=float(node.g))

            expanded_g[state] = node.g
            nodes_expanded += 1
            relaxed_plan = None
            if use_relaxed_plan:
                _relaxed_h, relaxed_plan = heuristic.calc_h_with_plan(
                    searchspace.make_root_node(state)
                )

            successors = sorted(
                task.get_successor_states(state),
                key=lambda item: getattr(item[0], "name", repr(item[0])),
            )
            for operator, successor_state in successors:
                if deadline is not None and time.perf_counter() >= deadline:
                    return finish(
                        "timeout", failure_detail="cooperative time limit reached"
                    )
                if use_relaxed_plan and relaxed_plan and operator.name not in relaxed_plan:
                    continue

                step_cost = _action_cost(operator)
                successor = searchspace.make_child_node(
                    node, operator, successor_state, step_cost
                )
                nodes_generated += 1
                old_g = best_g.get(successor_state, math.inf)
                if successor.g >= old_g:
                    continue

                successor_h = _heuristic_value(heuristic, successor)
                if successor_h == math.inf:
                    dead_ends_pruned += 1
                    continue

                if successor_state in expanded_g:
                    nodes_reopened += 1
                best_g[successor_state] = successor.g
                node_tiebreaker += 1
                heapq.heappush(
                    frontier,
                    make_open_entry(successor, successor_h, node_tiebreaker),
                )

        return finish("unsolved")
    except Exception as error:  # Convert planner/heuristic failures for runners.
        logging.exception("A* search failed")
        return finish(
            "error", failure_detail=f"{type(error).__name__}: {error}"
        )


def astar_search(
    task,
    heuristic,
    make_open_entry=ordered_node_astar,
    use_relaxed_plan=False,
):
    """Legacy Pyperplan adapter returning a plan or ``None``.

    Errors remain explicit: malformed heuristic outputs and invalid action
    costs raise ``SearchError`` instead of being mistaken for an unsolved task.
    """
    result = astar_search_result(
        task,
        heuristic,
        make_open_entry=make_open_entry,
        use_relaxed_plan=use_relaxed_plan,
    )
    if result.status == "error":
        raise SearchError(result.failure_detail)
    return result.plan
