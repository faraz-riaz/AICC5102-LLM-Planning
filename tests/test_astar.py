from __future__ import annotations

import heapq
import importlib.util
import math
import random
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
PYPERPLAN = ROOT / "src" / "pyperplan"
sys.path.insert(0, str(PYPERPLAN))

import grounding  # noqa: E402
from heuristics.relaxation import hMaxHeuristic  # noqa: E402
from heuristics.zero import ZeroHeuristic  # noqa: E402
from pddl.parser import Parser  # noqa: E402
from heuristics.relaxation import hFFHeuristic  # noqa: E402
from search import searchspace  # noqa: E402
from search.a_star import (  # noqa: E402
    SearchError,
    astar_search,
    astar_search_result,
    greedy_best_first_search,
    ordered_node_astar,
)
from search.gbfs import gbfs_early_goal_test  # noqa: E402

sys.path.remove(str(PYPERPLAN))
loaded_tools = sys.modules.get("tools")
if loaded_tools and Path(getattr(loaded_tools, "__file__", "")).resolve() == (
    PYPERPLAN / "tools.py"
).resolve():
    sys.modules.pop("tools")


BENCHMARKS = ROOT / "benchmarks" / "ipc2023-learning" / "testing"


@dataclass(frozen=True)
class GraphAction:
    name: str
    target: str
    cost: float = 1


class GraphTask:
    def __init__(self, edges, initial="S", goal="G") -> None:
        self.initial_state = initial
        self.goal = goal
        self.edges = edges

    def goal_reached(self, state) -> bool:
        return state == self.goal

    def get_successor_states(self, state):
        return [(action, action.target) for action in self.edges.get(state, [])]


class TableHeuristic:
    def __init__(self, values=None) -> None:
        self.values = values or {}

    def __call__(self, node):
        return self.values.get(node.state, 0)


def load_task(domain: str, problem: str):
    domain_file = BENCHMARKS / domain / "domain.pddl"
    problem_file = BENCHMARKS / domain / problem
    parser = Parser(str(domain_file), str(problem_file))
    parsed_domain = parser.parse_domain()
    parsed_problem = parser.parse_problem(parsed_domain)
    return grounding.ground(parsed_problem)


def replay_plan(task, plan) -> float:
    state = task.initial_state
    cost = 0.0
    for operator in plan:
        assert operator.applicable(state)
        state = operator.apply(state)
        cost += float(getattr(operator, "cost", 1))
    assert task.goal_reached(state)
    return cost


def independent_uniform_cost(task) -> tuple[float | None, list[object] | None]:
    """Small independent Dijkstra reference; does not call project A*."""
    frontier = [(0.0, 0, task.initial_state, [])]
    best = {task.initial_state: 0.0}
    tie = 0
    while frontier:
        cost, _tie, state, plan = heapq.heappop(frontier)
        if cost != best.get(state):
            continue
        if task.goal_reached(state):
            return cost, plan
        for operator, successor in task.get_successor_states(state):
            next_cost = cost + float(getattr(operator, "cost", 1))
            if next_cost < best.get(successor, math.inf):
                best[successor] = next_cost
                tie += 1
                heapq.heappush(
                    frontier, (next_cost, tie, successor, [*plan, operator])
                )
    return None, None


def test_priority_ordering_and_stable_tie_breaking() -> None:
    first = searchspace.SearchNode("first", None, None, 2)
    lower_h = searchspace.SearchNode("lower-h", None, None, 3)
    same_priority_later = searchspace.SearchNode("later", None, None, 2)
    frontier = [
        ordered_node_astar(first, 3, 0),
        ordered_node_astar(lower_h, 2, 1),
        ordered_node_astar(same_priority_later, 3, 2),
    ]
    heapq.heapify(frontier)

    assert heapq.heappop(frontier)[3].state == "lower-h"
    assert heapq.heappop(frontier)[3].state == "first"
    assert heapq.heappop(frontier)[3].state == "later"


