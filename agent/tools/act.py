from __future__ import annotations

from langchain_core.tools import BaseTool
from agent.runtime import require_page


class ActTool(BaseTool):
    name: str = "act"
    description: str = "Perform browser actions like clicking and typing (Stagehand act)."

    async def _arun(self, instruction: str) -> str:
        page = require_page()
        result = await page.act(instruction)
        return f"Action result: {result}"

    def _run(self, instruction: str) -> str:
        raise NotImplementedError("This tool is async-only.")
