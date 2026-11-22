"""Provenance, schema-conformant result records, and a minimal schema validator.

``jsonschema`` is not a project dependency, so ``validate_record`` implements
exactly the JSON-Schema subset used by ``configs/result.schema.json``
(type, enum, const, pattern, minimum, exclusiveMinimum, minLength, required,
additionalProperties=false, allOf with if/then/else on ``const``).
"""

from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import re
import subprocess
import tomllib
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "configs" / "result.schema.json"
SOURCE_FILES = {
    "a_star": ROOT / "src" / "pyperplan" / "search" / "a_star.py",
    "ida_star": ROOT / "src" / "pyperplan" / "search" / "ida_star.py",
    "gbfs": ROOT / "src" / "pyperplan" / "search" / "gbfs.py",
    "relaxation": ROOT / "src" / "pyperplan" / "heuristics" / "relaxation.py",
    "search_adapters": ROOT / "experiments" / "search_algorithms" / "search_adapters.py",
    "search_worker": ROOT / "experiments" / "search_algorithms" / "search_worker.py",
    "run_with_limits_windows": ROOT / "experiments" / "search_algorithms" / "run_with_limits_windows.py",
}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout


def provenance() -> dict:
    """Git revision, dirty flag, combined source hash, config and machine IDs."""
    with (ROOT / "configs" / "experiment.v2.toml").open("rb") as stream:
        config = tomllib.load(stream)
    spec = importlib.util.spec_from_file_location(
        "aicc5102_machine_profile", ROOT / "tools" / "capture_machine_profile.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    profile = module.build_profile()
    hashes = {name: sha256_file(path) for name, path in SOURCE_FILES.items()}
    combined = hashlib.sha256(
        "\n".join(f"{name}:{digest}" for name, digest in sorted(hashes.items())).encode()
    ).hexdigest()
    return {
        "config": config,
        "profile": profile,
        "git_commit": _git("rev-parse", "HEAD").strip(),
        "git_worktree_dirty": bool(_git("status", "--porcelain").strip()),
        "source_hashes": hashes,
        "source_bundle_sha256": combined,
    }


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def derive_seed(base_seed: int, *fields: object) -> int:
    """Protocol seed: SHA-256 of base seed and canonical fields (never hash())."""
    text = ":".join([str(base_seed), *(str(field) for field in fields)])
    return int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:8], 16)


def load_manifest() -> list[dict]:
    manifest = json.loads((ROOT / "benchmarks" / "manifest.json").read_text(encoding="utf-8"))
    return manifest["records"]


def load_schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


_TYPES = {
    "string": lambda v: isinstance(v, str),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "boolean": lambda v: isinstance(v, bool),
    "null": lambda v: v is None,
}


def _check_property(name: str, value, spec: dict) -> list[str]:
    errors = []
    if "type" in spec:
        types = spec["type"] if isinstance(spec["type"], list) else [spec["type"]]
        if not any(_TYPES[t](value) for t in types):
            return [f"{name}: {value!r} is not of type {types}"]
    if "const" in spec and value != spec["const"]:
        errors.append(f"{name}: {value!r} != const {spec['const']!r}")
    if "enum" in spec and value not in spec["enum"]:
        errors.append(f"{name}: {value!r} not in enum")
    if value is None:
        return errors
    if "minimum" in spec and isinstance(value, (int, float)) and value < spec["minimum"]:
        errors.append(f"{name}: {value!r} < minimum {spec['minimum']}")
    if (
        "exclusiveMinimum" in spec
        and isinstance(value, (int, float))
        and value <= spec["exclusiveMinimum"]
    ):
        errors.append(f"{name}: {value!r} <= exclusiveMinimum {spec['exclusiveMinimum']}")
    if "minLength" in spec and isinstance(value, str) and len(value) < spec["minLength"]:
        errors.append(f"{name}: shorter than {spec['minLength']}")
    if "pattern" in spec and isinstance(value, str) and not re.search(spec["pattern"], value):
        errors.append(f"{name}: {value!r} does not match {spec['pattern']}")
    return errors


def validate_record(record: dict, schema: dict | None = None) -> list[str]:
    """Return a list of schema violations (empty list = valid)."""
    schema = schema or load_schema()
    errors = [f"missing required field {k}" for k in schema["required"] if k not in record]
    if schema.get("additionalProperties") is False:
        errors += [f"unexpected field {k}" for k in record if k not in schema["properties"]]
    for name, spec in schema["properties"].items():
        if name in record:
            errors += _check_property(name, record[name], spec)
    for clause in schema.get("allOf", []):
        condition = clause["if"]["properties"]
        matches = all(
            record.get(key) == spec.get("const") for key, spec in condition.items()
        )
        branch = clause.get("then" if matches else "else", {})
        for name, spec in branch.get("properties", {}).items():
            if name in record:
                errors += _check_property(name, record[name], spec)
    return errors


def write_csv_new(path: Path, rows: list[dict]) -> None:
    """Write a CSV, refusing to replace an existing file (raw data is immutable)."""
    path = Path(path)
    if path.exists():
        raise FileExistsError(f"refusing to overwrite existing result file {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_json_new(path: Path, payload) -> None:
    path = Path(path)
    if path.exists():
        raise FileExistsError(f"refusing to overwrite existing result file {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8", newline="\n")
