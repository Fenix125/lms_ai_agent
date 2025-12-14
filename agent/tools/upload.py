from __future__ import annotations

from typing import Type
from langchain_core.tools import BaseTool
from pydantic import BaseModel

from agent.runtime import require_page
from agent.schemas.upload import UploadFileInput, UploadCSVInput


class UploadFileTool(BaseTool):
    name: str = "upload_file"
    description: str = "Upload a file to an <input type='file'> element on the page."
    args_schema: Type[BaseModel] = UploadFileInput

    async def _arun(self, file_path: str, selector: str) -> str:
        page = require_page()
        try:
            await page.set_input_files(selector, file_path)
            return f"Uploaded '{file_path}' to '{selector}'."
        except Exception as e:
            return f"Upload failed: {e}"

    def _run(self, *args, **kwargs) -> str:
        raise NotImplementedError("This tool is async-only.")


class UploadCSVTool(BaseTool):
    name: str = "upload_csv"
    description: str = (
        "Uploads a CSV file for grade import/bulk grading. "
        "Use observe() first to identify the correct <input type='file'> selector."
    )
    args_schema: Type[BaseModel] = UploadCSVInput

    async def _arun(self, file_path: str, selector: str) -> str:
        page = require_page()
        try:
            await page.set_input_files(selector, file_path)
            return f"CSV '{file_path}' uploaded into '{selector}'."
        except Exception as e:
            return f"CSV upload failed: {e}"

    def _run(self, *args, **kwargs) -> str:
        raise NotImplementedError("This tool is async-only.")
