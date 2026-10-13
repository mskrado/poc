"""Live Ollama checks. Skip cleanly when the server is not running."""
import pytest
import requests

from gate.client import HOST, version


def test_ollama_version_when_running():
    try:
        r = requests.get(f"{HOST}/api/version", timeout=2)
        r.raise_for_status()
    except (requests.RequestException, OSError):
        pytest.skip("Ollama is not running")
    assert version()
