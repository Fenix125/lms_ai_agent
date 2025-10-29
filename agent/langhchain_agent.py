import os
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

from agent.sys_prompt import SYSTEM_PROMPT


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

# @tool("navigate")
# async def navigate_tool(url: str):
#     """
#     Provide url to navigate to.
#     """
#     page = STAGEHAND["page"]
#     await page.goto(url)
#     return f"Navigated to {url}"

@tool("act")
async def act_tool(instruction: str):
    """
    Perform individual actions on a web page.
    Breaking complex actions into small, single-step actions works best. 
    If you need to orchestrate multi-step flows, use multiple act commands.
    """
    page = STAGEHAND["page"]
    result = await page.act(instruction)
    return f"Action result: {result}"

@tool("observe")
async def observe_tool(goal: str) -> str:
    """
    Allows you to turn any page into a checklist of reliable, executable actions. 
    It discovers key elements, ranks likely next steps, and returns structured 
    actions (selector, method, args) you can run instantly with act or use 
    to precisely target extract.
    """
    page = STAGEHAND["page"]
    preview = await page.observe(goal)
    return f"Observation preview: {preview}"


@tool("extract")
async def extract_tool(instruction: str) -> str:
    """
    Extract tool grabs structured data from a webpage.
    """
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

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_PROMPT),
            MessagesPlaceholder("chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder("agent_scratchpad"),
        ]
    )
    tools = [act_tool, observe_tool, extract_tool]

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
