"""Correctness tests for Weighted A* (M2-03), IDA* (M2-04), and the shared
guarantees of all three cost-aware searches (M2-05).

Independent oracles used here never call the project searches:

* ``independent_uniform_cost`` (forward Dijkstra, from ``test_astar``);
* ``exact_costs_to_goal`` (backward Dijkstra on the reversed synthetic graph,
  giving h* for every node, used to build admissible heuristics);
* ``graph_plan_cost`` / ``replay_plan`` (edge-by-edge / STRIPS replay).
"""

from __future__ import annotations

import heapq
import importlib.util
import math
import random
import sys
import time
from pathlib import Path

import pytest

from test_astar import (
    BENCHMARKS,
    ROOT,
    GraphAction,
    GraphTask,
    TableHeuristic,
    independent_uniform_cost,
    load_task,
    replay_plan,
)

PYPERPLAN = ROOT / "src" / "pyperplan"
sys.path.insert(0, str(PYPERPLAN))
from heuristics.relaxation import hMaxHeuristic  # noqa: E402
from heuristics.zero import ZeroHeuristic  # noqa: E402
from search import searchspace  # noqa: E402
from search.a_star import (  # noqa: E402
    SearchError,
    astar_search_result,
    ordered_node_astar,
    ordered_node_weighted_astar,
    validate_weight,
    weighted_astar_search_result,
)
from search.ida_star import ida_star_search, ida_star_search_result  # noqa: E402

sys.path.remove(str(PYPERPLAN))

LLM_FILES = {
    "blocksworld": ROOT / "artifacts" / "upstream" / "deepseek-r1" / "blocksworld9_10.py",
    "miconic": ROOT / "artifacts" / "upstream" / "deepseek-r1" / "miconic11_10.py",
    "transport": ROOT / "artifacts" / "upstream" / "deepseek-r1" / "transport7_10.py",
}
WEIGHTS = (1.0, 1.5, 2.0)


# ---------------------------------------------------------------------------
# Independent helpers
# ---------------------------------------------------------------------------


def graph_plan_cost(task: GraphTask, plan) -> float:
    state = task.initial_state
    cost = 0.0
    for action in plan:
        assert action in task.edges.get(state, []), (state, action)
        state = action.target
        cost += action.cost
    assert task.goal_reached(state)
    return cost


def exact_costs_to_goal(task: GraphTask) -> dict[str, float]:
    """Backward Dijkstra from the goal: h*(n) for every node that reaches it."""
    reverse: dict[str, list[tuple[str, float]]] = {}
    for source, actions in task.edges.items():
        for action in actions:
            reverse.setdefault(action.target, []).append((source, action.cost))
    distance = {task.goal: 0.0}
    frontier = [(0.0, task.goal)]
    while frontier:
        cost, node = heapq.heappop(frontier)
        if cost != distance[node]:
            continue
        for predecessor, edge_cost in reverse.get(node, []):
            new_cost = cost + edge_cost
            if new_cost < distance.get(predecessor, math.inf):
                distance[predecessor] = new_cost
                heapq.heappush(frontier, (new_cost, predecessor))
    return distance


def random_graph(rng: random.Random, max_extra_nodes: int, costs) -> GraphTask:
    nodes = ["S", "G", *[f"N{i}" for i in range(rng.randint(1, max_extra_nodes))]]
    edges: dict[str, list[GraphAction]] = {}
    for source in nodes:
        for target in nodes:
            if source != target and rng.random() < 0.3:
                edges.setdefault(source, []).append(
                    GraphAction(f"{source}-{target}", target, rng.choice(costs))
                )
    return GraphTask(edges)


def admissible_scaled_heuristic(task: GraphTask, rng: random.Random) -> TableHeuristic:
    """h(n) = factor(n) * h*(n), factor in [0, 1]: admissible, usually
    inconsistent. Unreachable-to-goal nodes get +inf (truthful dead ends)."""
    h_star = exact_costs_to_goal(task)
    nodes = {task.initial_state, task.goal, *task.edges}
    for actions in task.edges.values():
        nodes.update(action.target for action in actions)
    return TableHeuristic(
        {
            node: (h_star[node] * rng.random() if node in h_star else math.inf)
            for node in nodes
        }
    )


