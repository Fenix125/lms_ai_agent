from __future__ import annotations

from stagehand import Stagehand, StagehandConfig

from agent.config import Settings
from agent.runtime import RUNTIME


async def init_stagehand(cfg: Settings) -> None:
    sh_cfg = StagehandConfig(
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
