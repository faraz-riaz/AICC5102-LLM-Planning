from __future__ import annotations

import importlib
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_locked_dependencies_import() -> None:
    for module in ("click", "google.genai", "lab", "openai", "pandas"):
        importlib.import_module(module)


def test_upstream_planner_modules_import() -> None:
    sys.path.insert(0, str(ROOT / "src" / "pyperplan"))
    try:
        importlib.import_module("grounding")
        importlib.import_module("heuristics.relaxation")
        importlib.import_module("search.gbfs")
    finally:
        sys.path.pop(0)
