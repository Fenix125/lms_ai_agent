from __future__ import annotations

import argparse
import asyncio
import uuid
import os

from agent.config import Settings
from agent.stagehand_client import init_stagehand, close_stagehand
from agent.auth import login

from agent.agent_factory import build_agent


async def async_main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", choices=["openai", "google"], default=None, help="Override LLM_PROVIDER")
    args = parser.parse_args()

    cfg = Settings()
    if args.provider:
        os.environ["LLM_PROVIDER"] = args.provider
        cfg = Settings()

    await init_stagehand(cfg)
    try:
        print("Entering LMS...")
        await login(cfg)

        agent = build_agent(cfg)
        session_id = f"cli:{uuid.uuid4()}"

        print("Chat with agent (enter 'exit' to quit)")
        while True:
            user_in = input("> ").strip()
            if user_in.lower() == "exit":
                break
            if not user_in:
                continue

            res = await agent.ainvoke(
                {"input": user_in},
                config={"configurable": {"session_id": session_id}},
            )
            print(res["output"])
    finally:
        await close_stagehand()


def main() -> None:
    asyncio.run(async_main())


if __name__ == "__main__":
    main()