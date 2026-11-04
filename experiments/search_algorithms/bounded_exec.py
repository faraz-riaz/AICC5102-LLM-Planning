"""Run one search job in a child process under hard time and memory limits.

Stopgap resource guard for Faraz's reference generation and pilots, used
until the shared runner (Amina) provides the official monitor. It runs one
job per child process and does not schedule or define the experiment matrix.

Windows (tested): the child is assigned to a Job Object with
``JOB_OBJECT_LIMIT_JOB_MEMORY`` (hard cap on committed memory of the whole
process tree) and ``KILL_ON_JOB_CLOSE``. Peak memory is read from
``PeakJobMemoryUsed`` (committed bytes). This is the configured
``job_object_process_tree`` backend, but the metric is committed/private memory
rather than the config's ``working_set_sum_bytes``; it is recorded as
``platform_native_process_tree_bytes``. There is a short window between process
creation and job assignment (interpreter start-up) during which the cap is not
yet applied.

POSIX (untested here): ``RLIMIT_AS`` is set in the child; the worker reports
its own peak RSS. Recorded as ``portable_process_tree_polling`` /
``platform_native_process_tree_bytes``.

Time: the worker receives the full budget and stops its search cooperatively
(leaving a small reporting margin). The parent hard-kills the process tree
``hard_kill_grace_s`` seconds after the budget.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORKER = HERE / "search_worker.py"
IS_WINDOWS = os.name == "nt"


@dataclass
class BoundedOutcome:
    worker: dict | None
    exit_code: int | None
    wall_time_s: float
    peak_memory_mib: float | None
    killed_for_time: bool
    monitor_backend: str
    memory_metric: str
    timeout_enforced: bool
    memory_limit_enforced: bool
    stderr_tail: str


if IS_WINDOWS:
    import ctypes
    from ctypes import wintypes

    _kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

    class _IO_COUNTERS(ctypes.Structure):
        _fields_ = [
            (name, ctypes.c_ulonglong)
            for name in (
                "ReadOperationCount",
                "WriteOperationCount",
                "OtherOperationCount",
                "ReadTransferCount",
                "WriteTransferCount",
                "OtherTransferCount",
            )
        ]

    class _BASIC_LIMIT(ctypes.Structure):
        _fields_ = [
            ("PerProcessUserTimeLimit", ctypes.c_longlong),
            ("PerJobUserTimeLimit", ctypes.c_longlong),
            ("LimitFlags", wintypes.DWORD),
            ("MinimumWorkingSetSize", ctypes.c_size_t),
            ("MaximumWorkingSetSize", ctypes.c_size_t),
            ("ActiveProcessLimit", wintypes.DWORD),
            ("Affinity", ctypes.c_size_t),
            ("PriorityClass", wintypes.DWORD),
            ("SchedulingClass", wintypes.DWORD),
        ]

    class _EXTENDED_LIMIT(ctypes.Structure):
        _fields_ = [
            ("BasicLimitInformation", _BASIC_LIMIT),
            ("IoInfo", _IO_COUNTERS),
            ("ProcessMemoryLimit", ctypes.c_size_t),
            ("JobMemoryLimit", ctypes.c_size_t),
            ("PeakProcessMemoryUsed", ctypes.c_size_t),
            ("PeakJobMemoryUsed", ctypes.c_size_t),
        ]

    _JOB_OBJECT_EXTENDED_LIMIT_INFORMATION = 9
    _JOB_OBJECT_LIMIT_JOB_MEMORY = 0x00000200
    _JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000

    _kernel32.CreateJobObjectW.restype = wintypes.HANDLE
    _kernel32.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
    _kernel32.SetInformationJobObject.restype = wintypes.BOOL
    _kernel32.SetInformationJobObject.argtypes = [
        wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD
    ]
    _kernel32.QueryInformationJobObject.restype = wintypes.BOOL
    _kernel32.QueryInformationJobObject.argtypes = [
        wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD, ctypes.c_void_p
    ]
    _kernel32.AssignProcessToJobObject.restype = wintypes.BOOL
    _kernel32.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    _kernel32.TerminateJobObject.restype = wintypes.BOOL
    _kernel32.TerminateJobObject.argtypes = [wintypes.HANDLE, wintypes.UINT]
    _kernel32.CloseHandle.restype = wintypes.BOOL
    _kernel32.CloseHandle.argtypes = [wintypes.HANDLE]

    def _check(ok, what: str) -> None:
        if not ok:
            raise OSError(ctypes.get_last_error(), f"{what} failed")

    class _Job:
        def __init__(self, memory_limit_bytes: int) -> None:
            self.handle = _kernel32.CreateJobObjectW(None, None)
            _check(self.handle, "CreateJobObjectW")
            info = _EXTENDED_LIMIT()
            info.BasicLimitInformation.LimitFlags = (
                _JOB_OBJECT_LIMIT_JOB_MEMORY | _JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
            )
            info.JobMemoryLimit = memory_limit_bytes
            _check(
                _kernel32.SetInformationJobObject(
                    self.handle,
                    _JOB_OBJECT_EXTENDED_LIMIT_INFORMATION,
                    ctypes.byref(info),
                    ctypes.sizeof(info),
                ),
                "SetInformationJobObject",
            )

        def assign(self, process: subprocess.Popen) -> None:
            _check(
                _kernel32.AssignProcessToJobObject(self.handle, int(process._handle)),
                "AssignProcessToJobObject",
            )

        def peak_bytes(self) -> int:
            info = _EXTENDED_LIMIT()
            _check(
                _kernel32.QueryInformationJobObject(
                    self.handle,
                    _JOB_OBJECT_EXTENDED_LIMIT_INFORMATION,
                    ctypes.byref(info),
                    ctypes.sizeof(info),
                    None,
                ),
                "QueryInformationJobObject",
            )
            return int(info.PeakJobMemoryUsed)

        def terminate(self) -> None:
            _kernel32.TerminateJobObject(self.handle, 1)

        def close(self) -> None:
            _kernel32.CloseHandle(self.handle)


def _posix_limit(memory_limit_bytes: int):
    def apply() -> None:
        import resource

        resource.setrlimit(resource.RLIMIT_AS, (memory_limit_bytes, memory_limit_bytes))

    return apply


def run_bounded(
    job: dict,
    *,
    time_limit_s: float,
    memory_limit_mib: int,
    hard_kill_grace_s: float = 10.0,
    hash_seed: int | None = None,
) -> BoundedOutcome:
    """Run ``job`` in ``search_worker.py`` under the given limits.

    ``hash_seed`` sets ``PYTHONHASHSEED`` for the child. Pyperplan's grounding
    and hFF iterate over Python sets of strings, whose order depends on the
    per-process string-hash seed; without a fixed seed, operator order (hence
    GBFS tie-breaking) and hFF values vary between processes.
    """
    env = dict(os.environ)
    if hash_seed is not None:
        if not 0 <= int(hash_seed) <= 4294967295:
            raise ValueError("hash_seed must be in [0, 2**32 - 1]")
        env["PYTHONHASHSEED"] = str(int(hash_seed))
    payload = json.dumps({**job, "time_limit_s": time_limit_s})
    memory_limit_bytes = int(memory_limit_mib) * 1024 * 1024
    command = [sys.executable, "-X", "utf8", str(WORKER)]
    started = time.perf_counter()
    job_object = None
    if IS_WINDOWS:
        job_object = _Job(memory_limit_bytes)
        process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
        )
        job_object.assign(process)
        backend, metric = "job_object_process_tree", "platform_native_process_tree_bytes"
    else:
        process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
            preexec_fn=_posix_limit(memory_limit_bytes),
        )
        backend, metric = "portable_process_tree_polling", "platform_native_process_tree_bytes"

    killed = False
    try:
        stdout, stderr = process.communicate(payload, timeout=time_limit_s + hard_kill_grace_s)
    except subprocess.TimeoutExpired:
        killed = True
        if job_object is not None:
            job_object.terminate()
        else:
            process.kill()
        stdout, stderr = process.communicate()
    wall = time.perf_counter() - started

    peak_mib = None
    if job_object is not None:
        try:
            peak_mib = job_object.peak_bytes() / (1024 * 1024)
        finally:
            job_object.close()

    worker = None
    for line in reversed((stdout or "").strip().splitlines()):
        line = line.strip()
        if line.startswith("{"):
            try:
                worker = json.loads(line)
            except json.JSONDecodeError:
                worker = None
            break
    if peak_mib is None and worker is not None:
        peak_mib = worker.get("self_peak_rss_mib")

    return BoundedOutcome(
        worker=worker,
        exit_code=process.returncode,
        wall_time_s=wall,
        peak_memory_mib=peak_mib,
        killed_for_time=killed,
        monitor_backend=backend,
        memory_metric=metric,
        timeout_enforced=True,
        memory_limit_enforced=True,
        stderr_tail=(stderr or "")[-600:],
    )


def classify(outcome: BoundedOutcome, memory_limit_mib: int) -> tuple[str, str | None]:
    """Map a bounded outcome to a protocol run status (before plan checks).

    Returns ``(status, failure_detail)`` where status is one of ``success``
    candidates ``"solved"`` or a protocol status.
    """
    worker = outcome.worker
    near_cap = (
        outcome.peak_memory_mib is not None
        and outcome.peak_memory_mib >= 0.95 * memory_limit_mib
    )
    if outcome.killed_for_time:
        return "timeout", "hard time limit: process tree killed by parent"
    if worker is None:
        if near_cap:
            return "memory_limit", "process ended without a report at the memory cap"
        return "planner_error", (
            f"worker produced no report (exit {outcome.exit_code}): "
            f"{outcome.stderr_tail.strip()[-300:]}"
        )
    status = worker.get("status")
    detail = worker.get("failure_detail")
    if status == "error" and (
        (detail or "").startswith("MemoryError") or near_cap
    ):
        return "memory_limit", detail or "MemoryError at the memory cap"
    if status == "error":
        return "planner_error", detail
    if status in {"solved", "unsolved", "timeout"}:
        return status, detail
    return "planner_error", f"unexpected worker status {status!r}"
