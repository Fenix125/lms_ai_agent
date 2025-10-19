import os
import re
import asyncio
import uuid
from dotenv import load_dotenv
from stagehand import Stagehand, StagehandConfig
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.chat_history import InMemoryChatMessageHistory, BaseChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain.agents import create_tool_calling_agent, AgentExecutor

load_dotenv()

async def get_config():
    cfg = StagehandConfig(
        env="LOCAL", #can be BROWSERBASE
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
        "If a user asks a general question that doesn't match either tool, provide a neutral response."
        "If a user asks anything related to web-search use the provided tools to navigate, observe, act, and extract data."
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
    tools = [navigate_tool, act_tool, observe_tool, extract_tool]

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
        output_messages_key="output"
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
