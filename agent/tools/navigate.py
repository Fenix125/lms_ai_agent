from __future__ import annotations

from langchain_core.tools import BaseTool
from agent.runtime import require_page


class NavigateTool(BaseTool):
    name: str = "navigate"
    description: str = "Navigate to a specific URL inside learn.ucu.edu.ua."

    async def _arun(self, url: str) -> str:
        page = require_page()
        await page.goto(url)
        return f"Navigated to {url}"

    def _run(self, url: str) -> str:
        raise NotImplementedError("This tool is async-only.")
