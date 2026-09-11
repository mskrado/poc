"""Playwright MCP adapter — hook points only.

Mock mode is what this POC measures against. This stub records where a live
implementation plugs in so wiring it later does not reshape the harness.

Live sketch (from the article's harness):

    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    params = StdioServerParameters(command="npx", args=["@playwright/mcp@1.1.0", "--headless"])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            # agentic loop, max_steps from config, Anthropic tool use with the MCP tools
"""

from __future__ import annotations

from browser_benchmark.frameworks.base import FrameworkAdapter, LiveModeUnavailable
from browser_benchmark.models import RunResult, Task


class PlaywrightMCPAdapter(FrameworkAdapter):
    """DOM-based: excellent on static HTML, brittle when an SPA re-renders mid-task."""

    async def run_task(self, task: Task) -> RunResult:
        live = self.config.live
        raise LiveModeUnavailable(
            "playwright_mcp live mode is not wired in this POC. "
            f"Hook point: stdio MCP session via `{live.get('command', 'npx')} "
            f"{' '.join(live.get('args', []))}`, then an Anthropic tool-use loop capped at "
            f"{self.config.max_steps} steps against model {self.config.model}. "
            f"Install with `pip install -e '.[live]'` and run with --mode mock until then. "
            f"(task: {task.id})"
        )
