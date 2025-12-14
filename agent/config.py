from __future__ import annotations

import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


def require(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required env var: {name}")
    return value


@dataclass(frozen=True)
class Settings:
    lms_base_url: str = "https://learn.ucu.edu.ua"
    lms_username: str = require("LMS_USERNAME")
    lms_password: str = require("LMS_PASSWORD")

    browserbase_api_key: str = require("BROWSERBASE_API_KEY")
    browserbase_project_id: str = require("BROWSERBASE_PROJECT_ID")
    stagehand_env: str = os.getenv("STAGEHAND_ENV", "LOCAL")
    stagehand_verbose: int = int(os.getenv("STAGEHAND_VERBOSE", "2"))

    stagehand_model_name: str = os.getenv("STAGEHAND_MODEL_NAME", "openai/gpt-4.1-mini")
    stagehand_model_api_key: str = os.getenv("STAGEHAND_MODEL_API_KEY", os.getenv("OPENAI_API_KEY", ""))

    llm_provider: str = os.getenv("LLM_PROVIDER", "openai").lower()
    llm_temperature: float = float(os.getenv("LLM_TEMPERATURE", "0.4"))

    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    google_api_key: str = os.getenv("GOOGLE_API_KEY", "")
    google_model: str = os.getenv("GOOGLE_MODEL", "gemini-2.5-flash")

    show_real_time: str = os.getenv("STAGEHAND_SHOW_REALTIME", "true")
 