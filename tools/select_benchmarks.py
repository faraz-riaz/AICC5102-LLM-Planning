#!/usr/bin/env python3
"""Create the frozen AICC5102 90-problem benchmark selection.

This script is intentionally conservative: without ``--write`` it only prints
the proposed selection, and it will not replace an existing manifest unless
``--force`` is also supplied.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import shutil
from collections import Counter
from pathlib import Path


SELECTION_SEED = 5102
SELECTION_SCRIPT_VERSION = "1.0.0"
BENCHMARK_VERSION = "aicc5102-90-v1"
SAMPLING_DATE = "2026-11-04"
UPSTREAM_REPOSITORY = "https://github.com/abcorrea/llm-generated-heuristics"
UPSTREAM_COMMIT = "4c3deabc058e3ab181250a742181412507920d18"
DOMAINS = ("blocksworld", "miconic", "transport")
DIFFICULTIES = ("easy", "medium", "hard")
PREDETERMINED = {("blocksworld", "easy"): "easy-p03.pddl"}
RECORD_FIELDS = (
    "domain",
    "difficulty",
    "problem_id",
    "relative_problem_path",
    "relative_domain_path",
    "benchmark_split",
    "source_repository",
    "upstream_commit_or_archive_version",
    "sha256_problem",
    "sha256_domain",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stratum_seed(domain: str, difficulty: str) -> int:
    """Derive a stable seed without relying on Python's randomized hash()."""
    key = f"{SELECTION_SEED}:{domain}:{difficulty}".encode("utf-8")
    return int.from_bytes(hashlib.sha256(key).digest()[:8], "big")


def select(source_root: Path) -> tuple[list[tuple[str, str, Path]], dict[str, int]]:
    selected: list[tuple[str, str, Path]] = []
    candidate_counts: dict[str, int] = {}

    for domain in DOMAINS:
        domain_dir = source_root / "testing" / domain
        if not (domain_dir / "domain.pddl").is_file():
            raise FileNotFoundError(f"missing domain file: {domain_dir / 'domain.pddl'}")
        for difficulty in DIFFICULTIES:
            candidates = sorted(domain_dir.glob(f"{difficulty}-*.pddl"), key=lambda p: p.name)
            candidate_counts[f"{domain}/{difficulty}"] = len(candidates)
            if len(candidates) < 10:
                raise ValueError(
                    f"{domain}/{difficulty} has {len(candidates)} candidates; 10 required"
                )

            predetermined_name = PREDETERMINED.get((domain, difficulty))
            predetermined: list[Path] = []
            if predetermined_name:
                predetermined_path = domain_dir / predetermined_name
                if predetermined_path not in candidates:
                    raise FileNotFoundError(
                        f"predetermined problem is not an eligible candidate: {predetermined_path}"
                    )
                candidates.remove(predetermined_path)
                predetermined.append(predetermined_path)

            rng = random.Random(stratum_seed(domain, difficulty))
            sampled = rng.sample(candidates, 10 - len(predetermined))
            for problem in sorted(predetermined + sampled, key=lambda p: p.name):
                selected.append((domain, difficulty, problem))

    return selected, candidate_counts


def build_records(
    selected: list[tuple[str, str, Path]], source_root: Path
) -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    for domain, difficulty, problem in selected:
        domain_file = source_root / "testing" / domain / "domain.pddl"
        records.append(
            {
                "domain": domain,
                "difficulty": difficulty,
                "problem_id": problem.stem,
                "relative_problem_path": (
                    f"benchmarks/ipc2023-learning/testing/{domain}/{problem.name}"
                ),
                "relative_domain_path": (
                    f"benchmarks/ipc2023-learning/testing/{domain}/domain.pddl"
                ),
                "benchmark_split": "test",
                "source_repository": UPSTREAM_REPOSITORY,
                "upstream_commit_or_archive_version": UPSTREAM_COMMIT,
                "sha256_problem": sha256(problem),
                "sha256_domain": sha256(domain_file),
            }
        )
    return records


