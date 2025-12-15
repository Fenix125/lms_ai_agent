from __future__ import annotations

import asyncio
import threading
import uuid
from dataclasses import dataclass
from typing import Any, Optional, Tuple
import sys
from pathlib import Path

#ensuring repo root is on sys.path so 'agent' package is importable when Streamlit runs from ui/
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent.config import Settings
from agent.stagehand_client import init_stagehand, close_stagehand
from agent.auth import login
from agent.agent_factory import build_agent


class AsyncRunner:
    def __init__(self) -> None:
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def _run_loop(self) -> None:
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    def run(self, coro):
        fut = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return fut.result()

    def close(self) -> None:
        self._loop.call_soon_threadsafe(self._loop.stop)


@dataclass
class AgentSession:
    runner: AsyncRunner
    agent: Optional[Any] = None
    started: bool = False
    session_id: str = ""

    def ensure_started(self, ui_username: str, ui_password: str, show_realtime: bool) -> Tuple[bool, Optional[str]]:
        if self.started and self.agent is not None:
            return True, None

        cfg = Settings(
            lms_username=ui_username,
            lms_password=ui_password,
            show_realtime=show_realtime,
        )

        async def _start():
            await init_stagehand(cfg)
            ok, err = await login(cfg)
            if not ok:
                raise ValueError(err or "Login failed.")
            self.agent = build_agent(cfg) 
            self.session_id = f"ui:{uuid.uuid4()}"

        try:
            self.runner.run(_start())
            self.started = True
            return True, None
        except Exception as e:
            try:
                self.runner.run(close_stagehand())
            except Exception:
                pass
            self.started = False
            self.agent = None
            return False, str(e)

    def ask(self, text: str) -> str:
        if not self.started or self.agent is None:
            return "Agent is not started."

        async def _ask():
            res = await self.agent.ainvoke(
                {"input": text},
                config={"configurable": {"session_id": self.session_id}},
            )
            return res["output"] if isinstance(res, dict) and "output" in res else str(res)

        return self.runner.run(_ask())

    def stop(self) -> None:
        async def _stop():
            await close_stagehand()

        try:
            self.runner.run(_stop())
        finally:
            self.started = False
            self.agent = None
