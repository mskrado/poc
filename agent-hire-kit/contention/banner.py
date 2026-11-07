"""Labels that must travel with every run of this harness."""

MODEL_VERSION = "synthetic-scripted-worker-v26.10.31"
SIMULATION = "synthetic_scripted_workers"
RELEASE = "v26.10.31"
PACKET = "PF-20261031-fewer-people-more-agents"
AUTHOR = "Rex Circuit"

BANNER = (
    "SYNTHETIC CONTENTION SIMULATION. "
    "These are scripted workers, not ten AI agents. "
    "No human cleanup was measured. "
    "Do not quote these figures as agent speedup or hours saved."
)

ISOLATION_LIMIT = (
    "Scoped-memory and audit-replay checks cover this simulation's fixtures only. "
    "They are not proof of production AI memory isolation, credential isolation, "
    "or a security certification."
)

NOT_MEASURED = (
    "ten actual AI agents",
    "model quality or latency",
    "human cleanup time",
    "human effort or hours saved",
    "cost, headcount, or a hire decision",
    "production memory isolation",
    "credential isolation",
    "security certification",
)