def load_llm_class(domain: str):
    path = LLM_FILES[domain]
    spec = importlib.util.spec_from_file_location(f"t2_llm_{path.stem}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    (cls,) = [
        getattr(module, name)
        for name in dir(module)
        if name.endswith("Heuristic") and name != "Heuristic"
    ]
    return cls


def result_signature(result):
    return (
        result.status,
        None if result.plan is None else [action.name for action in result.plan],
        result.plan_cost,
        result.nodes_generated,
        result.nodes_expanded,
        result.nodes_reopened,
        result.stale_nodes_skipped,
        result.dead_ends_pruned,
    )


# Admissible but inconsistent: h(B)=6 <= h*(B)=6, h(A)=0, but the edge B->A
# (cost 1) violates consistency since h(B) > 1 + h(A). A is first reached via
# the expensive edge and expanded, then improved through B.
INCONSISTENT_ADMISSIBLE = GraphTask(
    {
        "S": [GraphAction("s-a", "A", 4), GraphAction("s-b", "B", 1)],
        "B": [GraphAction("b-a", "A", 1)],
        "A": [GraphAction("a-g", "G", 5)],
    }
)
INCONSISTENT_H = TableHeuristic({"S": 0, "A": 0, "B": 6, "G": 0})

# Inadmissible: h(A)=100 > h*(A)=1 hides the cheap route S-A-G (cost 2).
INADMISSIBLE = GraphTask(
    {
        "S": [GraphAction("s-g", "G", 10), GraphAction("s-a", "A", 1)],
        "A": [GraphAction("a-g", "G", 1)],
    }
)
INADMISSIBLE_H = TableHeuristic({"A": 100})


# ---------------------------------------------------------------------------
# M2-03 Weighted A*
# ---------------------------------------------------------------------------


def test_weighted_frontier_orders_by_g_plus_w_h() -> None:
    near = searchspace.SearchNode("near-goal", None, None, 4)  # g=4, h=1
    far = searchspace.SearchNode("far", None, None, 1)  # g=1, h=3
    # A*: f(far)=4 < f(near)=5.  WA* w=2: f(far)=7 > f(near)=6.
    astar = [ordered_node_astar(far, 3, 0), ordered_node_astar(near, 1, 1)]
    weighted = [
        ordered_node_weighted_astar(2.0)(far, 3, 0),
        ordered_node_weighted_astar(2.0)(near, 1, 1),
    ]
    heapq.heapify(astar)
    heapq.heapify(weighted)
    assert heapq.heappop(astar)[3].state == "far"
    assert heapq.heappop(weighted)[3].state == "near-goal"
    assert ordered_node_weighted_astar(2.0)(far, 3, 0)[0] == 7


@pytest.mark.parametrize("bad", [-1, -0.5, math.nan, math.inf, True, "2", None])
def test_invalid_weights_are_rejected(bad) -> None:
    with pytest.raises(ValueError):
        validate_weight(bad)
    with pytest.raises(ValueError):
        weighted_astar_search_result(GraphTask({}), TableHeuristic(), bad)


def test_weight_one_is_identical_to_astar_on_random_graphs() -> None:
    rng = random.Random(51021)
    for _ in range(150):
        task = random_graph(rng, 9, [0, 1, 2, 3, 7])
        heuristic = admissible_scaled_heuristic(task, rng)
        assert result_signature(
            weighted_astar_search_result(task, heuristic, 1.0)
        ) == result_signature(astar_search_result(task, heuristic))


