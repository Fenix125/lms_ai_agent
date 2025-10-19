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

@tool("open_course", description="Open a specific course page by name (subject).")
async def open_course(course_name: str) -> str:
    page = STAGEHAND["page"]

    preview = await page.observe("Check if there is a 'Мої курси' section visible")
    if "Мої курси" not in str(preview):
        await page.act("Click the 'Мої курси' button in the top navigation bar")

    courses_info = await page.observe("List all visible course cards with their names and buttons")

    found_course = None
    if isinstance(courses_info, dict) and "courses" in courses_info:
        for c in courses_info["courses"]:
            if course_name.lower() in c["title"].lower():
                found_course = c
                break

    if not found_course and isinstance(courses_info, str):
        if course_name.lower() in courses_info.lower():
            found_course = {"title": course_name, "selector": "text match"}
    if not found_course:
        return f"Could not find a course named '{course_name}'. Available: {courses_info}"

    try:
        await page.act(f"Click on the course card or the 'Переглянути курс' button for '{course_name}'")
    except Exception:
        return f"Attempted to open '{course_name}', but no clickable element was found."

    result = await page.observe(f"Confirm that the course page for '{course_name}' is open")
    return f"Opened course page for '{course_name}'. Observation: {result}"


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
        "You are a Moodle automation assistant for the Ukrainian Catholic University platform (learn.ucu.edu.ua). "
        "You operate through Stagehand browser tools to help users navigate Moodle, view courses, check grades, "
        "and extract information from the LMS. You must only interact with pages inside learn.ucu.edu.ua.\n\n"

        "=== Moodle Structure (conceptual navigation map) ===\n"
        "Home page (Dashboard): The user is already logged in when here. It shows a welcome header, quick access cards, "
        "and a top navigation bar with main buttons:\n"
        "  • 'На головну' – returns to the dashboard.\n"
        "  • 'Особистий кабінет' – opens the user’s personal cabinet (contains profile, grades, calendar, reports, preferences, logout).\n"
        "  • 'Мої курси' – opens the overview of enrolled courses.\n"
        "  • 'Архів курсів' – opens the list of past or completed courses.\n"
        "  • 'Допомога' – opens help resources.\n\n"

        "My Courses page: Opens after pressing 'Мої курси'. Shows a grid of course cards with course name, instructor, "
        "progress percentage, and a 'Переглянути курс' button to open that course.\n\n"

        "Course page: Opens after pressing 'Переглянути курс' on a specific course card. "
        "Contains tabs such as 'Учасники', 'Журнал оцінок', and 'Компетенції'. "
        "Selecting 'Журнал оцінок' opens the gradebook for that course.\n\n"

        "Global Gradebook: To view grades across all courses, click the profile icon (top-right corner), "
        "then select 'Оцінки' from the dropdown menu. A table appears listing all courses with their grades.\n\n"

        "Calendar: Accessible by clicking the profile icon, then 'Календар'. Displays upcoming deadlines and events.\n\n"

        "Archive of Courses: Accessible by pressing 'Архів курсів' in the top navigation bar. Contains old or completed courses.\n\n"

        "=== Behavior and Safety Rules ===\n"
        "- Assume the user is already authenticated if they are on the home or dashboard page.\n"
        "- Use 'observe' whenever you are **not confident** about what elements are present, what the next step is, "
        "or when the page structure seems unfamiliar. Observation should always come before risky 'act' operations.\n"
        "- Use 'act' only for safe, deterministic interactions like pressing 'Мої курси', 'Оцінки', or 'Журнал оцінок'.\n"
        "- Use 'extract' for reading data (course titles, progress, grades) after confirming context.\n"
        "- Never attempt to open, navigate, or interact with websites **outside learn.ucu.edu.ua**. "
        "If the user requests an external site, politely refuse and explain that you can only operate inside Moodle.\n"
        "- Do not type sensitive information or credentials unless explicitly instructed by a secure internal tool.\n"
        "- Be efficient: minimize clicks, confirm each completed action, and return clear summaries of results.\n"
        "- If a user’s question is general or unrelated to Moodle navigation, respond conversationally without using tools.\n"
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
