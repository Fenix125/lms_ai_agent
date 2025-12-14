from __future__ import annotations

from agent.config import Settings
from agent.runtime import require_page


async def login(cfg: Settings) -> None:
    page = require_page()

    await page.goto(f"{cfg.lms_base_url}/login")
    await page.get_by_placeholder("Ім’я входу").fill(cfg.lms_username)
    await page.get_by_placeholder("Пароль").fill(cfg.lms_password)
    await page.get_by_role("button", name="Увійти").click()
