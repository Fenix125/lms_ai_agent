from __future__ import annotations

from pydantic import BaseModel, Field

class UploadFileInput(BaseModel):
    file_path: str = Field(..., description="Path to the file to upload")
    selector: str = Field(..., description="CSS selector of the <input type='file'> element")


class UploadCSVInput(BaseModel):
    file_path: str = Field(..., description="Path to the CSV file to upload")
    selector: str = Field(..., description="CSS selector of the <input type='file'> element for CSV upload")
