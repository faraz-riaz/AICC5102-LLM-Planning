#!/usr/bin/env python3
"""Verify the frozen benchmark manifest and curated PDDL distribution."""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path


DOMAINS = ("blocksworld", "miconic", "transport")
DIFFICULTIES = ("easy", "medium", "hard")
EXPECTED_COMMIT = "4c3deabc058e3ab181250a742181412507920d18"
EXPECTED_VERSION = "aicc5102-90-v1"
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


def verify(root: Path) -> list[str]:
    errors: list[str] = []
    csv_path = root / "benchmarks" / "manifest.csv"
    json_path = root / "benchmarks" / "manifest.json"
    try:
        payload = json.loads(json_path.read_text(encoding="utf-8"))
        records = payload["records"]
        meta = payload["metadata"]
    except (OSError, KeyError, json.JSONDecodeError) as exc:
        return [f"cannot load {json_path}: {exc}"]

    try:
        with csv_path.open(encoding="utf-8", newline="") as stream:
            reader = csv.DictReader(stream)
            csv_records = list(reader)
            if tuple(reader.fieldnames or ()) != RECORD_FIELDS:
                errors.append(f"CSV columns differ from required schema: {reader.fieldnames}")
    except OSError as exc:
        return errors + [f"cannot load {csv_path}: {exc}"]

    if csv_records != records:
        errors.append("CSV and JSON records are not identical")
    if meta.get("benchmark_version") != EXPECTED_VERSION:
        errors.append(f"unexpected benchmark version: {meta.get('benchmark_version')!r}")
    if meta.get("selection_seed") != 5102:
        errors.append(f"unexpected selection seed: {meta.get('selection_seed')!r}")
    if meta.get("total_records") != 90 or len(records) != 90:
        errors.append(f"expected 90 records, found metadata={meta.get('total_records')} actual={len(records)}")
    if tuple(meta.get("selected_domains", ())) != DOMAINS:
        errors.append(f"selected domains must be exactly {DOMAINS}")

    problem_keys: set[tuple[str, str]] = set()
    relative_paths: set[str] = set()
    problem_hashes: set[str] = set()
    counts: Counter[tuple[str, str]] = Counter()
    expected_pddl_paths: set[Path] = set()

    for index, row in enumerate(records, start=1):
        missing_fields = [field for field in RECORD_FIELDS if not row.get(field)]
        if missing_fields:
            errors.append(f"record {index} has blank required fields: {missing_fields}")
            continue
        domain = row["domain"]
        difficulty = row["difficulty"]
        key = (domain, row["problem_id"])
        if key in problem_keys:
            errors.append(f"duplicate domain/problem_id: {key}")
        problem_keys.add(key)
        if row["relative_problem_path"] in relative_paths:
            errors.append(f"duplicate problem path: {row['relative_problem_path']}")
        relative_paths.add(row["relative_problem_path"])
        if row["sha256_problem"] in problem_hashes:
            errors.append(f"duplicate problem content hash: {row['sha256_problem']}")
        problem_hashes.add(row["sha256_problem"])
        counts[(domain, difficulty)] += 1

        expected_problem = f"benchmarks/ipc2023-learning/testing/{domain}/{row['problem_id']}.pddl"
        expected_domain = f"benchmarks/ipc2023-learning/testing/{domain}/domain.pddl"
        if row["relative_problem_path"] != expected_problem:
            errors.append(f"record {index} has inconsistent problem path")
        if row["relative_domain_path"] != expected_domain:
            errors.append(f"record {index} has inconsistent domain path")
        if row["benchmark_split"] != "test" or "/testing/" not in row["relative_problem_path"]:
            errors.append(f"record {index} is not exclusively in the test split")
        if row["upstream_commit_or_archive_version"] != EXPECTED_COMMIT:
            errors.append(f"record {index} has unexpected upstream version")

        for field, digest_field in (
            ("relative_problem_path", "sha256_problem"),
            ("relative_domain_path", "sha256_domain"),
        ):
            file_path = root / Path(row[field])
            expected_pddl_paths.add(file_path.resolve())
            if not file_path.is_file():
                errors.append(f"missing file: {row[field]}")
            elif sha256(file_path) != row[digest_field]:
                errors.append(f"checksum mismatch: {row[field]}")

    for domain in DOMAINS:
        for difficulty in DIFFICULTIES:
            if counts[(domain, difficulty)] != 10:
                errors.append(
                    f"expected 10 for {domain}/{difficulty}, found {counts[(domain, difficulty)]}"
                )
        if sum(counts[(domain, d)] for d in DIFFICULTIES) != 30:
            errors.append(f"expected 30 selected test problems for {domain}")

    if ("blocksworld", "easy-p03") not in problem_keys:
        errors.append("predetermined inclusion blocksworld/easy-p03 is missing")

    testing_root = root / "benchmarks" / "ipc2023-learning" / "testing"
    actual_pddl_paths = {path.resolve() for path in testing_root.rglob("*.pddl")}
    if actual_pddl_paths != expected_pddl_paths:
        for path in sorted(actual_pddl_paths - expected_pddl_paths):
            errors.append(f"unexpected testing PDDL: {path.relative_to(root)}")
        for path in sorted(expected_pddl_paths - actual_pddl_paths):
            errors.append(f"expected testing PDDL not present: {path.relative_to(root)}")

    training_root = root / "benchmarks" / "ipc2023-learning" / "training"
    training_hashes: set[str] = set()
    for domain in DOMAINS:
        domain_training = training_root / domain
        pddl_count = len(list(domain_training.glob("*.pddl")))
        if pddl_count != 100:
            errors.append(f"expected domain + 99 training PDDL for {domain}, found {pddl_count}")
        if not (domain_training / "domain.pddl").is_file():
            errors.append(f"missing training domain for {domain}")
        for path in domain_training.glob("p*.pddl"):
            training_hashes.add(sha256(path))
    leaked_hashes = problem_hashes & training_hashes
    if leaked_hashes:
        errors.append(f"selected test content duplicates training content ({len(leaked_hashes)} hashes)")

    return errors


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    errors = verify(root)
    if errors:
        print("Benchmark verification FAILED:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("Benchmark verification passed: 90 files, 3 domains, 10 per difficulty/domain, hashes intact.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
