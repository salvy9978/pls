"""Safety checking module."""

from __future__ import annotations

import re
from enum import Enum


class RiskLevel(Enum):
    """Risk level enumeration."""
    SAFE = "safe"
    CAUTION = "caution"
    DANGEROUS = "dangerous"


class SafetyResult:
    """Safety analysis result."""
    def __init__(self, level: RiskLevel, warnings: list[str]):
        self.level = level
        self.warnings = warnings


_DANGEROUS_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\brm\s+(-[a-zA-Z]*r[a-zA-Z]*\s+|--recursive\s+).*(/|~|\$HOME|\.\.|\" \")"), "recursive delete on sensitive path"),  # pylint: disable=line-too-long
    (re.compile(r"\brm\s+-[a-zA-Z]*rf"), "force recursive delete"),
    (re.compile(r"\bmkfs\b"), "filesystem format — will destroy all data"),
    (re.compile(r"\bdd\s+.*\bof=/dev/"), "raw disk write"),
    (re.compile(r">\s*/dev/sd[a-z]"), "direct write to block device"),
    (re.compile(r":\(\)\s*\{\s*:\|:\s*\&\s*\}\s*;"), "fork bomb"),
    (re.compile(r"\bchmod\s+(-R\s+)?777"), "world-writable permissions"),
    (re.compile(r"\bchown\s+-R\s+.*\s+/\s*$"), "recursive chown on root"),
]

_CAUTION_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bsudo\b"), "elevated privileges"),
    (re.compile(r"\brm\b"), "file deletion"),
    (re.compile(r"\bchmod\b"), "permission change"),
    (re.compile(r"\bchown\b"), "ownership change"),
    (re.compile(r"\|.*\b(bash|sh|zsh)\b"), "piping into shell"),
    (re.compile(r"\bcurl\b.*\|.*\b(bash|sh|sudo)\b"), "remote script execution"),
    (re.compile(r"\bwget\b.*\|.*\b(bash|sh|sudo)\b"), "remote script execution"),
    (re.compile(r"\b>\s*/etc/"), "writing to /etc"),
    (re.compile(r"\bmv\b.*\s+/\s*$"), "moving to root"),
    (re.compile(r"\bkill\s+-9"), "force kill"),
    (re.compile(r"\bpkill\b"), "process kill by pattern"),
    (re.compile(r"\bsystemctl\s+(stop|disable|mask)"), "stopping system service"),
    (re.compile(r"\biptables\b"), "firewall modification"),
]


def analyze(command: str) -> SafetyResult:
    """Analyze a command for dangerous patterns."""
    warnings: list[str] = []
    level = RiskLevel.SAFE

    for pattern, description in _DANGEROUS_PATTERNS:
        if pattern.search(command):
            warnings.append(description)
            level = RiskLevel.DANGEROUS

    if level != RiskLevel.DANGEROUS:
        for pattern, description in _CAUTION_PATTERNS:
            if pattern.search(command):
                warnings.append(description)
                if level == RiskLevel.SAFE:
                    level = RiskLevel.CAUTION

    return SafetyResult(level=level, warnings=warnings)
