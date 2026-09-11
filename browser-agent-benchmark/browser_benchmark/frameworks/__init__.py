from __future__ import annotations

from browser_benchmark.config import DEFAULT_SEED
from browser_benchmark.frameworks.base import FrameworkAdapter, LiveModeUnavailable
from browser_benchmark.frameworks.browser_use import BrowserUseAdapter
from browser_benchmark.frameworks.computer_use import ComputerUseAdapter
from browser_benchmark.frameworks.mock import MockAdapter
from browser_benchmark.frameworks.playwright_mcp import PlaywrightMCPAdapter
from browser_benchmark.models import FrameworkConfig

LIVE_ADAPTERS: dict[str, type[FrameworkAdapter]] = {
    "playwright_mcp": PlaywrightMCPAdapter,
    "browser_use": BrowserUseAdapter,
    "computer_use": ComputerUseAdapter,
}

MODES = ("mock", "live")


def get_adapter(
    config: FrameworkConfig,
    *,
    mode: str = "mock",
    seed: int = DEFAULT_SEED,
    correlation: float = 0.0,
) -> FrameworkAdapter:
    if mode not in MODES:
        raise ValueError(f"unknown mode: {mode} (expected one of {', '.join(MODES)})")
    if mode == "mock":
        return MockAdapter(config, seed=seed, correlation=correlation)
    try:
        adapter_cls = LIVE_ADAPTERS[config.adapter]
    except KeyError as exc:
        raise LiveModeUnavailable(f"no live adapter registered for {config.adapter}") from exc
    return adapter_cls(config, seed=seed, correlation=correlation)


__all__ = [
    "BrowserUseAdapter",
    "ComputerUseAdapter",
    "FrameworkAdapter",
    "LiveModeUnavailable",
    "MockAdapter",
    "PlaywrightMCPAdapter",
    "get_adapter",
]
