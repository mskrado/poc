"""Synthetic task data: believable form input that never touches a real service.

The article mentions a "synthetic task runner that generates believable form data for
testing without hitting real services". This is that generator. Values come from
`fixtures/synth_data/pools.yaml` and are drawn with a seeded PRNG, so a given seed always
produces the same roster.
"""

from __future__ import annotations

import csv
import io
import random
from pathlib import Path
from typing import Any

from browser_benchmark.config import fixtures_root, load_yaml

KINDS = ("contacts", "invoices", "leads", "tickets", "filers")


def load_pools(root: Path | None = None) -> dict[str, Any]:
    return load_yaml(fixtures_root(root) / "synth_data" / "pools.yaml")


def _person(rng: random.Random, pools: dict[str, Any]) -> dict[str, str]:
    first = rng.choice(pools["first_names"])
    last = rng.choice(pools["last_names"])
    place = rng.choice(pools["cities"])
    return {
        "first_name": first,
        "last_name": last,
        "email": f"{first}.{last}@{rng.choice(pools['email_domains'])}".lower(),
        "phone": f"555-{rng.randint(100, 999)}-{rng.randint(1000, 9999)}",
        "street": f"{rng.randint(100, 9899)} {rng.choice(pools['streets'])}",
        "city": place["city"],
        "state": place["state"],
        "zip": place["zip"],
        "company": rng.choice(pools["companies"]),
    }


def generate(kind: str, rows: int = 50, *, seed: int = 20260101, root: Path | None = None) -> list[dict[str, Any]]:
    """Generate `rows` synthetic records of the given kind."""
    if kind not in KINDS:
        raise ValueError(f"unknown synth data kind: {kind} (expected one of {', '.join(KINDS)})")
    pools = load_pools(root)
    rng = random.Random(f"{kind}:{seed}")

    records: list[dict[str, Any]] = []
    for index in range(rows):
        person = _person(rng, pools)
        if kind == "contacts":
            records.append(
                {
                    "full_name": f"{person['first_name']} {person['last_name']}",
                    "email": person["email"],
                    "company": person["company"],
                    "title": rng.choice(["Engineer", "Operations Lead", "Controller", "Founder"]),
                    "city": person["city"],
                }
            )
        elif kind == "invoices":
            period = pools["invoice_periods"][index % len(pools["invoice_periods"])]
            records.append(
                {
                    "invoice_id": f"INV-{2000 + index}",
                    "period": period,
                    "vendor": person["company"],
                    "amount_usd": round(rng.uniform(80, 4200), 2),
                    "status": rng.choice(["paid", "open", "pending"]),
                }
            )
        elif kind == "leads":
            records.append(
                {
                    "full_name": f"{person['first_name']} {person['last_name']}",
                    "email": person["email"],
                    "company": person["company"],
                    "source": rng.choice(pools["lead_sources"]),
                    "score": rng.randint(1, 100),
                }
            )
        elif kind == "tickets":
            records.append(
                {
                    "ticket_id": f"TCK-{4000 + index}",
                    "summary": rng.choice(
                        [
                            "Export fails on large accounts",
                            "Webhook retries duplicate",
                            "Slow dashboard load",
                            "Invoice PDF missing tax line",
                        ]
                    ),
                    "priority": rng.choice(pools["ticket_priorities"]),
                    "reporter": person["email"],
                    "status": rng.choice(["open", "triaged", "in_progress"]),
                }
            )
        else:  # filers
            card = rng.choice(pools["test_cards"])
            records.append(
                {
                    "legal_name": f"{person['first_name']} {person['last_name']}",
                    "entity_type": rng.choice(pools["entity_types"]),
                    "tax_id": f"{rng.randint(10, 99)}-{rng.randint(1000000, 9999999)}",
                    "naics": rng.choice(pools["naics_codes"]),
                    "street": person["street"],
                    "city": person["city"],
                    "state": person["state"],
                    "zip": person["zip"],
                    "card_brand": card["brand"],
                    "card_number": card["number"],
                }
            )
    return records


def to_csv(records: list[dict[str, Any]]) -> str:
    if not records:
        return ""
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(records[0].keys()), lineterminator="\n")
    writer.writeheader()
    writer.writerows(records)
    return buffer.getvalue()


def write_csv(kind: str, path: Path, rows: int = 50, *, seed: int = 20260101) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(to_csv(generate(kind, rows, seed=seed)), encoding="utf-8")
    return path
