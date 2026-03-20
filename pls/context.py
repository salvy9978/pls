from __future__ import annotations

import os
import platform
import shutil
from pathlib import Path

MAX_FILES_IN_CONTEXT = 50
MAX_FILENAME_LEN = 80


def _detect_shell() -> str:
    shell = os.environ.get("SHELL", "")
    if shell:
        return Path(shell).name
    if platform.system() == "Windows":
        if os.environ.get("PSModulePath"):
            return "powershell"
        return "cmd"
    return "sh"


def _list_cwd_files() -> list[str]:
    try:
        entries = sorted(Path.cwd().iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
        result = []
        for entry in entries[:MAX_FILES_IN_CONTEXT]:
            name = entry.name
            if len(name) > MAX_FILENAME_LEN:
                name = name[:MAX_FILENAME_LEN] + "..."
            suffix = "/" if entry.is_dir() else ""
            result.append(f"{name}{suffix}")
        remaining = len(list(Path.cwd().iterdir())) - MAX_FILES_IN_CONTEXT
        if remaining > 0:
            result.append(f"... and {remaining} more files")
        return result
    except PermissionError:
        return ["(permission denied)"]


def _has_tool(name: str) -> bool:
    return shutil.which(name) is not None


def gather() -> dict[str, str]:
    cwd_files = _list_cwd_files()
    available_tools = [t for t in ["git", "docker", "python3", "node", "cargo", "go"] if _has_tool(t)]

    return {
        "os": f"{platform.system()} {platform.release()}",
        "shell": _detect_shell(),
        "cwd": str(Path.cwd()),
        "files": "\n".join(cwd_files) if cwd_files else "(empty directory)",
        "user": os.environ.get("USER", os.environ.get("USERNAME", "unknown")),
        "tools": ", ".join(available_tools) if available_tools else "none detected",
    }
