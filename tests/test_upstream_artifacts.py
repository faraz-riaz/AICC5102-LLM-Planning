from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_DIR = ROOT / "artifacts" / "upstream" / "deepseek-r1"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_selected_deepseek_r1_artifacts_match_provenance() -> None:
    provenance = json.loads((ARTIFACT_DIR / "provenance.json").read_text(encoding="utf-8"))
    assert provenance["source"]["archive_md5"] == "8e20619169553ec6eb8b5f10e262a2d9"
    assert provenance["generation"]["model"] == "deepseek-r1"
    records = provenance["heuristics"]
    assert {record["domain"] for record in records} == {"blocksworld", "miconic", "transport"}
    assert {path.name for path in ARTIFACT_DIR.glob("*.py")} == {
        "blocksworld9_10.py",
        "miconic11_10.py",
        "transport7_10.py",
    }
    for record in records:
        artifact = ARTIFACT_DIR / record["filename"]
        assert artifact.is_file()
        assert sha256(artifact) == record["sha256"]
        assert record["source_entries_identical"] is True


def test_selected_heuristic_modules_import() -> None:
    sys.path.insert(0, str(ROOT / "src" / "pyperplan"))
    try:
        for path in sorted(ARTIFACT_DIR.glob("*.py")):
            spec = importlib.util.spec_from_file_location(f"upstream_{path.stem}", path)
            assert spec is not None and spec.loader is not None
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            classes = [name for name in dir(module) if name.endswith("Heuristic") and name != "Heuristic"]
            assert len(classes) == 1
    finally:
        sys.path.pop(0)