def test_path_cost_accounting_uses_operator_costs() -> None:
    task = GraphTask(
        {
            "S": [GraphAction("expensive", "G", 9), GraphAction("to-a", "A", 2)],
            "A": [GraphAction("to-g", "G", 3)],
        }
    )

    result = astar_search_result(task, TableHeuristic())

    assert result.status == "solved"
    assert result.plan_cost == 5
    assert result.plan_length == 2
    assert [action.name for action in result.plan] == ["to-a", "to-g"]


def test_duplicate_states_are_not_reexpanded() -> None:
    task = GraphTask(
        {
            "S": [GraphAction("to-a", "A"), GraphAction("to-b", "B")],
            "B": [GraphAction("duplicate-a", "A")],
            "A": [GraphAction("to-g", "G")],
        }
    )

    result = astar_search_result(task, TableHeuristic())

    assert result.status == "solved"
    assert result.plan_cost == 2
    assert result.nodes_expanded == 3
    assert result.nodes_generated == 5
    assert result.nodes_reopened == 0


def test_equal_priority_successors_use_deterministic_operator_order() -> None:
    task = GraphTask(
        {
            "S": [GraphAction("z-path", "Z"), GraphAction("a-path", "A")],
            "A": [GraphAction("a-goal", "G")],
            "Z": [GraphAction("z-goal", "G")],
        }
    )

    result = astar_search_result(task, TableHeuristic())

    assert [action.name for action in result.plan] == ["a-path", "a-goal"]


def test_better_path_reopens_an_expanded_state() -> None:
    task = GraphTask(
        {
            "S": [GraphAction("expensive-a", "A", 5), GraphAction("to-b", "B", 1)],
            "B": [GraphAction("better-a", "A", 1)],
            "A": [GraphAction("to-c", "C", 1)],
            "C": [GraphAction("to-g", "G", 1)],
        }
    )
    heuristic = TableHeuristic({"A": 0, "B": 10, "C": 100, "G": 0})

    result = astar_search_result(task, heuristic)

    assert result.status == "solved"
    assert result.plan_cost == 4
    assert [action.name for action in result.plan] == [
        "to-b",
        "better-a",
        "to-c",
        "to-g",
    ]
    assert result.nodes_reopened == 1


def test_unsolvable_task_terminates_cleanly() -> None:
    result = astar_search_result(GraphTask({}), TableHeuristic())

    assert result.status == "unsolved"
    assert result.plan is None
    assert result.plan_cost is None
    assert result.nodes_generated == 1
    assert result.nodes_expanded == 1


@pytest.mark.parametrize("invalid_value", [math.nan, -math.inf, -1, "bad", True])
def test_invalid_heuristic_values_are_explicit_errors(invalid_value) -> None:
    task = GraphTask({})
    result = astar_search_result(task, TableHeuristic({"S": invalid_value}))

    assert result.status == "error"
    assert "InvalidHeuristicError" in result.failure_detail
    with pytest.raises(SearchError, match="InvalidHeuristicError"):
        astar_search(task, TableHeuristic({"S": invalid_value}))


def test_positive_infinity_is_counted_as_a_dead_end() -> None:
    task = GraphTask({"S": [GraphAction("dead", "D")]})
    result = astar_search_result(task, TableHeuristic({"D": math.inf}))

    assert result.status == "unsolved"
    assert result.dead_ends_pruned == 1


def test_cooperative_timeout_has_explicit_status() -> None:
    class SlowHeuristic:
        def __call__(self, node):
            time.sleep(0.01)
            return 0

    result = astar_search_result(
        GraphTask({"S": [GraphAction("loop", "S")]}),
        SlowHeuristic(),
        time_limit_s=0.001,
    )

    assert result.status == "timeout"
    assert "time limit" in result.failure_detail


@pytest.mark.parametrize(
    ("domain", "problem"),
    [
        ("blocksworld", "easy-p03.pddl"),
        ("miconic", "easy-p02.pddl"),
        ("transport", "easy-p01.pddl"),
    ],
)
def test_zero_and_hmax_match_independent_uniform_cost(domain, problem) -> None:
    task = load_task(domain, problem)
    reference_cost, reference_plan = independent_uniform_cost(task)
    assert reference_plan is not None
    assert replay_plan(task, reference_plan) == reference_cost

    zero_result = astar_search_result(task, ZeroHeuristic(task), time_limit_s=60)
    hmax_result = astar_search_result(task, hMaxHeuristic(task), time_limit_s=60)

    for result in (zero_result, hmax_result):
        assert result.status == "solved", result.failure_detail
        assert result.plan_cost == reference_cost
        assert replay_plan(task, result.plan) == result.plan_cost


