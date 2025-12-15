from __future__ import annotations

from typing import Optional, Tuple

from agent.config import Settings
from agent.runtime import require_page


async def login(cfg: Settings) -> Tuple[bool, Optional[str]]:
    """
    Perform LMS login. Returns (ok, error_message).
    Streamlit runner expects a tuple; avoid raising so the caller can handle gracefully.
    """
    try:
        page = require_page()
        await page.goto(f"{cfg.lms_base_url}/login")
        await page.get_by_placeholder("Ім’я входу").fill(cfg.lms_username)
        await page.get_by_placeholder("Пароль").fill(cfg.lms_password)
        await page.get_by_role("button", name="Увійти").click()
        return True, None
    except Exception as exc:
        return False, str(exc)
