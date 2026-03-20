from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


class RiskLevel(Enum):
    SAFE = "safe"
    CAUTION = "caution"
    DANGEROUS = "dangerous"


@dataclass
class SafetyResult:
    level: RiskLevel
    warnings: list[str]


_DANGEROUS_PATTERNS: list[tuple[str, str]] = [
    (r"\brm\s+(-[a-zA-Z]*r[a-zA-Z]*\s+|--recursive\s+).*(/|~|\$HOME|\.\.|\" \")", "recursive delete on sensitive path"),
    (r"\brm\s+-[a-zA-Z]*rf", "force recursive delete"),
    (r"\bmkfs\b", "filesystem format — will destroy all data"),
    (r"\bdd\s+.*\bof=/dev/", "raw disk write"),
    (r">\s*/dev/sd[a-z]", "direct write to block device"),
    (r":\(\)\s*\{\s*:\|:\s*&\s*\}\s*;", "fork bomb"),
    (r"\bchmod\s+(-R\s+)?777", "world-writable permissions"),
    (r"\bchown\s+-R\s+.*\s+/\s*$", "recursive chown on root"),
]

_CAUTION_PATTERNS: list[tuple[str, str]] = [
    (r"\bsudo\b", "elevated privileges"),
    (r"\brm\b", "file deletion"),
    (r"\bchmod\b", "permission change"),
    (r"\bchown\b", "ownership change"),
    (r"\|.*\b(bash|sh|zsh)\b", "piping into shell"),
    (r"\bcurl\b.*\|.*\b(bash|sh|sudo)\b", "remote script execution"),
    (r"\bwget\b.*\|.*\b(bash|sh|sudo)\b", "remote script execution"),
    (r"\b>\s*/etc/", "writing to /etc"),
    (r"\bmv\b.*\s+/\s*$", "moving to root"),
    (r"\bkill\s+-9", "force kill"),
    (r"\bpkill\b", "process kill by pattern"),
    (r"\bsystemctl\s+(stop|disable|mask)", "stopping system service"),
    (r"\biptables\b", "firewall modification"),
]


def analyze(command: str) -> SafetyResult:
    warnings: list[str] = []
    level = RiskLevel.SAFE

    for pattern, description in _DANGEROUS_PATTERNS:
        if re.search(pattern, command):
            warnings.append(description)
            level = RiskLevel.DANGEROUS

    if level != RiskLevel.DANGEROUS:
        for pattern, description in _CAUTION_PATTERNS:
            if re.search(pattern, command):
                warnings.append(description)
                if level == RiskLevel.SAFE:
                    level = RiskLevel.CAUTION

    return SafetyResult(level=level, warnings=warnings)
