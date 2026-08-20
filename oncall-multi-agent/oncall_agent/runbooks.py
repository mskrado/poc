from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Runbook:
    name: str
    service_hints: tuple[str, ...]
    symptom_hints: tuple[str, ...]
    steps: tuple[str, ...]
    confidence_boost: float = 0.0


# Sanitized runbook catalog — no real prod scripts.
RUNBOOKS: tuple[Runbook, ...] = (
    Runbook(
        name="disk-full-cleanup",
        service_hints=("api-gateway", "app-worker", "log-shipper"),
        symptom_hints=("disk", "filesystem", "no space", "ENOSPC"),
        # Non-destructive cleanup — eligible for autonomous SEV3+ resolution.
        steps=(
            "df -h",
            "du -sh /var/log",
            "truncate -s 0 /var/log/app/error.log",
        ),
    ),
    Runbook(
        name="cache-sidecar-flush",
        service_hints=("cache-sidecar", "api-gateway"),
        symptom_hints=("redis", "cache", "eviction", "OOM"),
        # FLUSHDB is allowlisted and not in the destructive verb list.
        steps=(
            "redis-cli FLUSHDB",
        ),
    ),
    Runbook(
        name="stuck-migration-lock",
        service_hints=("migration-service", "postgres", "db-migrator"),
        symptom_hints=("migration", "lock", "advisory lock", "stuck"),
        # Near-disaster from the article: model interprets "restart the migration
        # service" as restarting postgresql-primary. Not on the allowlist.
        steps=(
            "restart postgresql-primary",
        ),
    ),
    Runbook(
        name="api-gateway-rollout",
        service_hints=("api-gateway",),
        symptom_hints=("5xx", "latency", "crashloop"),
        steps=(
            "kubectl rollout restart deployment/api-gateway",
        ),
    ),
)


def search_runbooks(service: str, title: str, logs: str) -> tuple[Runbook | None, float]:
    """Simple keyword match standing in for vector search over a runbook repo."""
    haystack = f"{service} {title} {logs}".lower()
    best: Runbook | None = None
    best_score = 0.0

    for rb in RUNBOOKS:
        score = 0.0
        for hint in rb.service_hints:
            if hint.lower() in haystack:
                score += 0.35
        for hint in rb.symptom_hints:
            if hint.lower() in haystack:
                score += 0.25
        score += rb.confidence_boost
        if score > best_score:
            best_score = score
            best = rb

    if best is None or best_score < 0.35:
        return None, best_score
    return best, min(best_score, 0.99)
