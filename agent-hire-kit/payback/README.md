# Payback is a cash-saving test, not an agent-count target

The worked model returns $10,000 net monthly saving and 11.81 months to payback for one role. These are Av’s model outputs, not deployment results.

Agent Hire Kit · PF-20261031-fewer-people-more-agents · v26.10.31

## Formula

Annual baseline equals roles cut multiplied by loaded annual cost per role.
Annual residual human cost equals residual share multiplied by full-workload annual human cost.
Net monthly saving equals annual baseline minus total annual agent run cost minus annual residual human cost, divided by 12.
Upfront cost equals exit cost per role multiplied by roles cut, plus implementation cost.
Payback months equals upfront cost divided by positive net monthly saving. Otherwise the result is **no payback**, represented by JSON null plus a status field.
The 24-month net position equals 24 times net monthly saving, minus upfront cost. A positive saving does not imply payback within that horizon.

## Inputs and scope

Use one currency throughout. Dollar amounts below are USD.

- `exit_cost_per_role`: one-off severance, notice, transition and other exit costs for each eliminated role.
- `roles_cut`: positive integer. Zero roles is outside this replacement model.
- `loaded_annual_cost_per_role`: avoidable annual compensation, benefits and allocated costs per role. Exclude allocations that will remain.
- `agent_annual_run_cost`: annual inference, platform and monitoring costs for the entire replacement scope, not per role.
- `residual_share`: share of the full annual workload still handled by people, between zero and one inclusive.
- `residual_staffing_cost`: annual human cost for that entire workload **at 100% human handling**, before applying the share. This is not an already share-adjusted residual bill. Use replacement staffing rates, including supervision and rework where applicable.
- Alternatively, supply `human_unit_cost` and `annual_units`: loaded cost per human-handled unit and total annual workload before routing. Their product replaces the full-workload staffing cost. Do not combine these modes.
- `implementation_cost`: total one-off integration, training and rollout cost; defaults to zero. Enter a measured estimate rather than relying on that default.

The explicit full-workload convention prevents applying the residual share twice. For fixed minimum staffing or nonlinear queues, this model is insufficient: price those commitments separately before approval.

## Source and worked example

Only source for exit-cost evidence: [HubSpot Form 8-K, signed October 6, 2026, Item 2.05](https://www.sec.gov/Archives/edgar/data/1404655/000119312526414965/d183135d8k.htm), including its incorporated [Exhibit 99.1](https://www.sec.gov/Archives/edgar/data/1404655/000119312526414965/d183135dex991.htm). Opened and checked for this section. The report estimates $65–75 million of charges, primarily future cash expenditures for severance, notice, transition and benefits. The incorporated employee update supplies “nearly 660” employees; the body of the report supplies approximately 7% of workforce, not 660.

**Av’s own derivation:** dividing the estimated $65–75 million by an approximate denominator of 660 gives $98,485–$113,636 per exit, roughly $98,000–$114,000. This is an aggregate charge proxy, not an observed individual severance award. The estimate and denominator are approximate. The incorporated update explicitly says the change is **not driven by AI-related efficiencies**. This model does not claim HubSpot replaced these roles with agents.

For the example, Av uses the charge-range midpoint divided by that approximate denominator: $70,000,000 / 660 = $106,060.61 per exit. Keep the unrounded quotient in the calculation.

| Example input | Value | Evidence status |
|---|---:|---|
| Exit cost per role | $70,000,000 / 660 | Av’s own derivation from the filing and incorporated exhibit |
| Roles cut | 1 | Illustrative input, not a benchmark |
| Loaded annual cost per role | $180,000 | Illustrative input, not a benchmark |
| Agent annual run cost, total scope | $24,000 | Illustrative input, not a benchmark |
| Residual human share | 20% | Illustrative input, not a benchmark |
| Full-workload annual human staffing cost | $180,000 | Illustrative input, not a benchmark |
| One-off implementation | $12,000 | Illustrative input, not a benchmark |

**Av’s model outputs for that example:** upfront cost $118,060.61; annual residual human cost $36,000; net monthly saving $10,000; payback 11.81 months; 24-month net position +$121,939.39.

Sensitivity below holds all other illustrative inputs fixed. These shares are illustrative inputs, not benchmarks; all results are Av’s model outputs.

| Residual share | Net monthly saving | Payback months | 24-month net position |
|---:|---:|---:|---:|
| 5% | $12,250 | 9.64 | $175,939.39 |
| 10% | $11,500 | 10.27 | $157,939.39 |
| 20% | $10,000 | 11.81 | $121,939.39 |
| 30% | $8,500 | 13.89 | $85,939.39 |

## Run and import

Dependency-free Python 3. Run from this directory:

```sh
python3 payback_calculator.py --exit-cost-per-role 106060.60606060606 --roles-cut 1 --loaded-annual-cost-per-role 180000 --agent-annual-run-cost 24000 --residual-share .2 --residual-staffing-cost 180000 --implementation-cost 12000
python3 -m unittest -v test_payback_calculator.py
```

```python
from payback_calculator import calculate_payback
result = calculate_payback(70000000/660, 1, 180000, 24000, .2,
                           residual_staffing_cost=180000,
                           implementation_cost=12000)
```

JSON includes the selected scenario and sensitivity rows. Invalid, negative, nonfinite or conflicting inputs fail explicitly. Internally the model uses unrounded floats; round only for presentation.

## Approval boundary

Assumes immediate, constant savings; all upfront costs paid at the start; unchanged volume, quality and revenue; linear residual costs; and no inflation, discounting, tax, ramp-up or financing effects. It is not a phased cash-flow forecast. Do not double-count monitoring in both agent and human costs. Include retained staff cost once, and count only genuinely avoidable baseline costs.

The source provides an exit-cost proxy, not an agent-performance benchmark. A runnable harness is not proof of production throughput. Measure residual routing, successful outcomes, rework and service levels before using the model for a staffing decision.

Build this calculator into the kit’s approval worksheet. The CFO owns the payback line; Operations validates capacity and service levels; HR validates exit obligations. Approve a measured deployment envelope, not a headcount promise. Mikhail controls publication; these files are a local handoff, not a published listing.
