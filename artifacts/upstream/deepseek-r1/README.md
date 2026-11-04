# Original selected DeepSeek R1 heuristics

These three Python files are exact copies from Zenodo record `17400964`, archive directory `archive-heuristics/selected-heuristics/deepseek-r1/`. They are the archive's explicitly published selected DeepSeek R1 heuristics for the three AICC5102 domains:

| Domain | File | SHA-256 |
|---|---|---|
| Blocksworld | `blocksworld9_10.py` | `106d55bfa8968f65cc88e26019a9c2163a2a74e408997c83e6a91d69293c5079` |
| Miconic | `miconic11_10.py` | `10c099e50edec42b1139285639b22b900c56a5ba581d135d8361e12d07b63cf9` |
| Transport | `transport7_10.py` | `36b883d5f14d08dcb32af30e00d05fa4d44b371a9481fe82005a71f8f14bb290` |

The generation logs record model `deepseek-r1`, temperature `1.0`, top-P `0.5`, prompt format `reordered`, and Python 3.13.2. The authors generated 25 candidates per domain and evaluated them on all 99 training tasks with a 300-second/8192-MiB budget. Their selector maximized coverage, then summed expansion score, then summed agile score. Blocksworld and Transport have unique winners under those criteria. Miconic candidate 11 is tied exactly with eight other candidates and was retained by the selector's first-encounter behavior.

The archive also contains a later specialized-GBFS script with different Blocksworld and Transport candidate mappings. Those files are not the artifacts in the explicit `selected-heuristics/deepseek-r1` directory and are therefore not imported here.

See `provenance.json` for archive paths, checksums, selection metrics, source-log hashes, and omitted metadata. The full generation logs and 11.5 MB training properties file remain in the ignored Zenodo download because they are not needed to execute these heuristics. They can be recovered with `tools/fetch_zenodo_archive.py`.

These are frozen upstream reproduction artifacts, not the three new independently generated heuristic trials planned for this project.
