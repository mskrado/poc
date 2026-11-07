# Agent Hire Kit

Local kit for roiscale.ai release v26.10.31, packet PF-20261031-fewer-people-more-agents. Tool first: this directory is the kit. It is not a marketplace listing and not an article.

Mikhail publishes. Zara Nova owns marketplace packaging; this tree does not contain a listing. Each section stays under its author's name. Numbers in one section are not results from another.

| Section | Author | Path |
|---|---|---|
| Contention harness | Rex Circuit | [contention/README.md](contention/README.md) |
| Payback calculator | Av Ledger | [payback/README.md](payback/README.md), [payback/SECTION.md](payback/SECTION.md) |
| Isolation and memory-audit checklist | Dr. Orion Kade | [isolation/checklist.md](isolation/checklist.md) |
| Buyout decision worksheet | Noah Solace | [buyout/worksheet.md](buyout/worksheet.md) |
| Agent job spec | Zara Nova | [job-spec/TEMPLATE.md](job-spec/TEMPLATE.md) |

## Commands

Python 3.9 or newer. No install and no network.

```bash
cd agent-hire-kit
python3 -m contention --out out/run
python3 -m unittest discover -s tests -v
cd payback && python3 -m unittest -v test_payback_calculator.py
```

The payback CLI, from `payback/`:

```bash
python3 payback_calculator.py --exit-cost-per-role 106060.60606060606 --roles-cut 1 --loaded-annual-cost-per-role 180000 --agent-annual-run-cost 24000 --residual-share .2 --residual-staffing-cost 180000 --implementation-cost 12000
```

That example's inputs other than the exit-cost proxy are illustrative, not measured agent savings. HubSpot's October 6, 2026 Form 8-K is an exit-cost reference only. HubSpot expressly says the restructuring was not driven by AI-related efficiencies. See [payback/README.md](payback/README.md).

## File map

```
agent-hire-kit/
  README.md                          kit index, commands, file map
  LICENSE
  pyproject.toml
  contention/                        Rex Circuit, runnable harness
    README.md                        what the harness measures and does not
    __init__.py
    __main__.py
    banner.py
    cli.py
    contract.py                      independent schedule contract
    memory.py                        scoped-memory probe (fixture only)
    replay.py                        replay one task and the ledger from the log
    report.py                        assertions, CSV, JSONL
    schedule.py
    tasks.py
    workspace.py                     path jail, grants, private memory paths
  fixtures/
    tasks.json                       10 invented SKUs, SYN-01 through SYN-10
    FIXTURE.txt
  tests/
    test_workspace.py
    test_schedule.py
    test_cli.py
    test_sections.py                 caveat and source checks for every section
  payback/                           Av Ledger, unchanged calculator and 11 acceptance tests
    payback_calculator.py
    test_payback_calculator.py
    README.md
    SECTION.md
  isolation/
    checklist.md                     Dr. Orion Kade
  buyout/
    worksheet.md                     Noah Solace
  job-spec/
    TEMPLATE.md                      Zara Nova
```

Harness artifacts (`events.jsonl`, `tasks.csv`, `summary.csv`, `summary.json`, `run.log`) are produced by `python3 -m contention`. They are not checked in.

## Caveats that travel with the kit

- **Contention harness.** SYNTHETIC CONTENTION SIMULATION. Scripted workers, not ten AI agents. No human cleanup was measured. Fixture checks inspired by isolation checklist items 3 and 5 cover simulation fixtures only. They are not proof of production AI memory isolation, credential isolation, or a security certification.
- **Payback.** Av's model outputs on illustrative inputs, not a deployment benchmark. The HubSpot charge range is an exit-cost proxy. The filing says the change was not driven by AI efficiencies.
- **Isolation checklist.** A design checklist, not a benchmark. It has not been measured against a production fleet.
- **Buyout worksheet.** Templates, not legal advice. The Microsoft example is US standard severance of up to 39 weeks of base pay depending on level and tenure. This kit does not claim that offer reflects agent replacement. The worksheet's figures are the author's sources, not findings from the contention harness.
- **Job spec.** A blank line means the agent is not ready to start. This file is not a listing.

## License

MIT. See [LICENSE](LICENSE).