def test_weighted_bound_holds_for_admissible_heuristics() -> None:
    """cost <= w * C* for admissible (inconsistent) h on random graphs."""
    rng = random.Random(51022)
    checked = 0
    for _ in range(200):
        task = random_graph(rng, 10, [1, 2, 3, 7])
        reference, _ = independent_uniform_cost(task)
        heuristic = admissible_scaled_heuristic(task, rng)
        for weight in WEIGHTS:
            result = weighted_astar_search_result(task, heuristic, weight)
            if reference is None:
                assert result.status == "unsolved"
                continue
            assert result.status == "solved"
            assert graph_plan_cost(task, result.plan) == result.plan_cost
            assert result.plan_cost <= weight * reference + 1e-9
            if weight == 1.0:
                assert result.plan_cost == reference
            checked += 1
    assert checked > 150


def test_weighted_astar_can_be_suboptimal_within_bound() -> None:
    task = GraphTask(
        {
            "S": [GraphAction("s-a", "A", 1), GraphAction("s-b", "B", 2)],
            "A": [GraphAction("a-g", "G", 4)],
            "B": [GraphAction("b-g", "G", 2)],
        }
    )
    heuristic = TableHeuristic({"A": 0, "B": 2})  # admissible: h*(A)=4, h*(B)=2

    optimal = weighted_astar_search_result(task, heuristic, 1.0)
    greedy = weighted_astar_search_result(task, heuristic, 2.0)

    assert optimal.plan_cost == 4
    assert greedy.status == "solved"
    assert greedy.plan_cost == 5  # suboptimal, but 5 <= 2 * 4
    assert graph_plan_cost(task, greedy.plan) == 5


def test_weighted_astar_reopens_states() -> None:
    result = weighted_astar_search_result(INCONSISTENT_ADMISSIBLE, INCONSISTENT_H, 1.0)
    assert result.plan_cost == 7
    assert result.nodes_reopened == 1


@pytest.mark.parametrize(
    ("domain", "problem"),
    [
        ("blocksworld", "easy-p03.pddl"),
        ("miconic", "easy-p02.pddl"),
        ("transport", "easy-p01.pddl"),
    ],
)
def test_weighted_astar_on_benchmark_tasks(domain, problem) -> None:
    task = load_task(domain, problem)
    reference, _ = independent_uniform_cost(task)
    llm_class = load_llm_class(domain)
    for weight in WEIGHTS:
        hmax_result = weighted_astar_search_result(
            task, hMaxHeuristic(task), weight, time_limit_s=60
        )
        llm_result = weighted_astar_search_result(
            task, llm_class(task), weight, time_limit_s=60
        )
        for result in (hmax_result, llm_result):
            assert result.status == "solved", result.failure_detail
            assert replay_plan(task, result.plan) == result.plan_cost
            assert result.plan_cost >= reference
        assert hmax_result.plan_cost <= weight * reference  # admissible hmax
    assert result_signature(
        weighted_astar_search_result(task, hMaxHeuristic(task), 1.0)
    ) == result_signature(astar_search_result(task, hMaxHeuristic(task)))


# ---------------------------------------------------------------------------
# M2-04 IDA*
# ---------------------------------------------------------------------------


def test_ida_star_threshold_sequence() -> None:
    task = GraphTask(
        {
            "S": [GraphAction("s-a", "A", 2), GraphAction("s-b", "B", 3)],
            "A": [GraphAction("a-g", "G", 3)],
            "B": [GraphAction("b-g", "G", 1)],
        }
    )

    result = ida_star_search_result(task, TableHeuristic())

    # bound 0 -> min exceeded f is 2 -> 3 -> 4 (goal via B at f=4).
    assert result.iteration_bounds == (0.0, 2.0, 3.0, 4.0)
    assert result.iterations == 4
    assert result.status == "solved"
    assert result.plan_cost == 4
    assert [action.name for action in result.plan] == ["s-b", "b-g"]
    assert result.nodes_reopened is None and result.stale_nodes_skipped is None


def test_ida_star_first_bound_is_initial_heuristic() -> None:
    task = GraphTask({"S": [GraphAction("s-g", "G", 5)]})
    result = ida_star_search_result(task, TableHeuristic({"S": 5}))
    assert result.iteration_bounds == (5.0,)
    assert result.plan_cost == 5


