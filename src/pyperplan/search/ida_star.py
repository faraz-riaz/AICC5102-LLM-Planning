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

"""Iterative Deepening A* (IDA*) over grounded tasks.

This is *not* Pyperplan's ``iterative_deepening_search`` (``-s ids``), which is
uninformed depth-bounded search. IDA* (Korf 1985) runs repeated depth-first
searches bounded by an f-cost threshold, ``f = g + h``:

* the first threshold is ``h(initial state)``;
* a node whose f exceeds the threshold is not expanded, and the smallest such
  f becomes the next threshold;
* if an iteration prunes nothing by the threshold and finds no goal, the
  (cycle-free) search space is exhausted and the task is unsolvable.

Memory: only the current path is stored, plus each path node's successor list
(``O(depth * branching)``). There is **no** transposition table, so states
reachable by many paths are re-expanded, within and across iterations. IDA*'s
small frontier memory therefore does not make it fast; on transposition-rich
domains it can be exponentially slower than A*. Peak process memory still
includes the grounded task and heuristic data structures.
"""

from __future__ import annotations

import logging
import math
import time
from numbers import Real

from search import searchspace
from search.a_star import (
    SearchError,
    SearchResult,
    SearchStatus,
    _action_cost,
    _heuristic_value,
    _log_result,
)


def _successor_key(item) -> str:
    operator = item[0]
    return getattr(operator, "name", repr(operator))


def ida_star_search_result(
    task,
    heuristic,
    time_limit_s: float | None = None,
) -> SearchResult:
    """Run IDA* and return a structured result.

    Search details:

    * goal test on generation for nodes inside the current bound (and on the
      root before the first iteration);
    * cycle detection against the states on the *current path* only;
    * successors visited in operator-name order (deterministic);
    * heuristic values and action costs validated exactly as in A*
      (``+inf`` = dead end, pruned and counted; NaN/negative/non-numeric =
      ``error``).

    Counters: ``nodes_expanded`` and ``nodes_generated`` are cumulative over
    all iterations (re-expansions included). ``cycles_pruned`` counts
    successors discarded because their state is already on the path.
    ``iteration_bounds`` lists the f-threshold of each iteration started.

    Optimality: with an admissible heuristic and non-negative action costs the
    first plan found is optimal. With an inadmissible heuristic the plan is
    valid but may be suboptimal.

    ``time_limit_s`` is a cooperative ``perf_counter`` deadline; process-level
    time and memory limits must be enforced externally.
    """
    started_at = time.perf_counter()
    if time_limit_s is not None:
        if (
            isinstance(time_limit_s, bool)
            or not isinstance(time_limit_s, Real)
            or not math.isfinite(time_limit_s)
            or time_limit_s <= 0
        ):
            raise ValueError("time_limit_s must be a finite positive number")
        deadline = started_at + float(time_limit_s)
    else:
        deadline = None

    nodes_generated = 1
    nodes_expanded = 0
    dead_ends_pruned = 0
    cycles_pruned = 0
    bounds: list[float] = []

    def finish(
        status: SearchStatus,
        *,
        plan: list[object] | None = None,
        plan_cost: float | None = None,
        failure_detail: str | None = None,
    ) -> SearchResult:
        result = SearchResult(
            status=status,
            plan=plan,
            plan_length=len(plan) if plan is not None else None,
            plan_cost=plan_cost,
            nodes_generated=nodes_generated,
            nodes_expanded=nodes_expanded,
            nodes_reopened=None,
            stale_nodes_skipped=None,
            dead_ends_pruned=dead_ends_pruned,
            wall_time_s=time.perf_counter() - started_at,
            failure_detail=failure_detail,
            iterations=len(bounds),
            iteration_bounds=tuple(bounds),
            cycles_pruned=cycles_pruned,
        )
        _log_result(result)
        return result

    def timed_out() -> bool:
        return deadline is not None and time.perf_counter() >= deadline

    try:
        root = searchspace.make_root_node(task.initial_state)
        root_h = _heuristic_value(heuristic, root)
        logging.info("Initial h value: %s", root_h)
        if root_h == math.inf:
            dead_ends_pruned += 1
            return finish(
                "unsolved",
                failure_detail="initial state flagged as a dead end (h=+inf)",
            )
        if task.goal_reached(task.initial_state):
            return finish("solved", plan=[], plan_cost=0.0)

        bound = root_h
        while True:
            bounds.append(bound)
            next_bound = math.inf
            # Each frame is [node, sorted successor list or None, next index].
            stack: list[list] = [[root, None, 0]]
            on_path = {task.initial_state}
            while stack:
                if timed_out():
                    return finish(
                        "timeout", failure_detail="cooperative time limit reached"
                    )
                frame = stack[-1]
                node = frame[0]
                if frame[1] is None:
                    frame[1] = sorted(
                        task.get_successor_states(node.state), key=_successor_key
                    )
                    nodes_expanded += 1
                successors = frame[1]
                if frame[2] >= len(successors):
                    stack.pop()
                    on_path.discard(node.state)
                    continue

                operator, successor_state = successors[frame[2]]
                frame[2] += 1
                step_cost = _action_cost(operator)
                nodes_generated += 1
                if successor_state in on_path:
                    cycles_pruned += 1
                    continue
                child = searchspace.make_child_node(
                    node, operator, successor_state, step_cost
                )
                child_h = _heuristic_value(heuristic, child)
                if child_h == math.inf:
                    dead_ends_pruned += 1
                    continue
                child_f = child.g + child_h
                if child_f > bound:
                    if child_f < next_bound:
                        next_bound = child_f
                    continue
                if task.goal_reached(successor_state):
                    plan = child.extract_solution()
                    return finish("solved", plan=plan, plan_cost=float(child.g))
                on_path.add(successor_state)
                stack.append([child, None, 0])

            logging.info(
                "IDA* iteration %d (bound %s) finished; next bound %s",
                len(bounds),
                bound,
                next_bound,
            )
            if next_bound == math.inf:
                return finish(
                    "unsolved",
                    failure_detail="search space exhausted: no node exceeded the bound",
                )
            bound = next_bound
    except Exception as error:  # Convert planner/heuristic failures for runners.
        logging.exception("IDA* search failed")
        return finish("error", failure_detail=f"{type(error).__name__}: {error}")


def ida_star_search(task, heuristic):
    """Legacy-style adapter returning a plan or ``None``.

    Raises ``SearchError`` when the structured search reports ``error``.
    """
    result = ida_star_search_result(task, heuristic)
    if result.status == "error":
        raise SearchError(result.failure_detail)
    return result.plan
