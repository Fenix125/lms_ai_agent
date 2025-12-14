from __future__ import annotations

from langchain_core.tools import BaseTool
from agent.runtime import require_page


class ObserveTool(BaseTool):
    name: str = "observe"
    description: str = "Observe the current webpage and look for elements (Stagehand observe)."

    async def _arun(self, goal: str) -> str:
        page = require_page()
        return await page.observe(goal)

    def _run(self, goal: str) -> str:
        raise NotImplementedError("This tool is async-only.")