def metadata(
    records: list[dict[str, str]], candidate_counts: dict[str, int]
) -> dict[str, object]:
    counts = Counter((row["domain"], row["difficulty"]) for row in records)
    per_domain_counts = {
        domain: {
            difficulty: counts[(domain, difficulty)] for difficulty in DIFFICULTIES
        }
        | {"total": sum(counts[(domain, d)] for d in DIFFICULTIES)}
        for domain in DOMAINS
    }
    return {
        "benchmark_version": BENCHMARK_VERSION,
        "selection_seed": SELECTION_SEED,
        "selection_script_version": SELECTION_SCRIPT_VERSION,
        "sampling_date": SAMPLING_DATE,
        "selection_algorithm": (
            "For each domain in [blocksworld, miconic, transport] and difficulty "
            "in [easy, medium, hard], sort filenames lexicographically; derive a "
            "64-bit stratum seed from the first 8 bytes of "
            "SHA256('5102:<domain>:<difficulty>'); use random.Random(seed).sample "
            "without replacement. Blocksworld easy-p03 is included first and nine "
            "other eligible easy problems are sampled. Selected records are sorted "
            "by the declared domain/difficulty order and filename."
        ),
        "python_random_generator": "random.Random (MT19937)",
        "inclusion_exceptions": [
            {
                "domain": "blocksworld",
                "difficulty": "easy",
                "problem_id": "easy-p03",
                "reason": "Predetermined proposal smoke-test instance; sample 9 from the other eligible files.",
            }
        ],
        "selected_domains": list(DOMAINS),
        "candidate_counts": candidate_counts,
        "per_domain_counts": per_domain_counts,
        "total_records": len(records),
        "source_repository": UPSTREAM_REPOSITORY,
        "upstream_commit": UPSTREAM_COMMIT,
    }


def write_selection(
    repository_root: Path,
    source_root: Path,
    selected: list[tuple[str, str, Path]],
    records: list[dict[str, str]],
    candidate_counts: dict[str, int],
) -> None:
    testing_root = repository_root / "benchmarks" / "ipc2023-learning" / "testing"
    for domain in DOMAINS:
        destination = testing_root / domain
        destination.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source_root / "testing" / domain / "domain.pddl", destination / "domain.pddl")

    for domain, _difficulty, problem in selected:
        shutil.copyfile(problem, testing_root / domain / problem.name)

    manifest_dir = repository_root / "benchmarks"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    with (manifest_dir / "manifest.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=RECORD_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(records)

    payload = {"metadata": metadata(records, candidate_counts), "records": records}
    with (manifest_dir / "manifest.json").open("w", encoding="utf-8", newline="\n") as stream:
        json.dump(payload, stream, indent=2, ensure_ascii=False)
        stream.write("\n")


def parse_args() -> argparse.Namespace:
    repository_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-root",
        type=Path,
        required=True,
        help="Path to the upstream benchmarks/ipc2023-learning directory at the recorded commit.",
    )
    parser.add_argument("--repository-root", type=Path, default=repository_root)
    parser.add_argument("--write", action="store_true", help="Copy files and write both manifests.")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Allow replacement of an existing frozen manifest (requires --write).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source_root = args.source_root.resolve()
    repository_root = args.repository_root.resolve()
    manifests = [repository_root / "benchmarks" / f"manifest.{ext}" for ext in ("csv", "json")]

    if args.force and not args.write:
        raise SystemExit("--force is only valid together with --write")
    if args.write and not args.force and any(path.exists() for path in manifests):
        raise SystemExit(
            "frozen manifest already exists; inspect the proposed selection, then use --write --force explicitly"
        )

    selected, candidate_counts = select(source_root)
    records = build_records(selected, source_root)
    print("\n".join(row["relative_problem_path"] for row in records))
    print(f"Selected {len(records)} problems with seed {SELECTION_SEED}.")
    if args.write:
        write_selection(repository_root, source_root, selected, records, candidate_counts)
        print(f"Wrote benchmark {BENCHMARK_VERSION} under {repository_root}.")
    else:
        print("Dry run only; pass --write to create files and manifests.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
