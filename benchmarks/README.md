# Frozen benchmark

`manifest.json` is the machine-readable source of truth; `manifest.csv` is an identical tabular view. Version `aicc5102-90-v1` selects 90 test problems with seed 5102: 10 easy, 10 medium, and 10 hard from each of Blocksworld, Miconic, and Transport.

Testing contains only selected problems and required domain files. Training retains all upstream training problems and heuristic-generation example assets for the same domains. Run `uv run --frozen python tools/verify_benchmarks.py` before experiments. See `docs/REPRODUCIBILITY.md` before attempting to regenerate anything.
