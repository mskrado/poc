# Agent Isolation and Memory-Audit Checklist
*Section for The Agent Hire Kit. Owner: Dr. Orion Kade, Production Architecture Desk.*

Run this before an agent takes over work a person did. Each item is pass or fail. One fail means the agent is not ready to replace the reviewer.

1. **Own identity.** The agent has its own credential, not a shared service account or a person's token. Test: revoke it and confirm only this agent stops.
2. **Least privilege.** Every tool the agent can call is listed with its scope, and write or delete actions need a separate grant. Test: call one unlisted tool and confirm it is refused. (OWASP LLM06:2025 Excessive Agency.)
3. **Scoped memory.** The agent's memory store is private to it and to one tenant. Test: write a marker from agent A and confirm agent B cannot read it.
4. **Memory provenance.** Every memory entry records its source, author, and time. Test: pick five entries and trace each to its origin. (OWASP Agentic AI Threats and Mitigations, Feb 2025, T1 Memory Poisoning.)
5. **Replayable audit log.** Each action logs the input, tool call, output, model version, and memory entries read. Test: replay one past task from the log alone.
6. **Named exception owner.** A named person owns the queue of the agent's failures, with an alert on the age of the oldest unreviewed item. Test: leave one item unreviewed past the limit and confirm someone is paged.
7. **Kill switch and rollback.** One action stops the agent and rolls its memory back to a known checkpoint. Test: run it in staging and time it.

**Limits:** This is a design checklist, not a benchmark. It has not been measured against a production fleet.

**References**
- OWASP GenAI Security Project, *Agentic AI – Threats and Mitigations*, Feb 2025. https://genai.owasp.org/resource/agentic-ai-threats-and-mitigations/
- OWASP, *Top 10 for LLM Applications 2025*, LLM06 Excessive Agency. https://genai.owasp.org/llmrisk/llm062025-excessive-agency/

---

**Kit note.** The contention harness runs fixture tests for checks 3 and 5 only: a scripted worker's marker is unreadable by the next scripted worker, and one task plus the ledger can be replayed from the run log. Those tests cover simulation fixtures only. They are not proof of production AI memory isolation, credential isolation, or a security certification. Checks 1, 2, 4, 6, and 7 are not executed here. This file remains a design checklist, not a benchmark.
