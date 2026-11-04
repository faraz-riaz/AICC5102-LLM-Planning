# Faraz — search-algorithm workstream progress report

Living research report for the AICC5102 search-algorithm workstream (branch
`feature/faraz-search`). Every number below is copied from a file in this
repository or from a command that was actually run. Nothing here is a final
paper result unless it is explicitly tagged **[PAPER RESULT]**; at present
**no item qualifies**, because only tiny validation runs have been performed.

Tags used: **[METHODOLOGY]** — a decision that affects how later experiments
must be run or interpreted; **[BLOCKER]** — something that prevents or
endangers later work until resolved; **[PAPER RESULT]** — a result intended for
the final report (none yet).

Status as of 2026-11-04: **M2-01 and M2-02 complete; all work uncommitted on
`feature/faraz-search` (base commit `eb8f95e`).**

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

The repository only defines the IDs M2-01 and M2-02 (in this workstream's
README and the task brief). The text of M2-03 … M2-09 is **not recorded
anywhere in the repository**, so those rows are deliberately left undefined
rather than guessed. Fill them in from the team project plan.

| ID | Task | Status | Evidence |
|---|---|---|---|
| M2-01 | Inspect and document the Pyperplan search architecture | **Complete** | §3 of this report |
| M2-02 | Implement/adapt A* with correctness tests and validation | **Complete** | `src/pyperplan/search/a_star.py`, `tests/test_astar.py` (33 tests pass), `results/raw/faraz_astar_validation.csv` (12/12 rows pass) |
| M2-03 … M2-09 | *Definitions not recorded in repo — confirm against the project plan* | Not started (out of scope for this milestone) | — |

Pending workstream scope that the repository *does* record
(`docs/TEAM_RESPONSIBILITIES.md`, `configs/experiment.v2.toml`), without
asserting which M2 ID each item maps to:

| Pending item | Recorded in | Status |
|---|---|---|
| Weighted A* with weights 1.0 / 1.5 / 2.0 (w=1.0 must equal A*) | `configs/experiment.v2.toml` `[algorithms.weighted_astar]` | `pending:faraz`; not started |
| IDA* (upstream `ids` is **not** IDA*) | `docs/EXPERIMENT_PROTOCOL.md` | `pending:faraz`; not started |
| UCS cross-check on all 10 easy tasks per domain | `[optimality_reference]` | Partially covered: 4 of 30 easy tasks validated here |
| Exact optimal references for the 90 tasks | `[optimality_reference]` | Not started |
| Search comparisons (GBFS vs A* vs WA* vs IDA*) | `docs/TEAM_RESPONSIBILITIES.md` | Not started; depends on Amina's shared runner |

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

## 15. Remaining work and next steps

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
