from __future__ import annotations

from typing import Dict
from langchain_core.chat_history import InMemoryChatMessageHistory, BaseChatMessageHistory

HISTORY_STORE: Dict[str, InMemoryChatMessageHistory] = {}


def get_history(session_id: str) -> BaseChatMessageHistory:
    if session_id not in HISTORY_STORE:
        HISTORY_STORE[session_id] = InMemoryChatMessageHistory()
    return HISTORY_STORE[session_id]
