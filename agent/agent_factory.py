from __future__ import annotations

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain.agents import create_tool_calling_agent, AgentExecutor

from agent.config import Settings
from agent.llm import build_llm
from agent.prompt import SYSTEM_PROMPT
from agent.history import get_history

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
        max_iterations=90,
    )

    return RunnableWithMessageHistory(
        executor,
        get_history,
        input_messages_key="input",
        history_messages_key="chat_history",
        output_messages_key="output",
    )
