# Upstream provenance

## Imported GitHub source

- Repository: <https://github.com/abcorrea/llm-generated-heuristics>
- Imported commit: `4c3deabc058e3ab181250a742181412507920d18`
- Commit timestamp: 2026-04-11T12:46:11+01:00
- Commit subject: `Fix import issue in end-to-end.py`
- Import method: source snapshot into a new Git repository; upstream Git history was not retained
- License: GPL-3.0-or-later, preserved as `LICENSE`

The snapshot contributes the original `src/pyperplan` planner, `src/llm_heuristics` generation interfaces/templates, top-level `llm-heuristics.py` and `end-to-end.py`, `pyproject.toml`, `uv.lock`, `CITATION.cff`, and the authors' benchmark copies. The original README is retained at `docs/UPSTREAM_README.md`.

Local foundation changes include project organization, a three-domain curated benchmark distribution, frozen manifests, verification/replay tools, shared configuration/schema, documentation, tests, and CI. The imported planner and prompt construction code has not been refactored. The LLM provider adapter and two inherited command-line entry points were updated locally to support `.env` configuration, provider-specific model defaults, current model request shapes, Gemini Developer API keys, and Vertex AI Application Default Credentials. These adapter changes are covered by no-network tests. The project Python range, runtime configuration dependency, and development test group were added to `pyproject.toml`, and the lock is regenerated for this repository.

Although upstream already contains Pyperplan implementations registered as `astar`, `wastar`, and `ids`, upstream `ids` is not IDA*. This foundation does not add or evaluate the planned A*, Weighted A*, or IDA* comparison implementations. Future member work must distinguish inherited behavior from project extensions.

## Benchmark provenance

The selected files come from the authors' own `benchmarks/ipc2023-learning` tree at the commit above. That upstream tree contains 30 easy, 30 medium, and 30 hard test instances in each requested domain and 99 training instances plus `domain.pddl` in each. It is derived from the IPC 2023 Learning Track, but this project does not replace it with a newer checkout of <https://github.com/ipc2023-learning/benchmarks>.

Only Blocksworld, Miconic, and Transport are retained. Their complete training data and example assets are present; their test distributions contain only the 90 manifest-selected problems and three required domain files. There are no unrelated-domain exceptions.

## Zenodo archive comparison

- DOI: <https://doi.org/10.5281/zenodo.17400964>
- Record: `17400964`, version v1, published 2025-10-20/21
- File: `correa-et-al-neurips2025.zip`
- Size: `200032733` bytes
- MD5: `8e20619169553ec6eb8b5f10e262a2d9`

Zenodo contains four experimental-data areas: `archive-heuristics` (all generated heuristics, including ablations), `logs` (generation prompts, responses, and extracted code), `benchmarks`, and `experiments` (planning scripts plus HTML reports under `data`). The first, second, and experiment/report areas are absent from the GitHub snapshot.

On 2026-11-04 the ZIP's 13,146-entry central directory and relevant contents were inspected after size/MD5 verification. Exact copies of the three files under `archive-heuristics/selected-heuristics/deepseek-r1/` are retained at `artifacts/upstream/deepseek-r1/`. Their provenance record includes source paths, entry/log hashes, generation parameters, training-selection scores, selector behavior, and raw metadata hashes. Full logs, reports, properties, and unrelated heuristic candidates are not committed.

The 200 MB ZIP is intentionally not committed. Retrieve and verify it only when needed:

```bash
uv run --frozen python tools/fetch_zenodo_archive.py
```

Pass `--extract` to extract after checksum verification. The default `external/archives/` destination is ignored by Git.

## Citation

Corrêa, Augusto B.; Pereira, André G.; Seipp, Jendrik. “Classical Planning with LLM-Generated Heuristics: Challenging the State of the Art with Python Code.” NeurIPS 2025. Software and experiment data: DOI `10.5281/zenodo.17400964`.
