# Faraz — search-algorithm workstream progress report

Living research report for the AICC5102 search-algorithm workstream (branch
`feature/faraz-search`). Every number below is copied from a file in this
repository or from a command that was actually run. Nothing here is a final
paper result unless it is explicitly tagged **[PAPER RESULT]**; at present
**no item qualifies**: everything below is a correctness test, a validation
run, a bounded pilot, or an exact-reference attempt, not the official
comparison matrix (which is blocked, §22).

Tags used: **[METHODOLOGY]** — a decision that affects how later experiments
must be run or interpreted; **[BLOCKER]** — something that prevents or
endangers later work until resolved; **[PAPER RESULT]** — a result intended for
the final report (none yet).

Report structure: **Part I (§1–§15)** documents M2-01/M2-02 as completed on
2026-11-04 and is preserved unchanged except for the status table (§2) and a
note on §15. **Part II (§16–§28)** documents M2-03 … M2-09.

Status as of 2026-11-04 (second session): **M2-01 … M2-06 complete within the
configured budget; M2-07 pilot done, official matrix BLOCKED; M2-08 and M2-09
tools complete and applied to pilot data.** M2-01/M2-02 were committed as
`6316856`; all M2-03 … M2-09 work is uncommitted on `feature/faraz-search`.

---

## 1. Project objective and Faraz's contribution

The project reproduces and extends Corrêa, Pereira, and Seipp, *Classical
Planning with LLM-Generated Heuristics* (NeurIPS 2025). The paper evaluates
LLM-generated Python heuristics with greedy best-first search (GBFS). GBFS
ignores path cost, so it says nothing about plan quality or optimality.

Faraz's workstream (see `docs/TEAM_RESPONSIBILITIES.md`) adds cost-aware search
so the team can ask how LLM heuristics behave when plan cost matters:

- A* (this milestone), Weighted A*, and IDA*;
- exact optimal-cost references (A* + admissible hmax, cross-checked with
  uniform-cost search, per `docs/EXPERIMENT_PROTOCOL.md`);
- search-algorithm comparisons on the frozen 90-task benchmark
  `aicc5102-90-v1`.

This milestone delivers the foundation: a documented understanding of the
inherited search code (M2-01) and a validated, instrumented A* (M2-02).

## 2. Task status (M2-01 … M2-09)

Task definitions M2-03 … M2-09 come from the second-session task brief
(2026-11-04); the first session had no written definitions for them.

| ID | Task | Status | Evidence |
|---|---|---|---|
| M2-01 | Inspect and document the Pyperplan search architecture | **Complete** | §3 |
| M2-02 | Implement/adapt A* with correctness tests and validation | **Complete** | §4–§11; `tests/test_astar.py` (33 tests) |
| M2-03 | Instrumented Weighted A* (w = 1.0, 1.5, 2.0) | **Complete** | §17; `weighted_astar_search_result`; validation batch 60 runs |
| M2-04 | Iterative Deepening A* | **Complete** | §18; `src/pyperplan/search/ida_star.py` |
| M2-05 | Comprehensive validation of A*, WA*, IDA* (+ easy-task reference cross-check) | **Complete** (cross-check limited by budget: 14/30 easy tasks matched, 0 mismatches) | §19; 150 tests pass; mutation checks |
| M2-06 | Exact optimal-cost references + h*(s) interface | **Complete within the 60 s / 4096 MiB budget**: 17/90 proven (easy 17/30, medium 0/30, hard skipped). h*(s) tool ready, not run (no state inventory) | §21; `results/raw/faraz_optimal_refs.csv` |
| M2-07 | Search comparison experiments | **Pilot complete (easy tier, 450 runs ×2 batches); official 90-task matrix BLOCKED** | §22 |
| M2-08 | Optimality-gap and trade-off analysis | **Tooling complete; applied to pilot data (figures R3–R5 stamped PILOT)** | §23 |
| M2-09 | Failure and guarantee audit | **Tooling complete; applied to pilot data; 0 guarantee violations** | §24 |

The "pending" table that stood here after M2-02 is superseded by this one.

## 3. Original Pyperplan search architecture (M2-01)

All paths are relative to `src/pyperplan/`. The planner runs as a script
(`pyperplan.py`) with this directory on `sys.path`, so modules import each
other as top-level packages (`from search import searchspace`, `from task
import Task`).

### 3.1 Entry points and API

