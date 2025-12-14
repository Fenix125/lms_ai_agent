from __future__ import annotations

from langchain_core.tools import BaseTool
from agent.runtime import require_page


class ExtractTool(BaseTool):
    name: str = "extract"
    description: str = "Extract structured data from the current page (Stagehand extract)."

    async def _arun(self, instruction: str) -> str:
        page = require_page()
        return await page.extract(instruction)

    def _run(self, instruction: str) -> str:
        raise NotImplementedError("This tool is async-only.")