@pytest.mark.parametrize("heuristic_kind", ["zero", "admissible"])
def test_ida_star_matches_dijkstra_on_random_graphs(heuristic_kind) -> None:
    rng = random.Random(51023)
    solvable = unsolvable = 0
    for index in range(200):
        task = random_graph(rng, 6, [0, 1, 2, 3])
        reference, _ = independent_uniform_cost(task)
        heuristic = (
            ZeroHeuristic(task)
            if heuristic_kind == "zero"
            else admissible_scaled_heuristic(task, rng)
        )
        result = ida_star_search_result(task, heuristic, time_limit_s=10)
        assert result.status != "timeout", index
        if reference is None:
            unsolvable += 1
            assert result.status == "unsolved", index
        else:
            solvable += 1
            assert result.status == "solved", index
            assert result.plan_cost == reference, index
            assert graph_plan_cost(task, result.plan) == result.plan_cost
        if result.iteration_bounds:
            bounds = result.iteration_bounds
            assert all(a < b for a, b in zip(bounds, bounds[1:]))
    assert solvable > 20 and unsolvable > 10


def test_ida_star_detects_cycles_on_the_current_path() -> None:
    task = GraphTask(
        {
            "S": [GraphAction("s-a", "A")],
            "A": [GraphAction("a-s", "S"), GraphAction("a-b", "B")],
            "B": [GraphAction("b-a", "A"), GraphAction("b-g", "G")],
        }
    )
    result = ida_star_search_result(task, TableHeuristic())
    assert result.status == "solved"
    assert result.plan_cost == 3
    assert result.cycles_pruned > 0


def test_ida_star_unsolvable_cyclic_graph_terminates() -> None:
    task = GraphTask(
        {
            "S": [GraphAction("s-a", "A")],
            "A": [GraphAction("a-b", "B"), GraphAction("a-s", "S")],
            "B": [GraphAction("b-s", "S"), GraphAction("b-a", "A")],
        }
    )
    result = ida_star_search_result(task, TableHeuristic())
    assert result.status == "unsolved"
    assert "exhausted" in result.failure_detail
    assert result.plan is None


def test_ida_star_goal_at_root_and_dead_end_root() -> None:
    goal = ida_star_search_result(GraphTask({}, initial="G"), TableHeuristic())
    assert (goal.status, goal.plan, goal.plan_cost, goal.iterations) == (
        "solved",
        [],
        0.0,
        0,
    )
    dead = ida_star_search_result(
        GraphTask({"S": [GraphAction("s-g", "G")]}), TableHeuristic({"S": math.inf})
    )
    assert dead.status == "unsolved"
    assert dead.dead_ends_pruned == 1


def test_ida_star_prunes_infinite_heuristic_successors() -> None:
    task = GraphTask(
        {
            "S": [GraphAction("s-d", "D"), GraphAction("s-a", "A")],
            "A": [GraphAction("a-g", "G")],
        }
    )
    result = ida_star_search_result(task, TableHeuristic({"D": math.inf}))
    assert result.status == "solved"
    assert result.dead_ends_pruned >= 1


@pytest.mark.parametrize("bad", [math.nan, -1, -math.inf, "x", None, True])
def test_ida_star_invalid_heuristic_values_are_errors(bad) -> None:
    root_bad = ida_star_search_result(GraphTask({}), TableHeuristic({"S": bad}))
    mid_bad = ida_star_search_result(
        GraphTask({"S": [GraphAction("s-a", "A")], "A": [GraphAction("a-g", "G")]}),
        TableHeuristic({"A": bad}),
    )
    for result in (root_bad, mid_bad):
        assert result.status == "error"
        assert "InvalidHeuristicError" in result.failure_detail
    with pytest.raises(SearchError, match="InvalidHeuristicError"):
        ida_star_search(GraphTask({}), TableHeuristic({"S": bad}))


