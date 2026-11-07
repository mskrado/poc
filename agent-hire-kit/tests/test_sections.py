import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def text(relative):
    return (ROOT / relative).read_text(encoding="utf-8")


class SectionCaveatTests(unittest.TestCase):
    def test_payback_keeps_hubspot_caveat_and_sources(self):
        readme = text("payback/README.md")
        section = text("payback/SECTION.md")
        for blob in (readme, section):
            self.assertIn("not driven by AI-related efficiencies", blob)
            self.assertIn("illustrative", blob.lower())
        self.assertIn("https://www.sec.gov/Archives/edgar/data/1404655/000119312526414965/d183135d8k.htm", readme)
        self.assertIn("https://www.sec.gov/Archives/edgar/data/1404655/000119312526414965/d183135dex991.htm", readme)
        self.assertIn("not an observed individual severance award", readme)
        self.assertIn("not a deployment benchmark", section)

    def test_isolation_checklist_keeps_sources_and_limits(self):
        blob = text("isolation/checklist.md")
        self.assertIn("Dr. Orion Kade", blob)
        self.assertIn("**Scoped memory.**", blob)
        self.assertIn("**Replayable audit log.**", blob)
        self.assertIn("design checklist, not a benchmark", blob)
        self.assertIn("https://genai.owasp.org/resource/agentic-ai-threats-and-mitigations/", blob)
        self.assertIn("https://genai.owasp.org/llmrisk/llm062025-excessive-agency/", blob)
        self.assertIn("simulation fixtures only", blob)
        self.assertIn("not proof of production AI memory isolation", blob)
        self.assertIn("credential isolation", blob)
        self.assertIn("security certification", blob)

    def test_buyout_keeps_attribution_limits_and_sources(self):
        blob = text("buyout/worksheet.md")
        self.assertIn("Noah Solace", blob)
        self.assertIn("Templates, not legal advice.", blob)
        self.assertIn("39 weeks", blob)
        self.assertIn("depending on level and tenure", blob)
        self.assertIn("does not claim that Microsoft's offer reflects agent replacement", blob)
        self.assertIn("not findings from the contention harness", blob)
        self.assertIn("https://www.bls.gov/news.release/disp.nr0.htm", blob)
        self.assertIn("https://www.bls.gov/news.release/empsit.t12.htm", blob)
        self.assertIn("https://www.eeoc.gov/laws/guidance/qa-understanding-waivers-discrimination-claims-employee-severance-agreements", blob)
        self.assertIn("https://www.businessinsider.com/microsoft-is-offering-buyouts-read-the-memo-2026-10", blob)

    def test_job_spec_is_the_supplied_template(self):
        blob = text("job-spec/TEMPLATE.md")
        self.assertIn("# Agent Job Spec (one page)", blob)
        self.assertIn("If a line stays blank, the agent isn't ready to start.", blob)
        self.assertIn("payback (Av)", blob)
        self.assertIn("readiness checklist (Orion)", blob)
        self.assertIn("buyout worksheet (Noah)", blob)
        self.assertIn("contention test (Rex)", blob)
        self.assertNotIn("marketplace listing", blob.lower())

    def test_harness_readme_labels_the_simulation(self):
        blob = text("contention/README.md")
        self.assertIn("SYNTHETIC CONTENTION SIMULATION", blob)
        self.assertIn("not ten AI agents", blob)
        self.assertIn("No human cleanup was measured", blob)
        self.assertIn("| serial_shared | deterministic | 10 | 0 | 0 | 50 |", blob)
        self.assertIn("| concurrent_shared | deterministic | 10 | 45 | 45 | 23 |", blob)
        self.assertIn("| concurrent_isolated | deterministic | 10 | 0 | 0 | 5 |", blob)
        self.assertIn("scheduler-dependent", blob)
        self.assertIn("not human time", blob.lower())

    def test_kit_readme_links_every_section_and_command(self):
        blob = text("README.md")
        for snippet in (
            "contention/README.md",
            "payback/README.md",
            "payback/SECTION.md",
            "isolation/checklist.md",
            "buyout/worksheet.md",
            "job-spec/TEMPLATE.md",
            "python3 -m contention --out out/run",
            "python3 -m unittest discover -s tests -v",
            "python3 -m unittest -v test_payback_calculator.py",
            "not driven by AI",
            "not ten AI agents",
            "Templates, not legal advice",
            "design checklist, not a benchmark",
        ):
            self.assertIn(snippet, blob)


if __name__ == "__main__":
    unittest.main()
