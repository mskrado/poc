import asyncio

import pytest

from browser_benchmark.config import list_framework_names, load_framework_config, load_tasks
from browser_benchmark.frameworks import LiveModeUnavailable, MockAdapter, get_adapter
from browser_benchmark.orchestrator import run_framework


def test_mock_mode_is_the_default_path():
    for name in list_framework_names():
        adapter = get_adapter(load_framework_config(name), mode="mock")
        assert isinstance(adapter, MockAdapter)


def test_live_adapters_refuse_cleanly_and_document_their_hook_point():
    task = load_tasks()[0]
    for name in list_framework_names():
        adapter = get_adapter(load_framework_config(name), mode="live")
        assert not isinstance(adapter, MockAdapter)
        with pytest.raises(LiveModeUnavailable) as excinfo:
            asyncio.run(adapter.run_task(task))
        message = str(excinfo.value)
        assert "not wired" in message
        assert "Hook point" in message
        assert task.id in message


def test_live_mode_surfaces_through_the_orchestrator():
    with pytest.raises(LiveModeUnavailable):
        asyncio.run(run_framework("browser_use", mode="live"))


def test_unknown_mode_is_rejected():
    with pytest.raises(ValueError):
        get_adapter(load_framework_config("browser_use"), mode="headless")
