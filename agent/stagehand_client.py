from __future__ import annotations


import threading

from stagehand import Stagehand, StagehandConfig

from agent.config import Settings
from agent.runtime import RUNTIME


def disable_stagehand_signal_handlers_if_needed() -> None:
    """
    Streamlit runs code in a ScriptRunner thread, where signal.signal() is not allowed.
    Stagehand registers signal handlers in __init__, so we no-op that method in non-main threads.
    """
    if threading.current_thread() is not threading.main_thread():
        if hasattr(Stagehand, "_register_signal_handlers"):
            Stagehand._register_signal_handlers = lambda self: None  # type: ignore[attr-defined]


async def init_stagehand(cfg: Settings) -> None:
    disable_stagehand_signal_handlers_if_needed()

    show_real_time = True
    if cfg.show_realtime == "yes" or (isinstance(cfg.show_realtime, bool) and cfg.show_realtime is True):
        show_real_time = False

    sh_cfg = StagehandConfig(
        localBrowserLaunchOptions={"headless": show_real_time},
        env=cfg.stagehand_env,
        api_key=cfg.browserbase_api_key,
        project_id=cfg.browserbase_project_id,
        model_name=cfg.stagehand_model_name,
        model_api_key=cfg.stagehand_model_api_key,
        verbose=cfg.stagehand_verbose,
    )

    client = Stagehand(sh_cfg)
    await client.init()

    RUNTIME.client = client
    RUNTIME.page = client.page


async def close_stagehand() -> None:
    if RUNTIME.client is not None:
        await RUNTIME.client.close()
    RUNTIME.client = None
    RUNTIME.page = None
