from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class Runtime:
    client: Optional[Any] = None
    page: Optional[Any] = None


RUNTIME = Runtime()


def require_page() -> Any:
    if RUNTIME.page is None:
        raise RuntimeError("Stagehand page is not initialized. Call init_stagehand() first.")
    return RUNTIME.page


def require_client() -> Any:
    if RUNTIME.client is None:
        raise RuntimeError("Stagehand client is not initialized. Call init_stagehand() first.")
    return RUNTIME.client