def test_legacy_astar_adapter_still_returns_a_plan() -> None:
    task = GraphTask({"S": [GraphAction("to-g", "G")]})

    plan = astar_search(task, TableHeuristic())

    assert [action.name for action in plan] == ["to-g"]


# ---------------------------------------------------------------------------
# Additional coverage added when completing M2-02 (see docs/FARAZ_PROGRESS.md).
# ---------------------------------------------------------------------------

LLM_HEURISTICS = ROOT / "artifacts" / "upstream" / "deepseek-r1"


def graph_plan_cost(task: GraphTask, plan) -> float:
    """Replay a synthetic-graph plan edge by edge, independently of A*."""
    state = task.initial_state
    cost = 0.0
    for action in plan:
        assert action in task.edges.get(state, []), (state, action)
        state = action.target
        cost += action.cost
    assert task.goal_reached(state)
    return cost


def load_llm_heuristic(filename: str):
    path = LLM_HEURISTICS / filename
    spec = importlib.util.spec_from_file_location(f"test_llm_{path.stem}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    classes = [
        getattr(module, name)
        for name in dir(module)
        if name.endswith("Heuristic") and name != "Heuristic"
    ]
    assert len(classes) == 1
    return classes[0]


def test_zero_heuristic_matches_independent_dijkstra_on_random_graphs() -> None:
    """A* + zero heuristic is uniform-cost search: same optimal cost as an
    independent Dijkstra on 200 seeded random weighted digraphs (including
    unsolvable ones and zero-cost edges)."""
    rng = random.Random(5102)
    solvable = unsolvable = 0
    for graph_index in range(200):
        nodes = ["S", "G", *[f"N{i}" for i in range(rng.randint(2, 10))]]
        edges: dict[str, list[GraphAction]] = {}
        for source in nodes:
            for target in nodes:
                if source != target and rng.random() < 0.3:
                    edges.setdefault(source, []).append(
                        GraphAction(
                            f"{source}-{target}", target, rng.choice([0, 1, 2, 3, 7])
                        )
                    )
        task = GraphTask(edges)
        reference_cost, _ = independent_uniform_cost(task)
        result = astar_search_result(task, ZeroHeuristic(task))

        if reference_cost is None:
            unsolvable += 1
            assert result.status == "unsolved", graph_index
            assert result.plan is None
        else:
            solvable += 1
            assert result.status == "solved", graph_index
            assert result.plan_cost == reference_cost, graph_index
            assert graph_plan_cost(task, result.plan) == result.plan_cost
            assert result.plan_length == len(result.plan)
    # Guard against a degenerate generator that never exercises one branch.
    assert solvable > 20 and unsolvable > 20


def test_stale_queue_entries_are_skipped_not_expanded() -> None:
    # S->A (5) is queued first; S->B->A (2) supersedes it. The old A entry with
    # g=5 is still in the heap and must be discarded when popped.
    task = GraphTask(
        {
            "S": [GraphAction("s-a", "A", 5), GraphAction("s-b", "B", 1)],
            "B": [GraphAction("b-a", "A", 1)],
            "A": [GraphAction("a-g", "G", 10)],
        }
    )

    result = astar_search_result(task, TableHeuristic())

    assert result.status == "solved"
    assert result.plan_cost == 12
    assert [action.name for action in result.plan] == ["s-b", "b-a", "a-g"]
    assert result.stale_nodes_skipped == 1
    # S, B, A expanded exactly once each; the stale A(g=5) is not expanded.
    assert result.nodes_expanded == 3
    assert result.nodes_reopened == 0


