"""Browser-Use adapter — hook points only.

Live sketch (from the article's harness):

    from browser_use import Agent
    from langchain_openai import ChatOpenAI

    agent = Agent(
        task=task.goal,
        llm=ChatOpenAI(model="gpt-4o"),
        max_actions_per_step=10,
        generate_gif=False,
    )
    result = await agent.run(max_steps=30)
"""

from __future__ import annotations

from browser_benchmark.frameworks.base import FrameworkAdapter, LiveModeUnavailable
from browser_benchmark.models import RunResult, Task


class BrowserUseAdapter(FrameworkAdapter):
    """DOM-based and fast, but generates far more actions per task than the others."""

    async def run_task(self, task: Task) -> RunResult:
        live = self.config.live
        raise LiveModeUnavailable(
            "browser_use live mode is not wired in this POC. "
            f"Hook point: `browser_use.Agent(task=..., llm=ChatOpenAI(model='{self.config.model}'), "
            f"max_actions_per_step={live.get('max_actions_per_step', 10)}).run("
            f"max_steps={self.config.max_steps})`. "
            f"Install with `pip install -e '.[live]'` and run with --mode mock until then. "
            f"(task: {task.id})"
        )
