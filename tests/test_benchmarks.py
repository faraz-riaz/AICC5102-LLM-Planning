from __future__ import annotations

import csv
import subprocess
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_frozen_manifest_verifier() -> None:
    completed = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "verify_benchmarks.py")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_manifest_paths_and_counts() -> None:
    with (ROOT / "benchmarks" / "manifest.csv").open(encoding="utf-8", newline="") as stream:
        records = list(csv.DictReader(stream))
    counts = Counter((record["domain"], record["difficulty"]) for record in records)
    assert len(records) == 90
    assert set(counts.values()) == {10}
    for record in records:
        assert (ROOT / record["relative_problem_path"]).is_file()
        assert (ROOT / record["relative_domain_path"]).is_file()