def test_cyclic_unsolvable_graph_terminates_after_exhausting_states() -> None:
    task = GraphTask(
        {
            "S": [GraphAction("s-a", "A")],
            "A": [GraphAction("a-b", "B"), GraphAction("a-s", "S")],
            "B": [GraphAction("b-s", "S"), GraphAction("b-a", "A")],
        }
    )

    result = astar_search_result(task, TableHeuristic())

    assert result.status == "unsolved"
    assert result.failure_detail is None
    assert result.nodes_expanded == 3
    assert result.nodes_generated == 6


def test_goal_initial_state_returns_empty_plan() -> None:
    result = astar_search_result(GraphTask({}, initial="G"), TableHeuristic())

    assert result.status == "solved"
    assert result.plan == []
    assert result.plan_length == 0
    assert result.plan_cost == 0
    assert result.nodes_expanded == 0


@pytest.mark.parametrize("invalid_value", [math.nan, -2.5, None])
def test_invalid_heuristic_value_during_search_is_explicit(invalid_value) -> None:
    task = GraphTask({"S": [GraphAction("s-a", "A")], "A": [GraphAction("a-g", "G")]})

    result = astar_search_result(task, TableHeuristic({"A": invalid_value}))

    assert result.status == "error"
    assert result.plan is None
    assert "InvalidHeuristicError" in result.failure_detail


def test_heuristic_exception_is_reported_not_swallowed() -> None:
    class BrokenHeuristic:
        def __call__(self, node):
            raise KeyError("missing fact")

    result = astar_search_result(GraphTask({}), BrokenHeuristic())

    assert result.status == "error"
    assert "KeyError" in result.failure_detail
    with pytest.raises(SearchError, match="KeyError"):
        astar_search(GraphTask({}), BrokenHeuristic())


def test_make_child_node_keeps_unit_cost_default() -> None:
    root = searchspace.make_root_node("S")
    assert searchspace.make_child_node(root, "op", "A").g == 1
    assert searchspace.make_child_node(root, "op", "A", 3).g == 3


def test_hmax_is_admissible_at_initial_state_on_small_tasks() -> None:
    for domain, problem in (
        ("blocksworld", "easy-p03.pddl"),
        ("miconic", "easy-p02.pddl"),
        ("transport", "easy-p01.pddl"),
    ):
        task = load_task(domain, problem)
        reference_cost, _ = independent_uniform_cost(task)
        root = searchspace.make_root_node(task.initial_state)
        assert hMaxHeuristic(task)(root) <= reference_cost


@pytest.mark.parametrize(
    ("domain", "problem"),
    [
        ("blocksworld", "easy-p03.pddl"),
        ("miconic", "easy-p02.pddl"),
        ("transport", "easy-p01.pddl"),
    ],
)
def test_original_gbfs_and_legacy_greedy_still_return_valid_plans(
    domain, problem
) -> None:
    """Regression: the paper's GBFS (search/gbfs.py) is untouched and the
    legacy greedy wrapper over the modified best-first core still works."""
    task = load_task(domain, problem)

    gbfs_plan = gbfs_early_goal_test(task, hFFHeuristic(task))
    greedy_plan = greedy_best_first_search(task, hFFHeuristic(task))

    for plan in (gbfs_plan, greedy_plan):
        assert plan is not None
        replay_plan(task, plan)


@pytest.mark.parametrize(
    ("domain", "problem", "heuristic_file"),
    [
        ("blocksworld", "easy-p03.pddl", "blocksworld9_10.py"),
        ("miconic", "easy-p02.pddl", "miconic11_10.py"),
        ("transport", "easy-p01.pddl", "transport7_10.py"),
    ],
)
def test_astar_accepts_archived_llm_heuristics(domain, problem, heuristic_file) -> None:
    """A* runs the frozen DeepSeek R1 heuristics unmodified. Their admissibility
    is unknown, so only validity and cost >= proven optimum are asserted."""
    task = load_task(domain, problem)
    heuristic = load_llm_heuristic(heuristic_file)(task)
    reference_cost, _ = independent_uniform_cost(task)

    result = astar_search_result(task, heuristic, time_limit_s=60)

    assert result.status == "solved", result.failure_detail
    assert replay_plan(task, result.plan) == result.plan_cost
    assert result.plan_cost >= reference_cost
