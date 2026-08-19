"""Optional webhook listener for live stack turn events (requires `pip install -e '.[live]'`)."""

from __future__ import annotations

from voice_benchmark.metrics.events import parse_turn_events


def create_app(stack: str = "vapi"):
    try:
        from fastapi import FastAPI, Request
    except ImportError as exc:
        raise ImportError(
            "Webhook server requires live extras: pip install -e '.[live]'"
        ) from exc

    app = FastAPI(title="Voice Benchmark Webhook")
    received: list[dict] = []

    @app.post("/webhook/{call_id}")
    async def webhook(call_id: str, request: Request):
        payload = await request.json()
        events = parse_turn_events(payload, call_id=call_id, stack=stack)
        received.append(
            {
                "call_id": call_id,
                "payload": payload,
                "events": [e.event_type.value for e in events],
            }
        )
        return {"ok": True, "parsed": len(events)}

    @app.get("/events")
    async def list_events():
        return received

    return app


def main() -> None:
    import uvicorn

    uvicorn.run(create_app(), host="0.0.0.0", port=8080)


if __name__ == "__main__":
    main()
