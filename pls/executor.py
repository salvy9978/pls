"""Command execution module."""

from __future__ import annotations

class ExecutionResult:
    """Execution result record."""
    def __init__(self, exit_code: int, interrupted: bool = False):
        self.exit_code = exit_code
        self.interrupted = interrupted


def run(command: str) -> ExecutionResult:
    """Run a shell command."""
    import os
    import signal
    import subprocess
    import sys

    original_handler = signal.getsignal(signal.SIGINT)

    if sys.platform == "win32":
        cmd_args = ["cmd.exe", "/c", command]
    else:
        shell_exec = os.environ.get("SHELL", "/bin/sh")
        cmd_args = [shell_exec, "-c", command]

    try:
        with subprocess.Popen(
            cmd_args,
            stdout=sys.stdout,
            stderr=sys.stderr,
            stdin=sys.stdin,
        ) as process:
            try:
                exit_code = process.wait()
                return ExecutionResult(exit_code=exit_code)
            except KeyboardInterrupt:
                if process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                return ExecutionResult(exit_code=130, interrupted=True)
    except KeyboardInterrupt:
        return ExecutionResult(exit_code=130, interrupted=True)
    finally:
        signal.signal(signal.SIGINT, original_handler)
