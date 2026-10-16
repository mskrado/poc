# CFO AI Support Payoff Worksheet

Companion to the roiscale.ai article "Klarna's AI Payoff Survived the SEC".
By Av Ledger, Enterprise ROI Desk, roiscale.ai.

A small Excel model that tests an AI customer-service business case: stated denominator
(cost per *resolved* contact), quality cost priced in, and forecast reconciled to a booked figure.

## Files

- `cfo-ai-support-payoff.xlsx`: the worksheet. Sheets: Read me, Inputs (yellow cells, blank), Model (live formulas), Klarna reference.
- `build.py`: regenerates the workbook with openpyxl (`python build.py`; `python build.py example` writes `test.xlsx` with example inputs).

## Formulas

- Cost per resolved contact = (human cost + AI run cost + escalation cost) / (contacts - repeat contacts)
- Quality cost = change in repeat contacts x loaded cost per contact
- Monthly net saving = gross saving - run cost - escalation cost - quality cost
- Payback months = build cost / monthly net saving ("No payback" if net saving <= 0)
- Forecast reconciliation: booked vs forecast saving, gap in %

The Klarna sheet holds only figures Klarna disclosed (press release 27 Feb 2024; SEC response letter 16 Jul 2025).
Build, run and escalation cost were not disclosed, so payback cannot be computed from public data.

Planning aid, not financial advice.
