from __future__ import annotations

import argparse
import asyncio
import uuid
import os

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain.agents import create_tool_calling_agent, AgentExecutor

from agent.config import Settings
from agent.llm import build_llm
from agent.prompt import SYSTEM_PROMPT
from agent.history import get_history
from agent.stagehand_client import init_stagehand, close_stagehand
from agent.auth import login

from agent.tools.navigate import NavigateTool
from agent.tools.act import ActTool
from agent.tools.extract import ExtractTool
from agent.tools.observe import ObserveTool
from agent.tools.upload import UploadFileTool, UploadCSVTool


def build_agent(cfg: Settings):
    llm = build_llm(cfg)

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_PROMPT),
            MessagesPlaceholder("chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder("agent_scratchpad"),
        ]
    )

    tools = [
        NavigateTool(),
        ActTool(),
        ObserveTool(),
        ExtractTool(),
        UploadFileTool(),
        UploadCSVTool(),
    ]

    agent = create_tool_calling_agent(llm, tools, prompt)
    executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        return_intermediate_steps=True,
    )

    return RunnableWithMessageHistory(
        executor,
        get_history,
        input_messages_key="input",
        history_messages_key="chat_history",
        output_messages_key="output",
    )


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