@pytest.mark.parametrize("search", ["astar", "ida_star"])
def test_negative_action_costs_are_rejected(search) -> None:
    task = GraphTask({"S": [GraphAction("s-g", "G", -1)]})
    run = astar_search_result if search == "astar" else ida_star_search_result
    result = run(task, TableHeuristic())
    assert result.status == "error"
    assert "InvalidActionCostError" in result.failure_detail


def test_ida_star_cooperative_timeout() -> None:
    class Slow:
        def __call__(self, node):
            time.sleep(0.01)
            return 0

    task = GraphTask({"S": [GraphAction("s-a", "A")], "A": [GraphAction("a-s", "S")]})
    result = ida_star_search_result(task, Slow(), time_limit_s=0.001)
    assert result.status == "timeout"


@pytest.mark.parametrize(
    ("domain", "problem", "heuristics"),
    [
        ("miconic", "easy-p02.pddl", ("zero", "hmax", "llm")),
        ("transport", "easy-p01.pddl", ("zero", "hmax", "llm")),
        ("blocksworld", "easy-p03.pddl", ("llm",)),
    ],
)
def test_ida_star_on_benchmark_tasks(domain, problem, heuristics) -> None:
    task = load_task(domain, problem)
    reference, _ = independent_uniform_cost(task)
    factories = {"zero": ZeroHeuristic, "hmax": hMaxHeuristic, "llm": load_llm_class(domain)}
    for name in heuristics:
        result = ida_star_search_result(task, factories[name](task), time_limit_s=60)
        assert result.status == "solved", (name, result.failure_detail)
        assert replay_plan(task, result.plan) == result.plan_cost
        if name in {"zero", "hmax"}:
            assert result.plan_cost == reference  # admissible: optimal
        else:
            assert result.plan_cost >= reference  # no optimality assumed


# ---------------------------------------------------------------------------
# M2-05 shared guarantees across A*, WA*(w=1), IDA*
# ---------------------------------------------------------------------------

OPTIMAL_SEARCHES = {
    "astar": lambda task, h: astar_search_result(task, h),
    "wastar_w1": lambda task, h: weighted_astar_search_result(task, h, 1.0),
    "ida_star": lambda task, h: ida_star_search_result(task, h, time_limit_s=10),
}


@pytest.mark.parametrize("name", sorted(OPTIMAL_SEARCHES))
def test_inconsistent_but_admissible_heuristic_still_optimal(name) -> None:
    h_star = exact_costs_to_goal(INCONSISTENT_ADMISSIBLE)
    for node, value in INCONSISTENT_H.values.items():
        assert value <= h_star[node]  # independently verified admissibility
    assert INCONSISTENT_H.values["B"] > 1 + INCONSISTENT_H.values["A"]  # inconsistent

    result = OPTIMAL_SEARCHES[name](INCONSISTENT_ADMISSIBLE, INCONSISTENT_H)

    assert result.status == "solved"
    assert result.plan_cost == h_star["S"] == 7
    assert graph_plan_cost(INCONSISTENT_ADMISSIBLE, result.plan) == 7


@pytest.mark.parametrize("name", sorted(OPTIMAL_SEARCHES))
def test_inadmissible_heuristic_gives_valid_but_suboptimal_plan(name) -> None:
    result = OPTIMAL_SEARCHES[name](INADMISSIBLE, INADMISSIBLE_H)
    assert result.status == "solved"
    assert graph_plan_cost(INADMISSIBLE, result.plan) == result.plan_cost
    assert result.plan_cost == 10  # optimum is 2; no guarantee without admissibility


@pytest.mark.parametrize("name", sorted(OPTIMAL_SEARCHES))
def test_searches_are_deterministic(name) -> None:
    task = load_task("transport", "easy-p01.pddl")
    first = OPTIMAL_SEARCHES[name](task, hMaxHeuristic(task))
    second = OPTIMAL_SEARCHES[name](task, hMaxHeuristic(task))
    assert result_signature(first) == result_signature(second)


def test_benchmarks_directory_is_the_frozen_one() -> None:
    assert (BENCHMARKS / "blocksworld" / "domain.pddl").is_file()
