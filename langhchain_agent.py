import os
import re
import asyncio
import uuid
from dotenv import load_dotenv
from stagehand import Stagehand, StagehandConfig
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.chat_history import (
    InMemoryChatMessageHistory,
    BaseChatMessageHistory,
)
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain.agents import create_tool_calling_agent, AgentExecutor

load_dotenv()


async def get_config():
    cfg = StagehandConfig(
        env="LOCAL",  # can be BROWSERBASE
        api_key=os.getenv("BROWSERBASE_API_KEY"),
        project_id=os.getenv("BROWSERBASE_PROJECT_ID"),
        model_name="google/gemini-2.5-flash",
        model_api_key=os.getenv("GOOGLE_API_KEY"),
        verbose=2,
    )
    sh = Stagehand(cfg)
    await sh.init()
    return sh


STAGEHAND = {"client": None, "page": None}
HISTORY_STORE = {}


@tool("navigate", description="Navigate to specific URLs")
async def navigate_tool(url: str):
    page = STAGEHAND["page"]
    await page.goto(url)
    return f"Navigated to {url}"


@tool("act", description="Perform browser actions (clicking, typing, etc.)")
async def act_tool(instruction: str):
    page = STAGEHAND["page"]
    result = await page.act(instruction)
    return f"Action result: {result}"


@tool("observe", description="Analyze page elements and possible actions")
async def observe_tool(goal: str) -> str:
    page = STAGEHAND["page"]
    preview = await page.observe(goal)
    return f"Observation preview: {preview}"


@tool("extract", description="Extract structured data using schemas")
async def extract_tool(instruction: str) -> str:
    page = STAGEHAND["page"]
    data = await page.extract(instruction)
    return str(data)


@tool(
    "upload_file", description="Upload a file to the page (handles file input elements)"
)
async def upload_file_tool(file_path: str, selector: str = None) -> str:
    page = STAGEHAND["page"]
    try:
        if not os.path.exists(file_path):
            return f"Error: File not found at {file_path}"

        if selector:
            await page.locator(selector).set_input_files(file_path)
        else:
            await page.locator("input[type='file']").set_input_files(file_path)

        return f"Successfully uploaded file: {file_path}"
    except Exception as e:
        return f"Error uploading file: {str(e)}"


@tool(
    "download_file",
    description="Download a file from the page by clicking a download link",
)
async def download_file_tool(selector: str, download_path: str = "./downloads") -> str:
    page = STAGEHAND["page"]
    try:
        os.makedirs(download_path, exist_ok=True)

        async with page.expect_download() as download_info:
            await page.locator(selector).click()

        download = await download_info.value
        file_path = os.path.join(download_path, download.suggested_filename)
        await download.save_as(file_path)

        return f"Successfully downloaded file to: {file_path}"
    except Exception as e:
        return f"Error downloading file: {str(e)}"


def make_agent():
    def get_history(session_id: str) -> BaseChatMessageHistory:
        if session_id not in HISTORY_STORE:
            HISTORY_STORE[session_id] = InMemoryChatMessageHistory()
        return HISTORY_STORE[session_id]

    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        temperature=0.2,
        api_key=os.getenv("GOOGLE_API_KEY"),
    )

    system_prompt = (
        "You are a web automation agent."
        "Do not leave learn.ucu.edu.ua platform."
        "If a user asks a general question that doesn't match any tool, provide a neutral response."
        "If a user asks anything related to search, file uploads, or downloads, use the provided tools to navigate, observe, act, extract data, and handle files."
        "Be precise and minimize unnecessary steps."
        "Prefer 'observe' to preview before risky 'act' operations."
    )

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            MessagesPlaceholder("chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder("agent_scratchpad"),
        ]
    )
    tools = [
        navigate_tool,
        act_tool,
        observe_tool,
        extract_tool,
        upload_file_tool,
        download_file_tool,
    ]

    agent = create_tool_calling_agent(llm, tools, prompt)

    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        return_intermediate_steps=True,
    )
    agent_executor_history = RunnableWithMessageHistory(
        agent_executor,
        get_history,
        input_messages_key="input",
        history_messages_key="chat_history",
        output_messages_key="output",
    )

    return agent_executor_history


async def entering_lms():
    page = STAGEHAND["page"]

    username = os.getenv("LMS_USERNAME")
    password = os.getenv("LMS_PASSWORD")

    await page.goto("https://learn.ucu.edu.ua/login")

    await page.get_by_placeholder("Ім’я входу").fill(username)

    await page.get_by_placeholder("Пароль").fill(password)

    await page.get_by_role("button", name="Увійти").click()


async def main():
    STAGEHAND["client"] = await get_config()
    STAGEHAND["page"] = STAGEHAND["client"].page

    agent = make_agent()

    session_id = f"cli:{uuid.uuid4()}"

    print("Entering LMS")
    await entering_lms()

    print("Chat with agent (enter 'exit' to quit)")
    while True:
        prompt = input("> ") or " "
        if prompt == "exit":
            break

        res = await agent.ainvoke(
            {"input": prompt},
            config={"configurable": {"session_id": session_id}},
        )
        print(res["output"])

    print("Bye!")
    await STAGEHAND["client"].close()


asyncio.run(main())
