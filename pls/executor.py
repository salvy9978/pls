from __future__ import annotations

import signal
import subprocess
import sys
from dataclasses import dataclass


@dataclass
class ExecutionResult:
    exit_code: int
    interrupted: bool = False


def run(command: str) -> ExecutionResult:
    original_handler = signal.getsignal(signal.SIGINT)
    process: subprocess.Popen[bytes] | None = None
    try:
        process = subprocess.Popen(
            command,
            shell=True,
            stdout=sys.stdout,
            stderr=sys.stderr,
            stdin=sys.stdin,
        )
        exit_code = process.wait()
        return ExecutionResult(exit_code=exit_code)
    except KeyboardInterrupt:
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
        return ExecutionResult(exit_code=130, interrupted=True)
    finally:
        signal.signal(signal.SIGINT, original_handler)
