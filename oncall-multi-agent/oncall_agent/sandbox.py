from __future__ import annotations

import re
from dataclasses import dataclass


# From the article: restart / delete / drop / terminate / kill need human confirm.
DESTRUCTIVE_PATTERNS = (
    r"\brestart\b",
    r"\bdelete\b",
    r"\bdrop\b",
    r"\bterminate\b",
    r"\bkill\b",
)

# Commands the sandbox will actually run. Everything else fails closed.
DEFAULT_ALLOWLIST = frozenset(
    {
        "df -h",
        "du -sh /var/log",
        "systemctl restart logrotate",
        "systemctl restart app-worker",
        "docker restart cache-sidecar",
        "redis-cli FLUSHDB",  # scoped flush of cache DB only in demo
        "kubectl rollout restart deployment/api-gateway",
        "truncate -s 0 /var/log/app/error.log",
    }
)


@dataclass(frozen=True)
class SandboxResult:
    allowed: bool
    command: str
    reason: str
    is_destructive: bool = False
    requires_human_confirm: bool = False


def classify_destructive(command: str) -> list[str]:
    """Flag destructive verbs before execution — even inside the sandbox."""
    hits: list[str] = []
    lower = command.lower()
    for pattern in DESTRUCTIVE_PATTERNS:
        if re.search(pattern, lower):
            hits.append(pattern.strip(r"\b"))
    return hits


class RunbookSandbox:
    """
    Sandboxed runbook executor.

    Mirrors the article's near-disaster lesson: no raw shell, no DB access,
    no internet egress — only an explicit command allowlist.
    """

    def __init__(
        self,
        allowlist: frozenset[str] | None = None,
        *,
        require_human_for_destructive: bool = True,
        human_confirmed: bool = False,
    ) -> None:
        self.allowlist = allowlist if allowlist is not None else DEFAULT_ALLOWLIST
        self.require_human_for_destructive = require_human_for_destructive
        self.human_confirmed = human_confirmed

    def check(self, command: str) -> SandboxResult:
        destructive = classify_destructive(command)
        is_destructive = bool(destructive)

        if command not in self.allowlist:
            return SandboxResult(
                allowed=False,
                command=command,
                reason=f"Command not on allowlist: {command!r}",
                is_destructive=is_destructive,
            )

        if (
            is_destructive
            and self.require_human_for_destructive
            and not self.human_confirmed
        ):
            return SandboxResult(
                allowed=False,
                command=command,
                reason=(
                    "Destructive action requires human confirmation: "
                    + ", ".join(destructive)
                ),
                is_destructive=True,
                requires_human_confirm=True,
            )

        return SandboxResult(
            allowed=True,
            command=command,
            reason="Allowlisted",
            is_destructive=is_destructive,
        )

    def execute(self, command: str) -> SandboxResult:
        result = self.check(command)
        return result
