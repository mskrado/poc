from voice_benchmark.models import PatientRecord
from voice_benchmark.synth_caller.patient_agent import PatientAgent


def test_cooperative_persona_script():
    agent = PatientAgent()
    patient = PatientRecord("Maria", "+15555550101", "cooperative", "2026-03-12 09:00")
    agent.reset("call-1")
    replies = [agent.respond(patient, "call-1") for _ in range(4)]
    assert replies[0].text == "Hello?"
    assert replies[-1].end_call is True


def test_wants_human_interrupts():
    agent = PatientAgent()
    patient = PatientRecord("Robert", "+15555550104", "wants_human", "2026-03-13 15:00")
    agent.reset("call-2")
    r1 = agent.respond(patient, "call-2")
    r2 = agent.respond(patient, "call-2")
    assert r2.interrupt is True
