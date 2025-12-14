from __future__ import annotations

from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI

from agent.config import Settings


def build_llm(cfg: Settings):
    provider = cfg.llm_provider

    if provider == "openai":
        if not cfg.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is required when LLM_PROVIDER=openai")
        return ChatOpenAI(
            model=cfg.openai_model,
            temperature=cfg.llm_temperature,
            api_key=cfg.openai_api_key,
        )

    if provider == "google":
        if not cfg.google_api_key:
            raise RuntimeError("GOOGLE_API_KEY is required when LLM_PROVIDER=google")
        return ChatGoogleGenerativeAI(
            model=cfg.google_model,
            temperature=cfg.llm_temperature,
            google_api_key=cfg.google_api_key,
        )

    raise ValueError(f"Unsupported LLM_PROVIDER: {provider}. Use 'openai' or 'google'.")
