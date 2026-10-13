"""Tiny Ollama client: /v1/systemone for gates, /api/chat for the baseline."""
from __future__ import annotations

import os
import time

import requests

HOST = os.environ.get("OLLAMA_HOST_URL", "http://127.0.0.1:11434")


class OllamaError(RuntimeError):
    pass


def version() -> str:
    return requests.get(f"{HOST}/api/version", timeout=10).json()["version"]


def systemone(model: str, state, questions: dict, timeout: int = 600) -> tuple[dict, float]:
    t0 = time.perf_counter()
    r = requests.post(
        f"{HOST}/v1/systemone",
        json={"model": model, "state": state, "questions": questions, "keep_alive": "30m"},
        timeout=timeout,
    )
    wall_ms = (time.perf_counter() - t0) * 1000
    if r.status_code != 200:
        raise OllamaError(f"systemone {r.status_code}: {r.text[:300]}")
    return r.json(), wall_ms


def chat(model: str, messages: list[dict], num_predict: int = 512, timeout: int = 900) -> dict:
    t0 = time.perf_counter()
    r = requests.post(
        f"{HOST}/api/chat",
        json={
            "model": model,
            "messages": messages,
            "stream": False,
            "think": False,
            "keep_alive": "30m",
            "options": {"temperature": 0, "seed": 42, "num_ctx": 4096, "num_predict": num_predict},
        },
        timeout=timeout,
    )
    wall_ms = (time.perf_counter() - t0) * 1000
    if r.status_code != 200:
        raise OllamaError(f"chat {r.status_code}: {r.text[:300]}")
    d = r.json()
    return {
        "content": d["message"]["content"],
        "input_tokens": d.get("prompt_eval_count", 0),
        "output_tokens": d.get("eval_count", 0),
        "wall_ms": wall_ms,
        "truncated": d.get("done_reason") == "length",
    }
