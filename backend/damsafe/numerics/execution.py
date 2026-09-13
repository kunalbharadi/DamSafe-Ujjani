"""Bounded, cancellable subprocess execution. No user-supplied command strings."""

import hashlib
import json
import os
import subprocess
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import psutil


@dataclass(frozen=True)
class Limits:
    timeout_seconds: float = 600
    memory_mb: int = 2048
    cpus: int = 2
    output_bytes: int = 1_000_000_000
    log_bytes: int = 8_000_000


def sha256(path):
    with Path(path).open("rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


def within(root: Path, name: str) -> Path:
    p = (root / name).resolve()
    if not p.is_relative_to(root.resolve()) or p == root.resolve():
        raise ValueError("Path must stay inside the run directory")
    return p


def execute(
    argv: list[str],
    cwd: Path,
    log: Path,
    limits: Limits,
    cancelled: Callable[[], bool] = lambda: False,
    on_progress: Callable[[dict], None] = lambda _: None,
    container_name: str | None = None,
) -> dict:
    """argv is constructed by trusted adapters. Tests use a labelled process harness."""
    if not argv or any(not isinstance(a, str) or "\x00" in a for a in argv):
        raise ValueError("Invalid argument array")
    started = time.monotonic()
    log.parent.mkdir(parents=True, exist_ok=True)
    if cancelled():
        return {"state": "CANCELLED", "exit_code": None, "elapsed_seconds": 0}
    env = {**os.environ, "OMP_NUM_THREADS": str(limits.cpus), "OPENBLAS_NUM_THREADS": "1"}
    try:
        proc = subprocess.Popen(
            argv,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            env=env,
            shell=False,
        )
    except OSError as e:
        return {
            "state": "FAILED",
            "error": f"Executable unavailable: {e}",
            "exit_code": None,
            "elapsed_seconds": time.monotonic() - started,
        }
    overflow = threading.Event()
    last = {"line": ""}

    def consume():
        count = 0
        with log.open("wb") as out:
            while chunk := proc.stdout.read(4096):
                if count < limits.log_bytes:
                    out.write(chunk[: limits.log_bytes - count])
                    out.flush()
                count += len(chunk)
                last["line"] = chunk[-500:].decode("utf-8", errors="replace")
                if count > limits.log_bytes:
                    overflow.set()

    reader = threading.Thread(target=consume, daemon=True)
    reader.start()
    state, error, peak_rss = "RUNNING", None, 0
    try:
        while proc.poll() is None:
            elapsed = time.monotonic() - started
            if cancelled():
                state, error = "CANCELLED", "Cancellation requested"
            elif elapsed > limits.timeout_seconds:
                state, error = "FAILED", "Wall-time limit exceeded"
            elif overflow.is_set():
                state, error = "FAILED", "Log-size limit exceeded"
            else:
                try:
                    parent = psutil.Process(proc.pid)
                    rss = sum(
                        p.memory_info().rss
                        for p in [parent, *parent.children(recursive=True)]
                        if p.is_running()
                    )
                    peak_rss = max(peak_rss, rss)
                    if rss > limits.memory_mb * 1024 * 1024:
                        state, error = "FAILED", "Process memory limit exceeded"
                except psutil.Error:
                    pass
                total = sum(p.stat().st_size for p in cwd.rglob("*") if p.is_file())
                if total > limits.output_bytes:
                    state, error = "FAILED", "Run-storage limit exceeded"
            on_progress({"elapsed_seconds": elapsed, "log_tail": last["line"]})
            if state != "RUNNING":
                break
            time.sleep(0.2)
    finally:
        if proc.poll() is None:
            if container_name:
                # Only the unique, server-created container for this run is killed.
                subprocess.run(
                    ["docker", "kill", container_name], capture_output=True, timeout=15, check=False
                )
            try:
                parent = psutil.Process(proc.pid)
                for child in parent.children(recursive=True):
                    child.kill()
                parent.kill()
            except psutil.Error:
                pass
        proc.wait(timeout=20)
        reader.join(timeout=5)
        if container_name:
            subprocess.run(
                ["docker", "rm", "-f", container_name], capture_output=True, timeout=15, check=False
            )
    if cancelled():
        state = "CANCELLED"
    elif state == "RUNNING":
        state = "SUCCEEDED" if proc.returncode == 0 and not overflow.is_set() else "FAILED"
    return {
        "state": state,
        "exit_code": proc.returncode,
        "error": error,
        "elapsed_seconds": time.monotonic() - started,
        "launcher_peak_rss_bytes": peak_rss,
        "argv": argv,
        "log_sha256": sha256(log),
    }


def save_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False), encoding="utf-8")
