#!/usr/bin/env python3
"""Emit a privacy-preserving, cross-platform machine profile.

The stable machine ID excludes hostnames, usernames, and timestamps. It is the
first 12 hex digits of SHA-256 over normalized hardware/OS-family fields.
"""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path


def _processor_name() -> str:
    name = platform.processor().strip()
    if name:
        return name
    if sys.platform.startswith("linux"):
        try:
            for line in Path("/proc/cpuinfo").read_text(encoding="utf-8").splitlines():
                if line.lower().startswith("model name"):
                    return line.split(":", 1)[1].strip()
        except OSError:
            pass
    return os.environ.get("PROCESSOR_IDENTIFIER", "unknown").strip() or "unknown"


def _total_memory_mib() -> int | None:
    if sys.platform == "win32":
        class MemoryStatusEx(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong),
                ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]

        status = MemoryStatusEx()
        status.dwLength = ctypes.sizeof(status)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            return round(status.ullTotalPhys / (1024 * 1024))
        return None

    try:
        pages = os.sysconf("SC_PHYS_PAGES")
        page_size = os.sysconf("SC_PAGE_SIZE")
        return round((pages * page_size) / (1024 * 1024))
    except (AttributeError, OSError, ValueError):
        return None


def _recommended_backend() -> str:
    if sys.platform == "win32":
        return "job_object_process_tree"
    if sys.platform.startswith("linux") and Path("/proc").is_dir():
        return "procfs_process_tree"
    return "portable_process_tree_polling"


def build_profile() -> dict[str, object]:
    stable = {
        "os_family": platform.system() or "unknown",
        "architecture": platform.machine() or "unknown",
        "processor": _processor_name(),
        "logical_cpu_count": os.cpu_count() or 1,
        "total_memory_mib": _total_memory_mib(),
    }
    canonical = json.dumps(stable, sort_keys=True, separators=(",", ":")).encode("utf-8")
    machine_id = f"machine-{hashlib.sha256(canonical).hexdigest()[:12]}"
    return {
        "profile_version": "1.0",
        "machine_id": machine_id,
        "captured_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "os_family": stable["os_family"],
        "os_release": platform.release() or "unknown",
        "architecture": stable["architecture"],
        "processor": stable["processor"],
        "logical_cpu_count": stable["logical_cpu_count"],
        "total_memory_mib": stable["total_memory_mib"],
        "python_version": platform.python_version(),
        "recommended_monitor_backend": _recommended_backend(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Optional JSON output path; stdout is always used otherwise.")
    parser.add_argument("--force", action="store_true", help="Replace an existing --output file.")
    args = parser.parse_args()
    if args.force and args.output is None:
        parser.error("--force requires --output")

    payload = json.dumps(build_profile(), indent=2, ensure_ascii=False) + "\n"
    if args.output is None:
        print(payload, end="")
        return 0
    output = args.output.resolve()
    if output.exists() and not args.force:
        raise SystemExit(f"refusing to replace existing machine profile: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(payload, encoding="utf-8", newline="\n")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
