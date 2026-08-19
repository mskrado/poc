from voice_benchmark.config import load_patient_list, load_scenario, load_stack_config, list_stack_names


def test_load_scenario():
    scenario = load_scenario()
    assert scenario["name"] == "appointment_confirmation"
    assert "system_prompt" in scenario


def test_load_patients():
    patients = load_patient_list()
    assert len(patients) >= 3
    assert patients[0].persona in {"cooperative", "rescheduler", "confused", "wants_human"}


def test_stack_configs_exist():
    names = list_stack_names()
    assert "vapi" in names
    assert "mock" in names
    vapi = load_stack_config("vapi")
    assert vapi.reference is not None
    assert vapi.reference.p95_turn_latency_ms == 380
