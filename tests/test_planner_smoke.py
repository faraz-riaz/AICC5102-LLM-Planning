from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
BENCHMARKS = ROOT / "benchmarks" / "ipc2023-learning" / "testing"
PLANNER = ROOT / "src" / "pyperplan" / "pyperplan.py"
VALIDATOR = ROOT / "tools" / "validate_plan.py"


@pytest.mark.parametrize(
    ("domain", "problem"),
    [
        ("blocksworld", "easy-p03.pddl"),
        ("miconic", "easy-p02.pddl"),
        ("transport", "easy-p01.pddl"),
    ],
)
def test_original_gbfs_hff_returns_replayable_plan(
    tmp_path: Path, domain: str, problem: str
) -> None:
    case_dir = tmp_path / domain
    case_dir.mkdir()
    domain_file = case_dir / "domain.pddl"
    problem_file = case_dir / problem
    shutil.copyfile(BENCHMARKS / domain / "domain.pddl", domain_file)
    shutil.copyfile(BENCHMARKS / domain / problem, problem_file)

    completed = subprocess.run(
        [
            sys.executable,
            str(PLANNER),
            "-s",
            "gbfs_early_goal_test",
            "-H",
            "hff",
            str(domain_file),
            str(problem_file),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "Parsing Problem" in completed.stdout
    assert "Plan length:" in completed.stdout
    plan_file = problem_file.with_suffix(problem_file.suffix + ".soln")
    assert plan_file.is_file()

    replay = subprocess.run(
        [sys.executable, str(VALIDATOR), str(domain_file), str(problem_file), str(plan_file)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert replay.returncode == 0, replay.stdout + replay.stderr
