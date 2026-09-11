"""Anthropic Computer Use adapter — hook points only.

The only screenshot-based approach in the suite: it sees pixels, not the DOM, which is
why it wins on odd form layouts and loses on anything repetitive.

Live sketch: a Dockerized Chrome on a virtual display, driven by the Anthropic
computer-use tool (screenshot / mouse / keyboard) in a step loop.
"""

from __future__ import annotations

from browser_benchmark.frameworks.base import FrameworkAdapter, LiveModeUnavailable
from browser_benchmark.models import RunResult, Task


class ComputerUseAdapter(FrameworkAdapter):
    """Pixel-level observer: most human-like, slowest, most expensive."""

    async def run_task(self, task: Task) -> RunResult:
        live = self.config.live
        raise LiveModeUnavailable(
            "computer_use live mode is not wired in this POC. "
            f"Hook point: Anthropic computer-use tool loop against model {self.config.model}, "
            f"driving container `{live.get('container', 'chrome-desktop')}` on display "
            f"{live.get('display', ':1')} at {live.get('screen', '1280x800')}. "
            f"Install with `pip install -e '.[live]'` and run with --mode mock until then. "
            f"(task: {task.id})"
        )