- **CLI:** `pyperplan.py:main()` parses `-s/--search` and `-H/--heuristic`.
  `SEARCHES` (`pyperplan.py:37`) maps CLI names to callables:
  `astar`, `wastar`, `gbf` (all in `search/a_star.py`),
  `gbfs_early_goal_test` (`search/gbfs.py`, **the paper's GBFS**),
  `gbfs_early_goal_test_int` (`search/gbfs_int.py`), `bfs`, `ehs`, `ids`, `sat`.
- **Pipeline:** `search_plan()` → `_parse()` (PDDL `Parser`) → `_ground()`
  (`grounding.ground`) → construct `heuristic_class(task)` → `_search()` calls
  `search(task, heuristic)` (or `search(task)` for blind searches). The search
  returns a list of operators or `None`; the CLI writes `<problem>.soln`.
- **No search base class:** each algorithm is a plain function with the
  signature `(task, heuristic, ...)` (`search/instructions.txt`).

### 3.2 State, node, and successor representation

- **State:** a `frozenset` of ground fact strings such as `"(on a b)"`
  (`grounding.py:383`). It is hashable, so states are used directly as dict
  keys for duplicate detection.
- **Operator** (`task.py:6`): `applicable(state)` is `preconditions <= state`;
  `apply(state)` returns `(state - del_effects) | add_effects`. **Operators have
  no `cost` attribute:** Pyperplan is unit-cost.
- **Task** (`task.py:76`): `goal_reached(state)` is `goals <= state`;
  `get_successor_states(state)` scans **all** operators and returns `(op,
  new_state)` pairs (`task.py:106-112`). A tree-based
  `search/successor_generator.py:SuccessorGenerator` exists but nothing uses it.
- **SearchNode** (`search/searchspace.py`): `state`, `parent`, `action`, `g`.
  `extract_solution()` walks parent pointers back to the root. Before this
  milestone, `make_child_node` always set `g = parent.g + 1`.
- `search/gbfs.py` defines **its own** `SearchNode` **without** `g`, plus its own
  `make_root_node`/`make_child_node`. The paper's GBFS therefore shares no node
  code with A*.

### 3.3 Inherited best-first core (`search/a_star.py`, before this milestone)

`astar_search(task, heuristic, make_open_entry, use_relaxed_plan)` was a single
generic best-first loop. A* / weighted A* / greedy best-first were selected by
passing a different `make_open_entry` that builds a heap tuple:

| Ordering function | Heap tuple |
|---|---|
| `ordered_node_astar` | `(g + h, h, tiebreaker, node)` |
| `ordered_node_weighted_astar(w)` | `(g + w*h, h, tiebreaker, node)` |
| `ordered_node_greedy_best_first` | `(h, h, tiebreaker, node)` |

- **Frontier:** a `heapq` min-heap. Ties on f are broken by lower h, then by an
  increasing insertion counter (FIFO).
- **Duplicates:** a `state_cost` dict holds the best g per state. A successor is
  pushed only if its g is strictly better. A popped entry is expanded only if
  `state_cost[state] == node.g`, which is the lazy-deletion pattern for stale
  heap entries. Reopening was implicit: a better g re-pushed the state even
  after expansion.
- **Goal test:** on pop (late goal test). This is correct for A*.
- **Heuristic:** evaluated for **every** generated successor, before the
  duplicate check. `h == inf` successors were dropped.
- **Gaps for this project:** no generated-node count; a popped goal was counted
  as an expansion; no plan cost; no status other than plan/`None`; no
  timeout; NaN or negative h silently accepted; successor order depended on
  operator list order; hard-coded unit costs.

### 3.4 The paper's GBFS (`search/gbfs.py:gbfs_early_goal_test`)

Heap keyed `(h, tiebreaker, node)`; a closed set of expanded states; **early goal
test** on generation; `h == inf` successors pruned; no g-values. This is the
configured reproduction algorithm (`gbfs_implementation =
"upstream:gbfs_early_goal_test"`). **This milestone does not modify
`search/gbfs.py`** (`git diff` is empty for it).

### 3.5 Heuristic interface

- Base class `heuristics/heuristic_base.py:Heuristic`. A heuristic is
  constructed as `HeuristicClass(task)` and called as `h(node) -> number`. By
  convention, `float("inf")` signals a dead end.
- Built-ins are auto-registered by `pyperplan.py:get_heuristics()`: every class
  in `heuristics/*.py` whose name ends in `Heuristic` becomes a CLI name (class
  name minus `Heuristic`, lowercased). This is how the new `ZeroHeuristic`
  automatically becomes `-H zero`.
- **hmax** (`heuristics/relaxation.py:hMaxHeuristic`): a
  `_RelaxationHeuristic` with `eval = max`. It propagates relaxed fact costs and
  returns the maximum goal-fact cost, or `inf` if the relaxed goal is
  unreachable. hmax is admissible (and consistent) under unit action costs.
  That is why the protocol uses it for exact references.
- **LLM heuristics** (e.g. `artifacts/upstream/deepseek-r1/blocksworld9_10.py`):
  ordinary `Heuristic` subclasses that read `task.goals` in `__init__` and parse
  `node.state` fact strings in `__call__`. The CLI loads them with `-H
  path/to/file.py` (first `*Heuristic` class in the file). They only use
  `node.state`, so they work with both node classes. Their admissibility is
  **unknown**.

### 3.6 Timeouts, memory limits, and experiment integration

- Pyperplan enforces **no** time or memory limit. `search_plan()` only logs
  `time.process_time()` for search and total time.
- `configs/experiment.v2.toml` `[resources]`/`[monitoring]` specifies 60 s and
  4096 MiB over the **process tree**, monotonic clock, and 0.1 s sampling. These
  must be enforced **externally** by the shared runner (Amina's scope, not yet
  implemented).
- Integration contract for new algorithms: an algorithm is referenced in
  `[algorithms]` (`astar_implementation = "project:search.a_star.astar_search"`)
  and emits records that satisfy `configs/result.schema.json`
  (statuses/fields defined in `docs/EXPERIMENT_PROTOCOL.md`).

## 4. A* implementation (M2-02)

File: `src/pyperplan/search/a_star.py`. The original single function was split
into an instrumented core and a backward-compatible adapter:

- `astar_search_result(task, heuristic, make_open_entry=ordered_node_astar,
  use_relaxed_plan=False, time_limit_s=None) -> SearchResult`, the new project
  API (line 189).
- `astar_search(...)`, the legacy Pyperplan adapter returning a plan or `None`
  (line 332). It is still what `-s astar` and `configs/experiment.v2.toml`
  reference. It raises `SearchError` when the core reports `error`, so a
  heuristic bug can never be mistaken for "unsolvable".
- `weighted_astar_search` and `greedy_best_first_search` still delegate to the
  same core.

`SearchResult` (line 41) fields: `status` ∈ {`solved`, `unsolved`, `timeout`,
`error`}, `plan`, `plan_length`, `plan_cost`, `nodes_generated`,
`nodes_expanded`, `nodes_reopened`, `stale_nodes_skipped`, `dead_ends_pruned`,
`wall_time_s`, `failure_detail`.

### 4.1 Algorithm

A* orders the frontier by f(n) = g(n) + h(n): the cost so far plus the
estimated cost to go. Core loop (`astar_search_result`, lines 207-330):

```
best_g[s0] = 0; push (h(s0), h(s0), 0, root)           # inf h(s0) -> unsolved
while frontier:
    pop (f, h, tie, node)                               # line 271
    if node.g != best_g[node.state]: stale += 1; continue   # line 273
    if goal_reached(node.state): return solved           # line 277, goal test on pop
    expanded_g[state] = node.g; expanded += 1            # line 281
    for (op, s') in sorted(successors, key=op.name):     # line 289, deterministic
        child.g = node.g + cost(op); generated += 1
        if child.g >= best_g.get(s', inf): continue      # line 307, duplicate / not better
        h' = validated h(child)                          # only for improving paths
        if h' == inf: dead_ends += 1; continue           # line 311
        if s' in expanded_g: reopened += 1               # line 316, reopening
        best_g[s'] = child.g; push (child.g + h', h', ++tie, child)
return unsolved
```

Why this is correct (the argument to give in a presentation):

1. **Priority and tie-breaking.** The heap tuple `(g+h, h, counter, node)` pops
   the minimum f. Among equal f it prefers lower h (closer to the goal), then
   earlier insertion. Successors are sorted by operator name before insertion,
   so the run is fully deterministic and independent of operator list order.
2. **Duplicate detection and stale entries.** `best_g` holds the cheapest known
   g per state. Python's `heapq` has no decrease-key, so a cheaper path pushes
   a *new* entry and leaves the old one in the heap. When an entry is popped
   whose g no longer equals `best_g[state]`, it is stale and is skipped
   (lazy deletion). Each state is expanded at most once per distinct improving
   g-value.
3. **Reopening.** If a strictly cheaper path reaches an already-expanded state,
   the state is pushed again and counted in `nodes_reopened`. With a consistent
   heuristic this never happens. With an inconsistent (e.g. LLM) heuristic, it
   is what keeps A* returning optimal plans when the heuristic is merely
   admissible.
4. **Goal test on pop.** When the goal is popped, every frontier entry has
   f ≥ its f. With an admissible h, no cheaper goal path remains, so the plan
   is optimal. Testing on generation (as GBFS does) would break this guarantee.
5. **Termination.** The state space is finite, and a state is re-pushed only
   when its g strictly decreases. With non-negative costs this happens finitely
   often, so the frontier eventually empties and the search returns
   `unsolved`.

### 4.2 Supporting changes

- `search/searchspace.py:make_child_node(parent, action, state,
  action_cost=1)`: an optional cost argument. The default keeps every existing
  caller on unit cost.
- `_action_cost(op)` reads `op.cost` if present, else 1. Non-numeric,
  non-finite, or negative costs raise `InvalidActionCostError` → status `error`.
  For grounded PDDL tasks this is always 1 (unit-cost model,
  `[optimality_reference].cost_model = "unit_action_cost"`).
- `_heuristic_value(heuristic, node)` (line 98): see §5.3.
- `heuristics/zero.py:ZeroHeuristic` returns 0 everywhere, so A* becomes
  uniform-cost search. The existing `BlindHeuristic` returns 1 for non-goal
  states, so it is **not** equivalent to UCS. That is why a separate zero
  heuristic was added.
- `configs/experiment.v2.toml`: `astar_implementation` changed from
  `pending:faraz` to `project:search.a_star.astar_search`.
  `configs/result.schema.json`: adds `nodes_generated` (required, nullable
  integer). `tests/test_config.py` asserts both. `docs/EXPERIMENT_PROTOCOL.md`
  defines generated vs expanded counting.

### 4.3 Node-count definitions **[METHODOLOGY]**

- `nodes_generated`: the root plus **every** applicable successor node
  constructed, including duplicates and dead ends.
- `nodes_expanded`: non-stale, **non-goal** nodes whose successors are
  enumerated. The popped goal is not counted. Upstream `astar_search` counted
  it, so A* expansion counts are one lower than upstream's for the same search.
  GBFS (`gbfs.py`) uses early goal testing and its own counter; the two counts
  must be compared with that difference in mind.

## 5. Implementation decisions and rationale

| Decision | Rationale |
|---|---|
| Adapt the inherited core instead of writing a new A* | The core already had the correct lazy-deletion structure. Minimal change preserves upstream `wastar`/`gbf` and keeps one implementation for A*/WA* (w=1.0 equivalence check comes for free). |
| Structured `SearchResult` + legacy adapter | The runner needs statuses and counters. The CLI and config keep the plan-or-`None` contract. |
| Goal test on pop | Required for A* optimality (see §4.1). |
| Compute h only for strictly improving successors | Equivalent search behaviour with fewer heuristic calls. A pruned duplicate never needed its h. |
| Sort successors by operator name | Determinism and reproducibility across machines and operator orderings. Costs a sort per expansion. |
| Do **not** modify `search/gbfs.py` | Paper reproduction must stay byte-identical (`gbfs_implementation = "upstream:gbfs_early_goal_test"`). |
| `time.perf_counter` for timing and the cooperative deadline | Monotonic, as the protocol requires, with 100 ns resolution. `time.monotonic` on Windows is `GetTickCount64` with 15.625 ms resolution (measured; §10). |
| Cooperative `time_limit_s` only | Hard process-tree limits belong to the shared runner, so no duplicate runner was built. |

### 5.3 Invalid and non-finite heuristic values **[METHODOLOGY]**

`_heuristic_value` never silently changes a heuristic's output:

| Heuristic returns | Handling |
|---|---|
| finite number ≥ 0 (int/float/numpy scalar) | used as `float(value)` |
| `+inf` | Pyperplan's dead-end signal: node pruned, counted in `dead_ends_pruned`. If at the root: status `unsolved` with `failure_detail` |
| `NaN`, `-inf`, negative, `bool`, non-numeric (`None`, str) | `InvalidHeuristicError` → status `error`; legacy adapter raises `SearchError` |
| heuristic raises any exception | caught → status `error` with exception type and message in `failure_detail` |

Rejecting negative values is a deliberate choice: a negative estimate is
meaningless as a cost-to-go, and silently clamping it to 0 would alter LLM
heuristic outputs. Consequence: an LLM heuristic that returns negatives fails
loudly under A*/WA*/`gbf`, while `gbfs_early_goal_test` (untouched) still
accepts it. Ranem/Amina should know this when comparing coverage.

### 5.4 Optimality guarantee **[METHODOLOGY]**

A* returns a cost-optimal plan **only if h is admissible** (never
overestimates h*). This holds for `zero` and `hmax` under unit costs. It does
**not** hold, in general, for LLM-generated heuristics. With an inadmissible h,
A* still returns a *valid* plan, but its cost may exceed the optimum. In
results, the field `astar_optimality_guaranteed` is `true` only for
`heuristic_admissibility = admissible`. An LLM run that happens to match the
reference cost does **not** show that the heuristic is admissible.

## 6. Experimental setup and reproducibility

- **Script:** `experiments/search_algorithms/run_astar_validation.py`. This is a
  validation utility, **not** the shared runner.
- **Tasks** (from the frozen manifest `benchmarks/manifest.json`, version
  `aicc5102-90-v1`): Blocksworld `easy-p03` and `easy-p04`, Miconic
  `easy-p02`, Transport `easy-p01`.
- **Heuristics:** `zero`, `hmax`, and `llm:deepseek-r1`, the archived upstream
  selected DeepSeek R1 heuristic for each domain (`blocksworld9_10.py`
  `106d55bf…`, `miconic11_10.py` `10c099e5…`, `transport7_10.py` `36b883d5…`;
  full SHA-256 in the CSV). These are the paper's baselines, not the project's
  new trials.
- **Independent reference:** `independent_uniform_cost()` in the same script,
  a Dijkstra that shares no code with `a_star.py` (stores full plans instead of
  parent pointers, never calls a heuristic). Its plan is replayed. If valid, its
  cost is `proven` optimal. An admissible-heuristic run whose cost disagrees
  is recorded as `cross_check_mismatch` with the reference cost withheld (per
  the protocol).
- **Plan validation:** every returned plan is replayed from the initial state,
  checking applicability at each step and goal satisfaction at the end
  (`replay_plan`).
- **Limits:** 60 s cooperative in-process time limit (from
  `[resources].time_limit_s`). The 4096 MiB memory cap is **not enforced**
  (`memory_limit_enforced = False` in every row).
- **Timing:** `search_wall_time_s` covers search only (excludes parsing,
  grounding, and heuristic construction). Single run, no repetitions.
- **Provenance recorded per row:** `git_commit` `eb8f95ea81a399d8633bf899e6db8b14d83fca8d`,
  `git_worktree_dirty = True` (work is uncommitted, so the commit alone is
  insufficient), `astar_source_sha256`
  `241be7ab62ee9f3c0bcb36d9b28f343c80560e827d9f2e7b6d7b7e7da03475ac` (matches the
  current `src/pyperplan/search/a_star.py`), `config_id` `pre-experiment-v2`,
  problem SHA-256, seed 5102, `machine_id` `machine-f922a64c5235`.
- **Machine** (`results/raw/faraz_astar_validation.machine.json`): Windows 11,
  AMD64, Intel64 Family 6 Model 198, 24 logical CPUs, 130,492 MiB RAM, Python
  3.12.12. Run timestamp 2026-11-04T08:28:10Z.
- **Benchmark integrity:** `tools/verify_benchmarks.py` reports "90 files, 3
  domains, 10 per difficulty/domain, hashes intact". `git status` shows no
  changes under `benchmarks/`.

## 7. Automated correctness tests and outcomes

Test file: `tests/test_astar.py`. Command: `uv run --frozen pytest -q`.
**Result (2026-11-04): 77 passed (whole suite), of which 33 are A* tests.**
Before this milestone was completed, the suite had 61 tests (17 of them A*,
written by Codex). All passed, but the validation script had never run (§10).

Independent references used: `independent_uniform_cost()` (separate Dijkstra
in the test file), `replay_plan()` (applicability/goal replay), and
`graph_plan_cost()` (edge-by-edge replay on synthetic graphs). No test uses A*
as its own reference.

| # | Requirement | Test(s) | Outcome |
|---|---|---|---|
| 1 | Zero h behaves like UCS | `test_zero_heuristic_matches_independent_dijkstra_on_random_graphs` (200 seeded random weighted digraphs, incl. zero-cost edges and unsolvable graphs); `test_zero_and_hmax_match_independent_uniform_cost` | pass |
| 2 | hmax optimal on small tasks | `test_zero_and_hmax_match_independent_uniform_cost` (BW easy-p03, Miconic easy-p02, Transport easy-p01); `test_hmax_is_admissible_at_initial_state_on_small_tasks` | pass |
| 3–5 | Plans replay, reach goal, cost correct | `replay_plan` in the PDDL tests; `test_path_cost_accounting_uses_operator_costs`; `graph_plan_cost` in the random-graph test | pass |
| 6 | Duplicate states | `test_duplicate_states_are_not_reexpanded` | pass |
| 7 | Reopening on better g | `test_better_path_reopens_an_expanded_state` (`nodes_reopened == 1`, optimal plan) | pass |
| 8 | Priority-queue ordering and ties | `test_priority_ordering_and_stable_tie_breaking`; `test_equal_priority_successors_use_deterministic_operator_order` | pass |
| 9 | Stale entries ignored | `test_stale_queue_entries_are_skipped_not_expanded` (`stale_nodes_skipped == 1`, `nodes_expanded == 3`) | pass |
| 10 | Unsolvable tasks terminate | `test_unsolvable_task_terminates_cleanly`; `test_cyclic_unsolvable_graph_terminates_after_exhausting_states`; `test_positive_infinity_is_counted_as_a_dead_end` | pass |
| 11 | Invalid / non-finite h explicit | `test_invalid_heuristic_values_are_explicit_errors` (root: NaN, −inf, −1, str, bool); `test_invalid_heuristic_value_during_search_is_explicit` (mid-search: NaN, −2.5, None); `test_heuristic_exception_is_reported_not_swallowed` | pass |
| 12 | GBFS unaffected | `test_original_gbfs_and_legacy_greedy_still_return_valid_plans` (3 domains, hFF); existing `tests/test_planner_smoke.py` (6 CLI runs of `gbfs_early_goal_test` with hFF and DeepSeek R1, plans validated) | pass |
| — | Archived LLM heuristics accepted | `test_astar_accepts_archived_llm_heuristics` (3 domains; valid plan, cost ≥ proven optimum) | pass |
| — | Edge cases | `test_goal_initial_state_returns_empty_plan`; `test_cooperative_timeout_has_explicit_status`; `test_make_child_node_keeps_unit_cost_default`; `test_legacy_astar_adapter_still_returns_a_plan` | pass |

**Mutation check (sensitivity of the tests).** On a scratch copy outside the
repository, three deliberate bugs were injected into `a_star.py` one at a time
and `tests/test_astar.py` was rerun:

| Injected bug | Tests failing |
|---|---|
| Never skip stale entries | 1 (`test_stale_queue_entries_are_skipped_not_expanded`) |
| Never reopen expanded states | 1 (`test_better_path_reopens_an_expanded_state`) |
| Ignore action costs (unit g) | 4 (incl. the random-graph Dijkstra test) |

## 8. Numerical validation results

Source: [`results/raw/faraz_astar_validation.csv`](../results/raw/faraz_astar_validation.csv)
(12 rows, 49 columns). Validation smoke test only, **not** paper results. All
12 rows: `status = success`, `plan_valid = True`, `reference_status = solved`,
`reference_plan_valid = True`, `optimal_cost_status = proven`,
`nodes_reopened = 0`, `dead_ends_pruned = 0`, no timeouts or errors. Script exit
code 0 ("validation rows: 12; failures: 0").

### 8.1 A* results

| Domain | Problem | Heuristic | Status | Plan length | Plan cost | Proven optimum | Matches | Generated | Expanded | Stale skipped | Search time (s) |
|---|---|---|---|---:|---:|---:|---|---:|---:|---:|---:|
| blocksworld | easy-p03 | zero | success | 20 | 20.0 | 20.0 | yes | 18509 | 7013 | 0 | 0.057792700 |
| blocksworld | easy-p03 | hmax | success | 20 | 20.0 | 20.0 | yes | 8660 | 2600 | 0 | 0.286272900 |
| blocksworld | easy-p03 | llm:deepseek-r1 | success | 20 | 20.0 | 20.0 | yes | 108 | 26 | 0 | 0.000560200 |
| blocksworld | easy-p04 | zero | success | 24 | 24.0 | 24.0 | yes | 186329 | 65740 | 0 | 0.705357900 |
| blocksworld | easy-p04 | hmax | success | 24 | 24.0 | 24.0 | yes | 95063 | 27227 | 0 | 3.821158600 |
| blocksworld | easy-p04 | llm:deepseek-r1 | success | 24 | 24.0 | 24.0 | yes | 417 | 84 | 1 | 0.002198200 |
| miconic | easy-p02 | zero | success | 4 | 4.0 | 4.0 | yes | 27 | 8 | 0 | 0.000052200 |
| miconic | easy-p02 | hmax | success | 4 | 4.0 | 4.0 | yes | 15 | 4 | 0 | 0.000091100 |
| miconic | easy-p02 | llm:deepseek-r1 | success | 4 | 4.0 | 4.0 | yes | 15 | 4 | 0 | 0.000037800 |
| transport | easy-p01 | zero | success | 3 | 3.0 | 3.0 | yes | 350 | 53 | 0 | 0.000619800 |
| transport | easy-p01 | hmax | success | 3 | 3.0 | 3.0 | yes | 37 | 6 | 0 | 0.000777700 |
| transport | easy-p01 | llm:deepseek-r1 | success | 3 | 3.0 | 3.0 | yes | 18 | 3 | 0 | 0.000095000 |

### 8.2 Independent uniform-cost reference

| Domain | Problem | Reference cost | Reference expansions | Reference time (s) | A*+zero expansions |
|---|---|---:|---:|---:|---:|
| blocksworld | easy-p03 | 20.0 | 7013 | 0.045897700 | 7013 |
| blocksworld | easy-p04 | 24.0 | 65740 | 0.592008200 | 65740 |
| miconic | easy-p02 | 4.0 | 8 | 0.000025000 | 8 |
| transport | easy-p01 | 3.0 | 53 | 0.000420200 | 53 |

## 9. Interpretation of observed results

These are four easy tasks with single timing runs. They validate correctness;
they are not evidence about general performance.

1. **A*+zero is exactly uniform-cost search.** Its expansion counts equal the
   independent Dijkstra's on all four tasks (7013, 65740, 8, 53). Both sort
   successors by operator name and break ties FIFO, so this is an exact,
   node-for-node agreement, not merely an equal final cost.
2. **hmax is correct and prunes, but is expensive per node.** Same optimal costs
   as the reference. Expansions fall from 7013 to 2600 (−62.9%) on
   Blocksworld easy-p03 and from 65740 to 27227 (−58.6%) on easy-p04. Search
   time nevertheless rises ×4.95 (0.0578 → 0.2863 s) and ×5.42 (0.7054 →
   3.8212 s), because hmax recomputes a relaxed fixpoint at every evaluated
   node. **[METHODOLOGY]** Exact references with A*+hmax will be bounded by
   per-node cost on the medium/hard tasks. Expect timeouts and record them as
   `unknown_timeout` rather than guessing costs.
3. **The DeepSeek R1 heuristics are far more informed here and happened to
   return optimal plans.** Expansions are 26 vs 2600 (BW p03) and 84 vs 27227
   (BW p04). Costs equal the proven optimum on all four tasks. This does
   **not** show admissibility: four easy tasks cannot reveal overestimation
   elsewhere, and A* gives no optimality guarantee for these heuristics.
   Quantifying overestimation is Ranem's scope.
4. **No reopening occurred** in any run. For zero and hmax this is expected
   (both consistent under unit costs). For the LLM heuristic it is merely
   unobserved. The single stale skip (LLM, BW p04) means a *frontier* state
   received a cheaper path before being expanded. That can happen even with a
   consistent heuristic, so it is not a sign of inconsistency.

## 10. Problems encountered and fixes

Chronological log for 2026-11-04 (continuation of Codex's unfinished work):

| # | Problem found | Fix |
|---|---|---|
| 1 | Codex's `run_astar_validation.py` had **never run successfully**: `from tools.capture_machine_profile import …` failed with `'tools' is not a package`, because `src/pyperplan/tools.py` shadows the repository's `tools/` package once Pyperplan's directory is on `sys.path`. No result CSV existed. | Load `tools/capture_machine_profile.py` by file path via `importlib`. Only `src/pyperplan` is put on `sys.path`. |
| 2 | Wall times were quantised to 0.000 / 0.0156 / 0.0625 s. Measured: `time.monotonic` on Windows = `GetTickCount64`, resolution 0.015625 s; `time.perf_counter` = `QueryPerformanceCounter`, 1e-07 s. | Switched `a_star.py` and the validation script to `time.perf_counter` (still monotonic). |
| 3 | The validation status logic would label any cost mismatch `reference_error`, and tied `optimal_cost_status` to the A* outcome. This was wrong for inadmissible LLM heuristics, and conflated reference status with run status (contrary to the protocol). | Main `status` now reflects only search outcome + plan validity. `optimal_cost_status` describes the reference. `cross_check_mismatch` is raised only for admissible heuristics. Added `cost_matches_reference`, `cost_ratio_to_reference`, `heuristic_admissibility`, `astar_optimality_guaranteed`. |
| 4 | Results were traceable only to `HEAD`, but the code is uncommitted. | Added `git_worktree_dirty`, `astar_source_sha256`, `sha256_problem`, `heuristic_file`, and `heuristic_file_sha256` columns. |
| 5 | Missing tests: stale entries, UCS equivalence on many graphs, cyclic unsolvable, mid-search invalid h, heuristic exceptions, GBFS regression, LLM heuristics, goal-at-root. | Added 16 tests (§7) and a mutation check. |
| 6 | Archived LLM heuristics were untested under A*. | Added to the validation matrix and tests, loaded unmodified exactly as the CLI loads them. |

## 11. Limitations and theoretical guarantees

- **Guarantee:** with non-negative action costs and an admissible heuristic,
  `astar_search_result` returns an optimal plan or proves unsolvability
  (exhausted frontier). With an inadmissible heuristic it returns a valid but
  possibly suboptimal plan. Plans are validated in all cases.
- Unit-cost model only in practice (Pyperplan operators have no costs). The
  cost plumbing is tested on synthetic graphs.
- `+inf` dead-end pruning is sound only if the heuristic's `inf` is truthful.
  hmax's is; an LLM heuristic could prune a solvable state. That would surface
  as `unsolved`, which must be interpreted carefully.
- **[BLOCKER] for experiments, not for M2-02:** no hard time or memory
  enforcement. The cooperative deadline is checked between expansions and
  successors. A single slow heuristic call can overrun it, and memory is
  unbounded. The shared runner must enforce process-tree limits.
- Duplicate detection holds every reached state in memory (`best_g`,
  `expanded_g`). Hard tasks may hit the 4096 MiB cap; that is the motivation
  for IDA*.
- Validation covers 4 of the 30 easy tasks. The protocol requires the UCS
  cross-check on all 10 easy tasks per domain before accepting the reference
  implementation.
- Timings are single runs on one Windows machine and exclude grounding.
- Behaviour change for legacy `-s astar/wastar/gbf`: deterministic
  name-sorted successor order, the goal pop is no longer counted as an
  expansion, and invalid heuristic values now raise `SearchError`.
  `gbfs_early_goal_test` is unchanged.

## 12. Files created or modified (uncommitted)

| File | Change | By |
|---|---|---|
| `src/pyperplan/search/a_star.py` | Instrumented core `astar_search_result`, `SearchResult`, validation of h/costs, reopening/stale counters, deterministic successor order, legacy adapter. `perf_counter` timing. | Codex; timing fix by Claude |
| `src/pyperplan/search/searchspace.py` | `make_child_node(..., action_cost=1)` | Codex |
| `src/pyperplan/search/__init__.py` | Export `SearchResult`, `astar_search_result` | Codex |
| `src/pyperplan/heuristics/zero.py` (new) | `ZeroHeuristic` (`-H zero`) | Codex |
| `tests/test_astar.py` (new) | 17 tests by Codex + 16 added | Codex + Claude |
| `experiments/search_algorithms/run_astar_validation.py` (new) | Validation utility. Import fix, LLM heuristic rows, status/provenance redesign, `perf_counter` | Codex + Claude |
| `experiments/search_algorithms/README.md` | Validation command and description | Codex + Claude |
| `configs/experiment.v2.toml` | `astar_implementation = "project:search.a_star.astar_search"` | Codex |
| `configs/result.schema.json` | New required field `nodes_generated` | Codex |
| `tests/test_config.py` | Asserts the two config/schema changes | Codex |
| `docs/EXPERIMENT_PROTOCOL.md` | Generated/expanded counting definition | Codex |
| `docs/FARAZ_PROGRESS.md` (new) | This report | Claude |
| `results/raw/faraz_astar_validation.csv`, `.machine.json` (new, git-ignored) | Raw validation output | generated |

Not modified: `search/gbfs.py`, `benchmarks/`, `artifacts/`, `pyperplan.py`,
the other members' `experiments/` directories.

## 13. Commands to reproduce

```bash
uv sync --frozen --group dev
uv run --frozen python tools/verify_benchmarks.py
uv run --frozen pytest -q                          # whole suite (77 tests)
uv run --frozen pytest -q tests/test_astar.py      # A* only (33 tests)
# Validation matrix (refuses to overwrite; add --force to regenerate):
uv run --frozen python experiments/search_algorithms/run_astar_validation.py
# CLI A* (writes <problem>.soln next to the problem; copy the PDDL to a scratch dir first):
uv run --frozen python src/pyperplan/pyperplan.py -s astar -H hmax <dir>/domain.pddl <dir>/easy-p03.pddl
uv run --frozen python tools/validate_plan.py <dir>/domain.pddl <dir>/easy-p03.pddl <dir>/easy-p03.pddl.soln
```

The CLI commands above were run on 2026-11-04 with Blocksworld easy-p03. Both
`-H hmax` (8660 generated, 2600 expanded) and `-H zero` (18509 / 7013) gave
plan length 20 and "valid plan: goal reached after 20 steps". These counts
match the CSV.

## 14. Dependencies and handoffs

**To Amina (shared runner):**

- Call `search.a_star.astar_search_result(task, heuristic, time_limit_s=...)`
  and map `SearchResult.status`: `solved` + valid replay → `success`; `solved`
  + failed replay → `invalid_plan`; `unsolved` → `unsolved`; `timeout` →
  `timeout`; `error` → `planner_error` (`failure_detail` carries the reason).
- The runner must provide hard process-tree time/memory enforcement. The
  cooperative limit is only a fallback.
- **[BLOCKER] (review):** `configs/result.schema.json` now *requires*
  `nodes_generated`. This is a shared-schema change that needs
  cross-workstream review (`docs/EXPERIMENT_PROTOCOL.md`). GBFS records will
  need either an instrumented count or `null`.
- **[BLOCKER] (traceability):** `.gitignore` excludes `results/raw/**`, so the
  validation CSV is not version-controlled. The protocol also places raw
  records at `results/raw/<config_id>/<run_id>.json`, whereas this validation
  CSV lives at the path requested for this milestone. The team should agree
  how validation artifacts are archived. Until then, §8 of this report is the
  tracked copy of the numbers.

**To Ranem (heuristic reliability):**

- A*+hmax / UCS provide proven h*(s₀) on tasks they can solve. The
  `reference_cost` column is the ground truth for overestimation analysis. LLM
  heuristics must be judged against it; matching costs on these four tasks
  say nothing about admissibility.
- A* rejects negative/NaN heuristic outputs as errors and does not clamp them.
  Report such failures rather than repairing outputs.

## 15. Remaining work and next steps (as of M2-02; superseded by §28)

*Historical note: items 1–4 below were completed in the second session
(M2-03 … M2-06, §17–§21); item 5 is the blocked M2-07 matrix (§22).*

Completed in this milestone: M2-01 and M2-02. Planned, not done:

1. **Next task:** extend the UCS cross-check to all 30 easy tasks (10 per
   domain), as the protocol requires before A*+hmax is accepted as the
   exact-reference procedure. The validation script only needs a larger
   `VALIDATION_CASES` tuple. Run it with the shared runner's limits once
   available.
2. Weighted A* (weights 1.0/1.5/2.0): `weighted_astar_search` already uses
   the validated core. It needs an instrumented entry point and a w=1.0 ≡ A*
   equivalence test.
3. IDA* as a memory-bounded alternative (new implementation; upstream `ids` is
   not IDA*).
4. Exact references on the 90 tasks with explicit `unknown_*` statuses.
5. Search comparisons with the team's frozen heuristic trials, after Amina's
   runner and Ranem's trial freeze.
6. Get team review of the schema change and the results-archiving question
   (§14), then commit and open a PR from `feature/faraz-search`.

---

# Part II — M2-03 … M2-09

## 16. Chronological progress log (second session, 2026-11-04)

1. Re-read this report, the protocol, config, schema, search code and tests.
   `git status` was clean on top of `6316856` (M2-01/M2-02 committed). No
   shared runner exists on any local branch (`experiments/reproduction/` holds
   only a README); `jsonschema` and `psutil` are not installed.
2. **M2-03:** added `weighted_astar_search_result` on the unchanged A* core.
3. **M2-04:** added `src/pyperplan/search/ida_star.py`; `SearchResult` gained
   optional IDA* fields (backward compatible).
4. **M2-05:** 45 tests in `tests/test_search_algorithms.py`, all passing on
   the first run; then five deliberate mutations (§19.3), each caught.
5. Built the bounded-execution layer (§20). Verified the hard memory cap: a
   40 MiB job ended `memory_limit` at 41.0 MiB peak.
6. **M2-06:** staged reference generation `refs-20261104a` (120 bounded runs,
   1.54 h of process wall time, 4 parallel jobs): 17/90 proven (§21).
7. **M2-03/M2-04 validation batch** (60 runs) and **M2-07 easy pilot**
   (450 runs, 6 parallel jobs).
8. **Finding:** results of GBFS and hFF differ between processes. Root cause:
   Pyperplan grounding and hFF iterate over Python `set`s of strings, whose
   order depends on the per-process `PYTHONHASHSEED` (§22.4). Fixed for
   Faraz's runs by setting `PYTHONHASHSEED` to the protocol-derived run seed;
   the pilot was rerun seeded and the two batches compared.
9. M2-08/M2-09 analysis and audit applied to the seeded pilot; figures
   checked visually and relaid out twice to remove label collisions.

## 17. M2-03 — Weighted A*

**Objective.** An instrumented Weighted A* with f = g + w·h for w ∈ {1.0, 1.5,
2.0}, sharing A*'s validated machinery.

**Original code / what changed.** Upstream `weighted_astar_search(task, h,
weight=5)` already passed `ordered_node_weighted_astar(weight)` into the
generic core, but returned only a plan. Added in `src/pyperplan/search/a_star.py`:

- `validate_weight(weight)`: finite number ≥ 0, else `ValueError` (bool, NaN,
  ±inf, negative, strings rejected). w = 0 is uniform-cost search.
- `weighted_astar_search_result(task, heuristic, weight, use_relaxed_plan=False,
  time_limit_s=None) -> SearchResult`: validates w, then calls
  `astar_search_result(..., make_open_entry=ordered_node_weighted_astar(w))`.
- The legacy `weighted_astar_search` is unchanged (keeps the upstream default
  w = 5 for `-s wastar`); `configs/experiment.v2.toml` now points
  `weighted_astar_implementation` at it, and `tests/test_config.py` imports
  every configured implementation.

**Algorithm.** Identical to §4.1 except the heap key:

```
key(n) = (g(n) + w*h(n), h(n), insertion counter)
```

Duplicate detection, reopening, stale-entry skipping, goal test on pop, and
heuristic validation are inherited unchanged.

**Design decisions.**
- *Reuse, not re-implementation*: one core means WA*'s correctness rests on
  the already-tested A* code. Because `1.0*h == h` exactly in IEEE
  arithmetic, w = 1.0 yields bit-identical keys, so WA*(1) **is** A*,
  not an approximation. This is checked (below), not assumed.
- *Reopening kept*: with reopening and an admissible h, WA* returns a plan
  costing ≤ w·C*. **[METHODOLOGY]** This bound is claimed only for zero and hmax;
  for hFF or LLM heuristics there is no bound at all.

**Tests** (`tests/test_search_algorithms.py`, all pass): f-ordering differs from
A* in the intended direction; invalid weights rejected (7 cases); w = 1 equals
A* on 150 random graphs with admissible-but-inconsistent heuristics (status,
plan, cost, all counters); cost ≤ w·C* on 200 random graphs × 3 weights (vs
independent Dijkstra); a graph where w = 2 is provably suboptimal (5 vs 4,
within 2×4); reopening at w = 1; benchmark tasks with hmax and DeepSeek-R1 for
all weights (valid plans; hmax cost ≤ w·L*; WA*(1) ≡ A* on Blocksworld easy-p03).

**Validation experiment** (`results/raw/faraz_search_validation-wa-ida-20261104.csv`,
60 runs; 4 tasks × {A*, WA* 1.0/1.5/2.0, IDA*} × {zero, hmax, DeepSeek-R1};
60 s / 4096 MiB hard limits). 58 success, 2 timeout (both IDA*, §18).
**WA*(1.0) and A* agree on plan hash, cost, generated and expanded nodes in
12/12 pairs.** Selected rows (full table in the CSV):

| Task (L*) | Heuristic | A* exp. | WA* 1.5 exp. (cost) | WA* 2.0 exp. (cost) |
|---|---|---:|---:|---:|
| BW easy-p03 (20) | hmax | 2600 | 2233 (20) | 1514 (20) |
| BW easy-p04 (24) | hmax | 27227 | 21403 (24) | 14928 (24) |
| BW easy-p04 (24) | DeepSeek-R1 | 84 | 84 (24) | 76 (24) |
| BW easy-p03 (20) | zero | 7013 | 7013 (20) | 7013 (20) |

With zero h, w is irrelevant (w·0 = 0), and the counts confirm it. With hmax,
larger w expands fewer nodes and, on these four tasks, stays optimal.

## 18. M2-04 — IDA*

**Objective.** Iterative Deepening A* with f-thresholds, distinct from upstream
`ids` (uninformed iterative deepening on depth).

**New file** `src/pyperplan/search/ida_star.py`:
`ida_star_search_result(task, heuristic, time_limit_s=None) -> SearchResult`
and legacy-style `ida_star_search(task, heuristic)` (plan or `None`, raises
`SearchError` on error). Reuses `_heuristic_value`, `_action_cost`,
`SearchResult` from `a_star.py`. `SearchResult` gained optional fields
`iterations`, `iteration_bounds`, `cycles_pruned`; for IDA*
`nodes_reopened`/`stale_nodes_skipped` are `None` (not applicable) rather
than a misleading 0.

**Algorithm** (iterative, explicit stack, so long plans cannot hit Python's
recursion limit):

```
h0 = h(s0); if h0 == inf: unsolved; if goal(s0): return []
bound = h0
loop:
    record bound; next = inf
    DFS from s0 with frames [node, sorted successors, index]; on_path = {s0}
        expanding a frame: successors sorted by operator name; expanded += 1
        for each successor s' (generated += 1):
            if s' in on_path: cycles_pruned += 1; skip
            h' = validated h(child); if h' == inf: dead_end += 1; skip
            f' = g' + h'
            if f' > bound: next = min(next, f'); skip
            if goal(s'): return plan            # goal test inside the bound
            push frame; on_path.add(s')
        frame exhausted: pop; on_path.remove(state)
    if next == inf: unsolved ("search space exhausted")
    bound = next
```

**Why it is optimal with admissible h** (presentation argument): if an
iteration with bound B finds no goal, every path whose nodes all have f ≤ B
was explored. On an optimal path every node has f ≤ C* (admissibility), so if
C* ≤ B a goal would have been found; hence the next bound, the smallest
pruned f, is ≤ C*. A goal found in the iteration with bound B has cost
g = f ≤ B ≤ C* (h(goal) = 0), so it is optimal. Bounds strictly increase, so
with a finite state space the cycle-free search terminates.

**Design decisions.**
- *Path-only cycle detection, no transposition table*: this is the textbook
  memory profile, O(depth · branching) for the stack and successor lists.
  **[METHODOLOGY]** It also means IDA* re-expands states reached by different
  paths, within and across iterations. The low memory is real (seeded pilot:
  max peak 21.9 MiB for IDA* vs 628.2 MiB for A* over all runs), but it does
  not make IDA* fast.
- *Memory guarantee stated honestly*: peak process memory still includes the
  grounded task and heuristic tables; only the search frontier is small.
- *Goal test on generation* inside the bound (standard IDA*), root tested
  before the first iteration.

**Tests** (all pass): exact threshold sequence (0, 2, 3, 4) on a crafted graph;
first bound = h(s0); 200 random graphs × {zero, admissible-inconsistent h} vs
independent Dijkstra (optimal costs, unsolvable detection, strictly increasing
bounds); cycle detection; unsolvable cyclic graph; goal at root; dead-end root
and successors; invalid h at root and mid-search (6 values); negative action
costs; cooperative timeout; benchmark tasks with zero/hmax (optimal) and
DeepSeek-R1 (valid, cost ≥ L*).

**Validation results** (same 60-run batch):

| Task (L*) | Heuristic | IDA* status | cost | iterations | expanded | A* expanded |
|---|---|---|---:|---:|---:|---:|
| BW easy-p03 (20) | zero | success | 20 | 21 | 4,669,539 | 7,013 |
| BW easy-p03 (20) | hmax | success | 20 | 14 | 117,209 | 2,600 |
| BW easy-p03 (20) | DeepSeek-R1 | success | **40** | 1 | 168 | 26 (cost 20) |
| BW easy-p04 (24) | zero | timeout (bound reached 19) | — | 20 | 4,780,268 | 65,740 |
| BW easy-p04 (24) | hmax | timeout (bound reached 20) | — | 13 | 155,330 | 27,227 |
| BW easy-p04 (24) | DeepSeek-R1 | success | **36** | 1 | 120 | 84 (cost 24) |
| Miconic easy-p02 (4) | zero / hmax / DeepSeek-R1 | success | 4 / 4 / 4 | 5 / 2 / 1 | 62 / 10 / 4 | 8 / 4 / 4 |
| Transport easy-p01 (3) | zero / hmax / DeepSeek-R1 | success | 3 / 3 / 3 | 4 / 2 / 1 | 188 / 7 / 3 | 53 / 6 / 3 |

**Interpretation.** (1) Re-expansion cost is severe on Blocksworld:
666× A*'s expansions with zero h on easy-p03. (2) **IDA* exposes LLM
inadmissibility far more than A*.** The DeepSeek-R1 Blocksworld heuristic
gives h(s0) = 42 on easy-p03 (L* = 20), so IDA*'s first bound is 42 and its
first depth-first pass accepts the first goal path with cost ≤ 42 (cost 40).
A* with the same heuristic still found the optimum because its best-first
order kept cheaper paths competitive. Same pattern on easy-p04 (h(s0) = 36,
IDA* cost 36, L* = 24).

## 19. M2-05 — Comprehensive validation

### 19.1 Test inventory (all executed 2026-11-04)

`uv run --frozen pytest -q` → **151 passed** (7.7 s on this machine).

| File | Tests | Scope |
|---|---:|---|
| `tests/test_astar.py` | 33 | A* (unchanged from M2-02) |
| `tests/test_search_algorithms.py` | 45 | WA*, IDA*, shared guarantees |
| `tests/test_search_experiment_tools.py` | 28 | adapters, GBFS wrapper, reference policy, h*(s), schema validator, Job Object limits, hash-seed reproducibility |
| `tests/test_config.py` | 5 | incl. new: configured WA*/IDA* implementations importable |
| other existing suites | 40 | benchmarks, imports, LLM models, planner smoke (GBFS CLI), artifacts |

### 19.2 Requirement coverage

| Requirement | Where verified |
|---|---|
| Optimality under admissible h | random-graph Dijkstra tests (A*, WA* w=1, IDA*); benchmark tasks with zero/hmax |
| Uniform-cost equivalence | A*+zero vs Dijkstra (M2-02); IDA*+zero vs Dijkstra; WA*+zero ignores w |
| WA*(1) ≡ A* | 150 random graphs + Blocksworld easy-p03; 12/12 validation pairs |
| Path costs / reopening / duplicates / stale entries | `test_astar.py` (M2-02) + `test_weighted_astar_reopens_states` |
| Inconsistent but admissible h | `test_inconsistent_but_admissible_heuristic_still_optimal` (A*, WA*1, IDA*); admissibility checked against backward Dijkstra |
| Inadmissible h | `test_inadmissible_heuristic_gives_valid_but_suboptimal_plan` (cost 10 vs optimum 2, plan valid) |
| Goal at root, unsolvable, invalid/non-finite h, timeout | A* (M2-02) and IDA* tests; negative action costs for both |
| Plan replay / goal satisfaction | `replay_plan` / `graph_plan_cost` in every solving test; every bounded run replays its plan in the worker |
| Determinism | `test_searches_are_deterministic` (in-process); `test_fixed_hash_seed_makes_gbfs_hff_reproducible_across_processes` (cross-process) |
| GBFS regression | GBFS wrapper returns the *identical* plan as calling `gbfs_early_goal_test` directly (3 domains); `test_planner_smoke.py` (6 CLI runs) |

### 19.3 Mutation checks (scratch copy outside the repo)

| Injected bug | Caught by |
|---|---|
| IDA* next bound = max instead of min | 6 tests (threshold sequence, both random-graph tests, benchmark, inadmissible) |
| IDA* accepts a goal beyond the bound | caught (first failure under `-x`) |
| IDA* without path cycle check | caught under `-x`; full suite exceeds 300 s (IDA* loops until timeouts) |
| WA* ignores w | 2 tests (f-ordering, suboptimal-within-bound) |
| IDA* first bound 0 instead of h(s0) | `test_ida_star_first_bound_is_initial_heuristic` |

### 19.4 Easy-task reference cross-check (protocol requirement)

The protocol requires A*+hmax to be cross-checked against uniform-cost search
on all 10 easy tasks per domain. Within 60 s / 4096 MiB per solver:
**14 tasks matched exactly, 0 mismatched**; 3 tasks were proven only by UCS
(A*+hmax timed out); on 13 tasks neither solver finished (UCS: 9 timeouts,
4 memory-limit). **[BLOCKER] (budget, not correctness):** the full 30-task
cross-check cannot be completed under the provisional 60 s budget; see §21.

## 20. Bounded execution, records, and reproducibility (infrastructure)

No shared runner exists, so Faraz's experiments use a deliberately small,
clearly scoped layer in `experiments/search_algorithms/` (not `src/`, per
`docs/TEAM_RESPONSIBILITIES.md`):

| Component | Behaviour |
|---|---|
| `bounded_exec.run_bounded` | One child process per run. Windows: child assigned to a **Job Object** with `JOB_OBJECT_LIMIT_JOB_MEMORY` (hard cap on committed memory of the process tree) and kill-on-close; peak from `PeakJobMemoryUsed`. Worker gets the full time budget and stops cooperatively; the parent hard-kills the job 10 s later. Sets `PYTHONHASHSEED` per run. |
| `search_worker.py` | Parses, grounds, builds the heuristic, runs one search with the *remaining* budget (setup counts against the 60 s), replays the plan, reports h(s0) after the timed search. |
| `faraz_jobs.execute` | Maps outcomes to protocol statuses; builds a `configs/result.schema.json` record, **validated before writing** by `result_records.validate_record` (subset validator; `jsonschema` is not installed); writes one JSON per run to `results/raw/pre-experiment-v2/<run_id>.json` (1,080 records: 120 reference, 60 validation, 2 × 450 pilot) plus an extended CSV row. |
| `search_adapters.py` | Runner-facing `run_search(...)`. GBFS = the **unmodified** `gbfs_early_goal_test` behind read-only proxies that count expansions/generations, count +inf values, and raise a cooperative deadline; values are never altered or validated (baseline behaviour preserved). |

**[METHODOLOGY] Measurement definitions.** `wall_time_s` = parent-measured
process wall time (includes interpreter start, parsing, grounding);
`search_time_s` = search only. `peak_memory_mib` = Job Object peak
*committed* memory, recorded as `platform_native_process_tree_bytes`. This is
not the config's `working_set_sum_bytes`, and the difference is documented. The cap
is applied a few milliseconds after process start (interpreter boot), before
any search. POSIX code path (`RLIMIT_AS`) is untested. All writers refuse to
overwrite existing files.

**Provenance per row.** `git_commit` (`631685638316…`), `git_worktree_dirty =
True` (work is uncommitted), SHA-256 of each relevant source file and a
combined `source_bundle_sha256`, problem SHA-256, heuristic file SHA-256,
`config_id`, protocol seed, `python_hash_seed`, `parallel_jobs`, `machine_id`
(`machine-f922a64c5235`). The reference batch ran before `search_worker.py`,
`bounded_exec.py` and `faraz_jobs.py` gained the hash-seed and
`initial_state` options; `a_star.py` (`328250fb…`) and `relaxation.py`
(`d2796301…`) are unchanged since then, so the solver code of every reference
matches the current files.

## 21. M2-06 — Exact optimal-cost references

**Objective.** A reproducible exact-reference table for the 90 tasks, usable
by Ranem and the shared runner, plus an h*(s) interface.

**Workflow** (`experiments/search_algorithms/generate_optimal_refs.py`):

1. Stage easy: A*+hmax and the independent UCS on every task.
2. Stages medium/hard: A*+hmax; tasks it leaves unproven get an exact UCS
   fallback (a completed Dijkstra is itself an optimality certificate). This
   is an extension of the protocol's primary solver, recorded in `solver`.
3. If no task of a domain is proven in a stage, the next stage of that domain
   is skipped and recorded `not_requested` with the reason (no budget spent on
   searches that cannot finish).

**Status policy [METHODOLOGY].** `proven` only if an exact solver *completed*,
its plan replays to the goal with the reported cost, and, where both ran to
completion, A*+hmax and UCS agree (otherwise `cross_check_mismatch`, cost
null). Timeouts → `unknown_timeout`, memory → `unknown_memory`, errors or
exhaustion → `unknown_error`; never a cost. A timeout is never read as
unsolvable; no feasible plan from GBFS/WA*/LLM heuristics is ever a reference.
Policy unit-tested (10 cases, `test_reference_status_policy`).

**Run:** batch `refs-20261104a`, 60 s / 4096 MiB per solver run (config), 4
parallel jobs under Job Object caps, 120 runs. Output:
[`results/raw/faraz_optimal_refs.csv`](../results/raw/faraz_optimal_refs.csv)
(90 rows, one per task), per-run table `results/raw/faraz_refs_runs_refs-20261104a.csv`,
120 schema records.

### 21.1 Coverage by difficulty

| Difficulty | Blocksworld | Miconic | Transport | Total proven | Unknown / not requested |
|---|---:|---:|---:|---:|---|
| easy | 2/10 | 10/10 | 5/10 | **17/30** | 13 `unknown_timeout` |
| medium | 0/10 | 0/10 | 0/10 | **0/30** | 30 `unknown_timeout` (A*+hmax and UCS both timed out) |
| hard | — | — | — | **0/30** | 30 `not_requested` (stage skipped: no medium task proven) |

### 21.2 Proven references

| Task | L* | Solver | Cross-check | A*+hmax expanded | Search s | Peak MiB | UCS expanded |
|---|---:|---|---|---:|---:|---:|---:|
| blocksworld easy-p03 | 20 | A*+hmax | match | 2,600 | 0.30 | 17.5 | 7,013 |
| blocksworld easy-p04 | 24 | A*+hmax | match | 27,227 | 4.13 | 47.8 | 65,740 |
| miconic easy-p02 | 4 | A*+hmax | match | 4 | 0.0001 | 13.1 | 8 |
| miconic easy-p07 | 10 | A*+hmax | match | 135 | 0.005 | 14.0 | 182 |
| miconic easy-p08 | 11 | A*+hmax | match | 147 | 0.005 | 14.0 | 182 |
| miconic easy-p09 | 10 | A*+hmax | match | 146 | 0.007 | 13.8 | 208 |
| miconic easy-p11 | 13 | A*+hmax | match | 583 | 0.03 | 14.1 | 714 |
| miconic easy-p14 | 17 | A*+hmax | match | 2,384 | 0.18 | 15.1 | 2,647 |
| miconic easy-p17 | 20 | A*+hmax | match | 9,058 | 0.85 | 19.8 | 9,448 |
| miconic easy-p23 | 26 | A*+hmax | match | 103,940 | 14.98 | 109.5 | 104,926 |
| miconic easy-p25 | 28 | A*+hmax | match | 333,216 | 55.20 | 302.4 | 334,564 |
| miconic easy-p27 | 31 | UCS | A* timeout | (316,102 at timeout) | 11.64 (UCS) | 315.0 | 354,257 |
| transport easy-p01 | 3 | A*+hmax | match | 6 | 0.001 | 14.0 | 53 |
| transport easy-p03 | 6 | A*+hmax | match | 264 | 0.12 | 14.2 | 2,476 |
| transport easy-p06 | 13 | A*+hmax | match | 11,336 | 4.12 | 38.5 | 62,998 |
| transport easy-p07 | 14 | UCS | A* timeout | (91,965 at timeout) | 56.24 (UCS) | 1684.2 | 1,358,493 |
| transport easy-p08 | 15 | UCS | A* timeout | (99,767 at timeout) | 37.29 (UCS) | 1223.5 | 969,678 |

### 21.3 Interpretation

- **hmax is nearly uninformative in Miconic** (h(s0) = 3 on every Miconic
  task, L* up to 31): A*+hmax expands about as many nodes as UCS, and each
  expansion costs ~5× more, so UCS proved easy-p27 where A* timed out.
- **hmax is extremely expensive per node on larger tasks**: median A*+hmax
  expansions *within 60 s* on medium tasks were 190 (Blocksworld), 10,590.5
  (Miconic) and 12 (Transport). UCS on medium tasks exhausted time with peaks
  up to 3,949 MiB.
- **[BLOCKER] for M2-08 denominators:** under the provisional 60 s budget only
  17 easy tasks have proven optima, so gap statistics are limited to them.
  Options (team decision): a longer offline budget for references only, or a
  faster exact solver (e.g. Fast Downward A* + LM-cut). Neither was run.

### 21.4 h*(s) interface (ready, not run)

`experiments/search_algorithms/exact_reference.py`:
`exact_remaining_cost(task, state_facts, time_limit_s=...) -> ExactCost`
(statuses `proven`, `proven_dead_end`, `unknown_timeout`, `unknown_error`) and a
batch CLI (`--states <jsonl> --output <csv>`) that runs each state in a bounded
child process. Tested: along the optimal plan of Transport easy-p01,
h*(s_k) = 3 − k for every prefix state, each checked against the independent
Dijkstra from that state. **Not run on real samples: Ranem's frozen state
inventory does not exist yet, and no samples were invented.**

## 22. M2-07 — Search comparison experiments

### 22.1 Status: official matrix **[BLOCKER]**

The official comparison (90 tasks × {GBFS, A*, WA* 1.5/2.0, IDA*} × the
team's frozen heuristic sets) is **BLOCKED** and was **not** run:

1. **No shared runner** (Amina) exists on any branch; Faraz must not build a
   competing one (`docs/TEAM_RESPONSIBILITIES.md`).
2. **No frozen project heuristic trials** (`trial-01..03`, Ranem) exist; only
   the archived upstream DeepSeek-R1 baselines are available.
3. **Resource enforcement for the official matrix** must come from the shared
   runner's monitor; Faraz's Job Object layer is a stopgap.

### 22.2 What was prepared for integration (interface for Amina)

```python
# with src/pyperplan and experiments/search_algorithms on sys.path
from search_adapters import run_search, load_heuristic_class, heuristic_file_for, replay_plan
h = load_heuristic_class(heuristic_id, heuristic_file_for(heuristic_id, domain))(task)
result = run_search(algorithm, task, h, weight=w_or_None, time_limit_s=remaining_budget)
# algorithm in {"gbfs", "astar", "weighted_astar", "ida_star"}; weight only for WA*
# result: SearchResult(status, plan, plan_cost, nodes_generated, nodes_expanded, ...)
```

Status mapping used by `faraz_jobs.execute` (reusable as-is): `solved` + valid
replay + replayed cost = reported cost → `success`; otherwise `invalid_plan`;
`unsolved`/`timeout` unchanged; `error` → `planner_error` (or `memory_limit` if
`MemoryError`/peak at cap); missing heuristic file → `configuration_error`.
The runner must set `PYTHONHASHSEED` per process (§22.4). Records validated
against `configs/result.schema.json`.

### 22.3 Pilot (bounded, easy tier only, NOT the official matrix)

Matrix: 30 easy tasks × {GBFS, A*, WA* 1.5, WA* 2.0, IDA*} × {archived
DeepSeek-R1, hmax, hFF} = 450 runs, each in its own process under 60 s / 4096
MiB hard limits, 6 parallel jobs. Run twice:

| Batch | `PYTHONHASHSEED` | CSV | Outcome |
|---|---|---|---|
| `pilot-easy-20261104` | random per process (Python default) | `results/raw/faraz_search_pilot-easy-20261104.csv` | 323 success, 127 timeout |
| `pilot-easy-seeded-20261104` (**primary**) | run seed (scope `run`) | `results/raw/faraz_search_pilot-easy-seeded-20261104.csv` | 318 success, 132 timeout |

No run ended `invalid_plan`, `planner_error`, `memory_limit`, or was hard-killed
(all timeouts were cooperative). Coverage, seeded batch (valid plans / 30):

| Heuristic | GBFS | A* | WA* 1.5 | WA* 2.0 | IDA* |
|---|---:|---:|---:|---:|---:|
| DeepSeek-R1 | 30 | 30 | 30 | 30 | 23 |
| hFF | 25 | 19 | 23 | 24 | 16 |
| hmax | 19 | 13 | 14 | 15 | 7 |

Per domain (BW / Miconic / Transport): DeepSeek-R1 IDA* 6/10/7; hFF A* 3/10/6;
hmax A* 2/8/3; hmax IDA* 1/4/2; every DeepSeek-R1 best-first method 10/10/10.

**[METHODOLOGY] timing sensitivity.** In the reference batch A*+hmax solved
Miconic easy-p25 in 55.2 s (4 parallel jobs); in both pilot batches (6 jobs)
it timed out at ~59.5 s. Runs near the limit can flip with machine load;
the official matrix should fix the degree of parallelism and report it.

### 22.4 Process-level non-determinism (hash seed) **[METHODOLOGY]** **[BLOCKER for reproduction]**

Pyperplan grounding builds operators from Python `set`s of strings, so the
grounded operator *order* depends on the per-process string-hash seed; hFF's
relaxed-plan extraction is also order-dependent. Evidence:

- Same task (Transport easy-p07), `PYTHONHASHSEED` = 1, 2, 3, 4: first grounded
  operator differs every time; GBFS+DeepSeek-R1 plan cost 14 / 16 / 14 / 16;
  GBFS+hmax expansions 832 / 714 / 950 / 714; GBFS+hFF cost 14 / 17 / 17 / 15.
  A*+DeepSeek-R1 was identical (14, 14 expansions) because A* sorts successors
  by name and the heuristic is order-independent.
- Paired comparison of the two pilot batches
  (`results/derived/pre-experiment-v2/faraz-pilot-easy-seeded-20261104/batch_comparison_summary.csv`):

| Heuristic | Method | Both success | Plan differs | Cost differs | Expansions differ | Status differs |
|---|---|---:|---:|---:|---:|---:|
| DeepSeek-R1 | GBFS | 30 | 21 | 5 | 18 | 0 |
| hFF | GBFS | 25 | 18 | 14 | 20 | 2 |
| hmax | GBFS | 19 | 12 | 1 | 16 | 0 |
| hFF | WA* 1.5 / WA* 2.0 / A* / IDA* | 23 / 24 / 19 / 16 | 7 / 6 / 2 / 1 | 6 / 5 / 0 / 1 | 7 / 6 / 4 / 3 | 0 / 1 / 0 / 0 |
| DeepSeek-R1, hmax | A*, WA*, IDA* | — | 0 | 0 | 0 | 0–1 (timing only) |

**Consequence for Amina:** the paper's GBFS is not reproducible run-to-run in
this codebase unless `PYTHONHASHSEED` is fixed and recorded. Fix in Faraz's
tools: `bounded_exec.run_bounded(hash_seed=...)`; default scope is now
`task` (all algorithms/heuristics of a task share one seed, so paired
comparisons see the identical grounded task). The seeded pilot used scope
`run` (seed recorded per row in `python_hash_seed`). Protocol note proposed
in `docs/EXPERIMENT_PROTOCOL.md`.

## 23. M2-08 — Optimality gap and trade-off analysis

**Tool:** `experiments/search_algorithms/analyze_search_results.py`.
Gap (%) = 100·(L − L*)/L* only for `success` runs on tasks with a `proven`
reference and L* > 0 (zero-cost tasks counted separately; none occur). Reports
coverage with denominators, per-method quality on its own solved set, a
**paired common-solved** comparison per heuristic, and gap histograms.

**Outputs (seeded pilot):** tables in
`results/derived/pre-experiment-v2/faraz-pilot-easy-seeded-20261104/`
(`coverage.csv`, `quality.csv`, `common_solved.csv`, `gap_distribution.csv`,
`summary.md`) and figures in
`results/figures/pre-experiment-v2/faraz-pilot-easy-seeded-20261104/`
(`R3_coverage.png`, `R4_gap_distribution.png`, `R5_effort_vs_quality.png`).
Every figure is stamped "PILOT (not final)". The same analysis of the unseeded
batch is kept under `.../faraz-pilot-easy-20261104/` for the comparison in §22.4.
Figure design: fixed colour per algorithm across all figures (reference
categorical palette, first slots in documented order), direct labels on every
mark, one y-axis per panel, faceted by heuristic. The palette validator script
could not be run (Node.js is not installed).

### 23.1 Quality on each method's own solved set (seeded pilot)

Gap statistics use the 17 easy tasks with proven L* (gap n ≤ 17).

| Heuristic | Method | Solved | Gap n | Optimal | Mean gap % | Median gap % | Max gap % | Median expanded |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| DeepSeek-R1 | GBFS | 30 | 17 | 11 | 3.08 | 0 | 16.7 | 29.5 |
| DeepSeek-R1 | A* | 30 | 17 | 12 | 2.79 | 0 | 16.7 | 29.5 |
| DeepSeek-R1 | WA* 1.5 | 30 | 17 | 12 | 2.79 | 0 | 16.7 | 29.5 |
| DeepSeek-R1 | WA* 2.0 | 30 | 17 | 12 | 2.79 | 0 | 16.7 | 29.5 |
| DeepSeek-R1 | IDA* | 23 | 17 | 2 | 21.8 | 17.6 | 100 | 32 |
| hFF | GBFS | 25 | 17 | 6 | 8.49 | 6.67 | 30 | 37 |
| hFF | A* | 19 | 17 | 16 | 0.452 | 0 | 7.69 | 42 |
| hFF | WA* 1.5 | 23 | 17 | 12 | 2.93 | 0 | 20 | 40 |
| hFF | WA* 2.0 | 24 | 17 | 5 | 6.92 | 5 | 25 | 37 |
| hFF | IDA* | 16 | 16 | 15 | 0.481 | 0 | 7.69 | 41.5 |
| hmax | GBFS | 19 | 16 | 7 | 6.03 | 5.44 | 16.7 | 437 |
| hmax | A* | 13 | 13 | 13 | 0 | 0 | 0 | 583 |
| hmax | WA* 1.5 | 14 | 14 | 14 | 0 | 0 | 0 | 1,410 |
| hmax | WA* 2.0 | 15 | 15 | 13 | 1.62 | 0 | 16.7 | 1,510 |
| hmax | IDA* | 7 | 7 | 7 | 0 | 0 | 0 | 70,400 |

(Median expanded values ≥ 1,000 are rounded from `summary.md`'s 3-significant-digit output; exact values are in `quality.csv`.)

### 23.2 Paired comparison on common-solved tasks (seeded pilot)

| Heuristic | Common tasks | Method: mean gap % (optimal / gap n), median expanded |
|---|---:|---|
| DeepSeek-R1 | 23 | GBFS 3.08 (11/17), 21 · A* 2.79 (12/17), 25 · WA*1.5 2.79 (12/17), 20 · WA*2 2.79 (12/17), 20 · IDA* 21.8 (2/17), 32 |
| hFF | 16 | GBFS 8.54 (6/16), 21 · A* 0.481 (15/16), 23.5 · WA*1.5 2.88 (12/16), 23.5 · WA*2 7.12 (5/16), 22 · IDA* 0.481 (15/16), 41.5 |
| hmax | 7 | GBFS 3.81 (5/7), 48 · A* 0 (7/7), 146 · WA*1.5 0 (7/7), 146 · WA*2 2.38 (6/7), 122 · IDA* 0 (7/7), 70,400 |

### 23.3 Interpretation (pilot only, 17 proven easy tasks)

- **DeepSeek-R1 dominates coverage** on the easy tier (30/30 for every
  best-first method) with tiny search effort, but A* with it is **not
  optimal**: 5 of 17 proven tasks suboptimal (max gap 16.7 %). A*, WA* 1.5
  and WA* 2.0 give identical gaps: the LLM values are large relative to g,
  so A*'s ordering is already nearly greedy, and GBFS is barely worse
  (3.08 % vs 2.79 %).
- **IDA* is the worst match for the LLM heuristic** (mean gap 21.8 %, only
  2/17 optimal, up to 100 %), because a single overestimating h(s0) sets the
  first bound too high (§18).
- **hFF**: weight trades quality for coverage monotonically: A* 0.45 % gap /
  19 solved → WA* 1.5 2.93 % / 23 → WA* 2.0 6.92 % / 24 → GBFS 8.49 % / 25.
- **hmax**: every optimal-guaranteed method returned L* (0 % gap), WA* stayed
  within its bound, but hmax is too expensive to scale (13/30 for A*).
- Solved-only comparisons mislead here (methods solve different subsets),
  which is why the common-solved table and denominators are reported.

## 24. M2-09 — Failure and guarantee audit

**Tool:** `experiments/search_algorithms/audit_failures.py` (exit code 1 on any
guarantee violation). Applied to the seeded pilot + validation batch (510 runs);
outputs `audit_*.csv` and `audit_summary.md` in
`results/derived/pre-experiment-v2/faraz-pilot-easy-seeded-20261104/`.

### 24.1 Guarantees vs outcomes (510 runs)

| Guarantee class | Runs (method × heuristic) | Violations |
|---|---|---:|
| `optimal` (A*, IDA*, WA* w=1 with zero/hmax) | A*+hmax 17 empirically optimal / 17 not solved; IDA*+hmax 10 / 24; WA*1+hmax 4; zero (A* 4, IDA* 3 + 1 not solved, WA*1 4) 11 optimal / 1 not solved | **0** |
| `bounded_w` (WA* 1.5/2.0 with zero/hmax) | WA*1.5+hmax 18 optimal / 16 not solved; WA*2+hmax 17 optimal, **2 suboptimal within bound** / 15 not solved; zero 8 optimal | **0** |
| `none` (GBFS; hFF; DeepSeek-R1) | e.g. A*+DeepSeek-R1 16 optimal / 5 suboptimal / 13 no proven ref; IDA*+DeepSeek-R1 4 / 17 / 6 / 7 not solved; GBFS+hFF 6 / 11 / 8 / 5 | n/a |

Run statuses: 132 timeouts in the seeded pilot plus 2 in the validation batch
(listed with details in `audit_failures.csv`, 134 rows); 0 memory-limit, 0
invalid plans, 0 heuristic runtime errors, 0 exhausted (`unsolved`) searches,
0 missing or hash-mismatched heuristic files (all three DeepSeek-R1 files
match `provenance.json`).

**Inadmissibility certificates.** Comparing h(s0) with proven L*: DeepSeek-R1
overestimates at the initial state on **15 of 17** proven tasks (median
h(s0)/L* = 1.18, max 2.1), so it is provably inadmissible on those tasks.
hFF never exceeded L* at s0 on these tasks (max ratio 1.0), although it is
inadmissible in general. hmax max ratio 0.75, zero 0, as admissibility requires.

**Unsound pruning check.** No DeepSeek-R1 run returned +inf for any state and
none ended `unsolved` on a task with a proven plan, so no evidence of
incorrect dead-end pruning in this pilot.

Exact-reference status (task level): 17 `proven`, 43 `unknown_timeout`, 30
`not_requested` (§21.1).

### 24.2 Guarantees explained (presentation notes)

| Property | Holds when | Evidence here |
|---|---|---|
| **Completeness** (finds a plan if one exists, given enough resources) | A*, WA*, IDA*, GBFS on finite state spaces with truthful +inf | Timeouts are resource failures, not incompleteness; 0 `unsolved` |
| **Optimality** | A* / IDA* / WA*(w=1) with **admissible** h (zero, hmax) | 0 violations against proven L* |
| **Bounded suboptimality** cost ≤ w·L* | WA* with admissible h and w ≥ 1 (reopening kept) | WA* 2.0 + hmax: 2 suboptimal runs, both within bound |
| **Empirically optimal plan** | Observed cost = proven L*; no guarantee implied | A*+DeepSeek-R1: 16 such runs, yet 5 suboptimal |
| **Proven reference** | Exact solver completed and plan validated | 17/90 tasks |
| **Failure within resources** | Timeout / memory limit | Says nothing about solvability or optimum |

- *A* with admissible h is optimal:* when the goal is popped, every frontier
  node has f ≥ the goal's cost, and admissibility makes f a lower bound on any
  plan through that node (§4.1).
- *A* with an LLM h has no such guarantee:* the lower-bound argument fails as
  soon as h overestimates. DeepSeek-R1 does so (15/17 tasks at s0) and A*
  returned 5 suboptimal plans.
- *WA* bounds need admissibility (and w ≥ 1):* the proof multiplies an
  admissible lower bound by w; with an overestimating h there is no bound.
- *IDA* may be infeasible despite small memory:* no duplicate detection, so
  transpositions are re-expanded every iteration (4.67 M vs 7,013 expansions
  on Blocksworld easy-p03; 23/30 hmax runs timed out while peak memory stayed
  ≤ 21.9 MiB).
- *An LLM h returning +inf can wrongly prune:* all searches treat +inf as a
  dead end and never expand it; if the heuristic is wrong, a reachable
  solution can be cut off and the search can end `unsolved` on a solvable
  task. The audit checks this explicitly (0 cases observed).

## 25. Files created or modified in Part II (uncommitted)

| File | Change |
|---|---|
| `src/pyperplan/search/a_star.py` | `validate_weight`, `weighted_astar_search_result`; `SearchResult` optional IDA* fields; `nodes_reopened` logged with `%s` |
| `src/pyperplan/search/ida_star.py` (new) | IDA* |
| `src/pyperplan/search/__init__.py` | exports `weighted_astar_search_result`, `ida_star_search`, `ida_star_search_result` |
| `configs/experiment.v2.toml` | WA*/IDA* implementation pointers (`pending:faraz` → project functions) |
| `tests/test_config.py` | asserts pointers; imports every configured implementation |
| `tests/test_search_algorithms.py` (new) | 45 tests |
| `tests/test_search_experiment_tools.py` (new) | 28 tests |
| `docs/EXPERIMENT_PROTOCOL.md` | IDA*/GBFS counter definitions; `PYTHONHASHSEED` requirement (proposed) |
| `docs/FARAZ_PROGRESS.md` | header, §2 status, §15 note, Part II |
| `experiments/search_algorithms/README.md` | tool inventory |
| `experiments/search_algorithms/{search_adapters,bounded_exec,search_worker,faraz_jobs,result_records,generate_optimal_refs,exact_reference,run_faraz_pilot,analyze_search_results,audit_failures,compare_pilot_batches}.py` (new) | §20–§24 |
| `results/raw/…`, `results/derived/pre-experiment-v2/…`, `results/figures/pre-experiment-v2/…` (git-ignored) | outputs listed in §21–§24 |

Not modified: `search/gbfs.py`, `pyperplan.py`, benchmarks, manifest,
artifacts, `configs/result.schema.json`, other members' directories.

## 26. Commands to reproduce Part II

```bash
uv sync --frozen --group dev
uv run --frozen python tools/verify_benchmarks.py
uv run --frozen pytest -q                                   # 151 tests
S=experiments/search_algorithms
# M2-06 references (writes results/raw/faraz_optimal_refs.csv; refuses to overwrite)
uv run --frozen python $S/generate_optimal_refs.py --jobs 4 --batch-id refs-20261104a
# M2-03/M2-04 validation batch
uv run --frozen python $S/run_faraz_pilot.py --batch-id validation-wa-ida-20261104 \
  --problems blocksworld:easy-p03 blocksworld:easy-p04 miconic:easy-p02 transport:easy-p01 \
  --algorithms astar weighted_astar:1.0 weighted_astar:1.5 weighted_astar:2.0 ida_star \
  --heuristics zero hmax deepseek-r1 --jobs 6
# M2-07 pilots (the unseeded batch was produced before hash seeding existed;
# reproduce its behaviour with --no-hash-seed; the seeded batch used scope "run")
uv run --frozen python $S/run_faraz_pilot.py --batch-id pilot-easy-20261104 --difficulties easy \
  --algorithms gbfs astar weighted_astar:1.5 weighted_astar:2.0 ida_star \
  --heuristics deepseek-r1 hmax hff --jobs 6 --no-hash-seed
uv run --frozen python $S/run_faraz_pilot.py --batch-id pilot-easy-seeded-20261104 --difficulties easy \
  --algorithms gbfs astar weighted_astar:1.5 weighted_astar:2.0 ida_star \
  --heuristics deepseek-r1 hmax hff --jobs 6 --hash-seed-scope run
# M2-08 / M2-09 / batch comparison
T=faraz-pilot-easy-seeded-20261104
uv run --frozen python $S/compare_pilot_batches.py --a results/raw/faraz_search_pilot-easy-20261104.csv \
  --b results/raw/faraz_search_pilot-easy-seeded-20261104.csv --tag $T
uv run --frozen python $S/analyze_search_results.py --runs results/raw/faraz_search_pilot-easy-seeded-20261104.csv \
  --tag $T --scope "PILOT (not final): 30 easy tasks, archived DeepSeek-R1/hmax/hFF, 60 s / 4096 MiB, 1 seeded run each, machine-f922a64c5235"
uv run --frozen python $S/audit_failures.py --runs results/raw/faraz_search_pilot-easy-seeded-20261104.csv \
  results/raw/faraz_search_validation-wa-ida-20261104.csv --tag $T
```

Re-running a command with an existing batch ID or tag stops with "refusing to
overwrite"; use a new ID. The 2026-11-04 batches took 1.54 h (references),
0.06 h (validation) and 2.43 h / 2.45 h (pilots) of summed process wall time.

## 27. Dependencies and handoffs (Part II)

**Amina (shared runner, reproduction):**
- **[BLOCKER]** The official M2-07 matrix waits for the shared runner. Use
  `search_adapters.run_search` (§22.2); GBFS stays her unmodified baseline.
- **[BLOCKER for reproduction]** Fix and record `PYTHONHASHSEED` per process
  (§22.4); otherwise GBFS plans/costs vary between identical runs.
- Job Object code in `bounded_exec.py` can seed the runner's Windows monitor;
  note it caps committed memory, not working set.
- Fix the degree of parallelism (runs near 60 s flip, §22.3).

**Ranem (heuristic reliability):**
- `results/raw/faraz_optimal_refs.csv`: 17 proven L* (easy only) for
  overestimation analysis; `unknown_*` rows must not be used as ground truth.
- `exact_reference.py` computes h*(s) for her frozen state inventory (batch
  CLI with hard limits). Waiting on that inventory.
- Initial-state certificates: DeepSeek-R1 h(s0) > L* on 15/17 tasks.
- **[BLOCKER]** New heuristic trials `trial-01..03` are needed before the
  official comparison; only archived DeepSeek-R1 was used here.

**Team decisions needed:** longer offline budget or faster exact solver for
references (only 17/90 proven under 60 s); approve the `PYTHONHASHSEED`
protocol note; results archiving (`results/` is git-ignored, §14).

## 28. Remaining work before the final paper

1. **Exact references beyond easy** (blocking good gap denominators): agree a
   reference-only budget or solver; rerun `generate_optimal_refs.py` with a new
   batch ID; also complete the 30-task UCS cross-check.
2. **Official M2-07 matrix** through Amina's runner on all 90 tasks with the
   frozen trial heuristics and seeded processes (scope `task`), fixed
   parallelism, then rerun M2-08/M2-09 tools on its output.
3. Run `exact_reference.py` on Ranem's frozen state inventory.
4. Only after 1–2: promote findings to **[PAPER RESULT]** (none so far). Pilot
   observations worth re-testing at scale: LLM-heuristic A* is not optimal but
   near-greedy; IDA* amplifies LLM overestimation; hFF weight/quality trade-off.
5. Review and commit Part II; open a PR from `feature/faraz-search`.

## 29. Shared-runner integration review and fixes (2026-11-10)

Amina's shared runner now exists (`feature/amina-reproduction`: GBFS runner
`run_reproduction.py`; `feature/amina-runner-wiring`: plus
`run_search_algorithms.py`, which runs this workstream's `search_worker.py`
under the same limits and record format). The M2-07 blocker "no shared
runner" (§22.1) is therefore resolved, pending the fixes below. Review
findings and fixes (all uncommitted; not pushed):

| Finding | Fix | Branch |
|---|---|---|
| Runner kills the worker at exactly the time limit; the worker computed h(s0) *after* the search, so a timed-out run could be killed before reporting (node counts lost) | Worker computes h(s0) during setup; reporting margin 0.5 → 1.0 s. Test: worker reports under a parent with zero kill grace | `feature/faraz-search` (+ identical copy on the wiring branch) |
| Worker knew only `zero`/`hmax`/`hff`; other Pyperplan built-ins (`blind`, `lmcut`, …) failed every run | `search_adapters` discovers all built-ins like the CLI; `blind`/`lmcut` marked admissible in `faraz_jobs`/`audit_failures` | same |
| Runner records lack the extended columns M2-08/M2-09 need; heuristic IDs differ (file stem / `upstream-deepseek-r1` vs `deepseek-r1`) | New `convert_runner_records.py`: selects runs via batch sidecars, maps IDs, pulls search statistics from worker logs | same |
| Per-run `PYTHONHASHSEED` (includes algorithm/heuristic/trial) mixes hash-seed noise into paired and trial comparisons (§22.4) | `--hash-seed-scope task\|run` in both runners, default `task` = same formula as `faraz_jobs` (verified by test); `run` reproduces the original 270 runs; seeds listed in batch sidecars | `feature/amina-runner-wiring` |
| Invalid plans recorded as `validator_error` (validator prints failures to stderr) | Validator interpreted by exit code; test covers valid / goal-not-reached / unknown operator / missing file | wiring |
| `--heuristic zero` rejected | `zero` added to built-ins | wiring |
| Reproduction summary mixed A*/WA*/IDA* and non-batch records into GBFS tables | Summary keeps only GBFS records listed in a batch sidecar | wiring |

Tests: `feature/faraz-search` 154 passed; `feature/amina-runner-wiring` 158
passed (incl. new `tests/test_shared_runner.py`, with an end-to-end GBFS + A*
run on Blocksworld easy-p03 confirming both runners use the same task hash
seed). Benchmark hashes intact on both.
