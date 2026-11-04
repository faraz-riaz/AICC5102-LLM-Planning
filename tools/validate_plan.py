#!/usr/bin/env python3
"""Replay a Pyperplan ``.soln`` file and fail unless it reaches the goal."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PYPERPLAN_DIR = ROOT / "src" / "pyperplan"
sys.path.insert(0, str(PYPERPLAN_DIR))

import grounding  # noqa: E402
from pddl.parser import Parser  # noqa: E402


def validate(domain_file: Path, problem_file: Path, plan_file: Path) -> tuple[bool, str]:
    parser = Parser(str(domain_file), str(problem_file))
    domain = parser.parse_domain()
    problem = parser.parse_problem(domain)
    task = grounding.ground(problem)
    operators = {operator.name: operator for operator in task.operators}
    state = task.initial_state

    steps = [line.strip() for line in plan_file.read_text(encoding="utf-8").splitlines() if line.strip()]
    for number, name in enumerate(steps, start=1):
        operator = operators.get(name)
        if operator is None:
            return False, f"step {number}: unknown grounded operator {name!r}"
        if not operator.applicable(state):
            return False, f"step {number}: operator is not applicable: {name}"
        state = operator.apply(state)

    if not task.goal_reached(state):
        return False, f"goal not reached after {len(steps)} steps"
    return True, f"valid plan: goal reached after {len(steps)} steps"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("domain", type=Path)
    parser.add_argument("problem", type=Path)
    parser.add_argument("plan", type=Path)
    args = parser.parse_args()
    try:
        valid, message = validate(args.domain, args.problem, args.plan)
    except (OSError, ValueError) as exc:
        print(f"plan validation failed: {exc}", file=sys.stderr)
        return 1
    print(message, file=sys.stdout if valid else sys.stderr)
    return 0 if valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
