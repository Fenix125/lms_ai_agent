import os
import re
import asyncio
import uuid
from typing import List
from dotenv import load_dotenv
from stagehand import Stagehand, StagehandConfig
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.chat_history import InMemoryChatMessageHistory, BaseChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_community.callbacks.manager import get_openai_callback
from langchain_openai import ChatOpenAI
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Type

load_dotenv()

TOTAL_PROMPT_TOKENS = 0
TOTAL_COMPLETION_TOKENS = 0
TOTAL_COST = 0.0

async def get_config():
    cfg = StagehandConfig(
        env="LOCAL",
        api_key=os.getenv("BROWSERBASE_API_KEY"),
        project_id=os.getenv("BROWSERBASE_PROJECT_ID"),
        model_name="openai/gpt-4.1-mini",
        model_api_key=os.getenv("OPENAI_API_KEY"),
        verbose=2,
    )
    sh = Stagehand(cfg)
    await sh.init()
    return sh

STAGEHAND = {"client": None, "page": None}
HISTORY_STORE = {}




class NavigateTool(BaseTool):
    name: str = "navigate"
    description: str = "Navigate to a specific URL."

    async def _arun(self, url: str):
        page = STAGEHAND["page"]
        await page.goto(url)
        return f"Navigated to {url}"

    def _run(self, url: str):
        raise NotImplementedError("This tool is async-only.")


class ActTool(BaseTool):
    name: str = "act"
    description: str = "Perform browser actions like clicking and typing."

    async def _arun(self, instruction: str):
        page = STAGEHAND["page"]
        result = await page.act(instruction)
        return f"Action result: {result}"

    def _run(self, instruction: str):
        raise NotImplementedError("Sync not supported.")


class ObserveTool(BaseTool):
    name: str = "observe"
    description: str = "Observe the current webpage and look for elements."

    async def _arun(self, goal: str):
        page = STAGEHAND["page"]
        result = await page.observe(goal)
        return result

    def _run(self, goal: str):
        raise NotImplementedError("Sync not supported.")



class ExtractTool(BaseTool):
    name: str = "extract"
    description: str = "Extract structured data from the current page."

    async def _arun(self, instruction: str):
        page = STAGEHAND["page"]
        result = await page.extract(instruction)
        return result

    def _run(self, instruction: str):
        raise NotImplementedError("Sync not supported.")



class UploadFileInput(BaseModel):
    file_path: str = Field(
        ...,
        description="Path to the file to upload"
    )
    selector: str = Field(
        ...,
        description="CSS selector of the file input element"
    )


class UploadFileTool(BaseTool):
    name: str = "upload_file"
    description: str = "Upload a file to an input on the page."
    args_schema: type = UploadFileInput

    async def _arun(self, file_path: str, selector: str):
        page = STAGEHAND["page"]
        try:
            await page.set_input_files(selector, file_path)
            return f"Uploaded '{file_path}' to '{selector}'."
        except Exception as e:
            return f"Upload failed: {e}"

    def _run(self, file_path: str, selector: str):
        raise NotImplementedError("Sync not supported.")
    

class UploadCSVInput(BaseModel):
    file_path: str = Field(..., description="Path to the CSV file to upload")
    selector: str = Field(
        ...,
        description="CSS selector of the <input type='file'> element for grade CSV upload"
    )


class UploadCSVTool(BaseTool):
    name: str = "upload_csv"
    description: str = (
        "Uploads a CSV file for grade import or bulk grading. "
        "Use observe() first to identify the <input type='file'> selector "
        "inside the Gradebook → Import page."
    )
    args_schema: type = UploadCSVInput

    async def _arun(self, file_path: str, selector: str):
        page = STAGEHAND['page']
        try:
            await page.set_input_files(selector, file_path)
            return f"CSV '{file_path}' uploaded into '{selector}'."
        except Exception as e:
            return f"CSV upload failed: {e}"

    def _run(self, *args, **kwargs):
        raise NotImplementedError("Sync not supported.")


# class UploadInput(BaseModel):
#     file_path: str = Field(..., description="Path to the file to upload")


# class UploadFileTool(BaseTool):
#     name: str = "upload_file"
#     description: str = (
#         "Uploads a file to a Moodle assignment submission without interacting with the OS file dialog."
#     )
#     args_schema: Type[BaseModel] = UploadInput
#     coroutine: bool = True

#     def _run(self, *args, **kwargs):
#         raise NotImplementedError("Sync mode not supported. Use async version.")


#     async def _arun(self, file_path: str):
#         page = STAGEHAND["page"]

#         try:
#             # 1. Click Add submission (OK)
#             await page.click("text='Add submission'")

#             # 2. Locate the input (DO NOT CLICK IT)
#             file_inputs = await page.query_selector_all("input[type='file']")
#             if not file_inputs:
#                 return "No <input type='file'> found on the page."

#             # Use first file input
#             selector = "input[type='file']"

#             # 3. Upload the file directly
#             await page.set_input_files(selector, file_path)

#             # 4. Save changes
#             await page.click("text='Save changes'")

#             return f"Uploaded '{file_path}' successfully."
#         except Exception as e:
#             return f"Upload failed: {e}"






def make_agent(llm=None):
    if llm is None:
        llm = ChatOpenAI(
            model="gpt-4.1-mini",
            temperature=0.2,
            api_key=os.getenv("OPENAI_API_KEY"),
        )
    def get_history(session_id: str) -> BaseChatMessageHistory:
        if session_id not in HISTORY_STORE:
            HISTORY_STORE[session_id] = InMemoryChatMessageHistory()
        return HISTORY_STORE[session_id]


    
    system_prompt = (
        "You are a Moodle automation assistant for the Ukrainian Catholic University platform (learn.ucu.edu.ua). "
        "You operate through Stagehand browser tools to help users navigate Moodle, view courses, check grades, "
        "and extract information from the LMS. You must only interact with pages inside learn.ucu.edu.ua.\n\n"

        "=== Moodle Structure (conceptual navigation map) ===\n"
        "Home page (Dashboard): it shows a welcome header, quick access cards, "
        "and a top navigation bar with main buttons:\n"
        " • 'Home' – returns to the dashboard.\n"
        " • 'Dashboard' – opens the user’s personal cabinet (contains profile, grades, calendar, reports, preferences, logout).\n"
        " • 'My courses' – opens the overview of enrolled courses.\n"
        " • 'Course Archive' – opens the list of past or completed courses.\n"
        " • 'Help' – opens help resources.\n\n"
        "Global Gradebook: To view any grade for any course, click the profile icon (top-right corner), "
        "then select 'Grades' from the dropdown menu. A table appears listing all courses with their grades.\n\n"

        "My Courses page (you are on this page after logging in): Opens after pressing 'My courses'. Shows a grid of course cards with course name, instructor, "
        "progress percentage, and a 'View course' button to open that course.\n\n"

        "Course page: Opens after pressing 'View course' on a specific course card. "
        "Contains tabs such as 'Participants', 'Grades', and 'Reports'. "
        "Selecting 'Grades' opens the gradebook for that course.\n\n"


        "Calendar: Accessible by clicking the profile icon, then 'Calendar'. Displays upcoming deadlines and events.\n\n"

        "Archive of Courses: Accessible by pressing 'Course archive' in the top navigation bar. Contains old or completed courses.\n\n"

        "=== Behavior and Safety Rules ===\n"
        "- Assume the user is already authenticated if they are on the home or dashboard page.\n"
        "- Use 'observe' before every act to analyze current environment, "
        "whenever you are **not confident** about what elements are present, what the next step is, "
        "or when the page structure seems unfamiliar. Observation should always come before risky 'act' operations.\n"
        "- Use 'act' only for safe, deterministic interactions like pressing 'My courses', 'Grades', or 'Grdebook'.\n"
        "- Use 'extract' for reading data (course titles, progress, grades) after confirming context.\n"
        "- Never attempt to open, navigate, or interact with websites **outside learn.ucu.edu.ua**. "
        "If the user requests an external site, politely refuse and explain that you can only operate inside Moodle.\n"
        "- Do not type sensitive information or credentials unless explicitly instructed by a secure internal tool.\n"
        "- Be efficient: minimize clicks, confirm each completed action, and return clear summaries of results.\n"
        "- If a user’s question is general or unrelated to Moodle navigation, respond conversationally without using tools.\n"
        "- You can download files LMS by simply clicking on them"
        """
        === Teacher / Assistant Permissions ===
        The user may be a Teacher or Teaching Assistant in Moodle. 
        In this case, additional actions become available:cdk19

        • Access grading for each assignment
        • Open the “Grader report” for the whole course
        • Open “User report”, “Single view”, and “Grade history”
        • Export grades to CSV or Excel
        • Upload a CSV file with grades (“Import” tab inside Gradebook)

        You must support these workflows in addition to student workflows.
        When uploading any file (CSV or assignment files), Moodle uses a File Picker modal.
        The visible “Choose a file...” button is NOT a real <input type="file">.
        You must:

        1. Click the “Choose a file...” button.
        2. Wait for the File Picker modal to appear.
        3. Click “Upload a file”.
        4. Use observe() to locate the REAL <input type='file'> inside the modal.
        5. Call upload_csv (or upload_file) with that selector.
        6. Click “Upload this file”.
        """
        """
        You have an additional tool: upload_file. 
        Use it to attach files inside Moodle, but only after you have used observe to identify the correct file upload element selector (usually an <input type="file">).

        Process for uploading: 
        1. Navigate to the assignment submission page. 
        2. Use act to click "Add submission" button. 
        3. Use act to click "Add file" button. 
        4. Use act to click "Upload a file" button. 
        5. Call the upload_file tool with the file_path and selector you observed. 
        6. After the file is uploaded, use act to click “Save changes” or “Submit assignment” on the main page. 

        Never call upload_file before locating the selector using observe."""
        """
        You have a special tool: upload_csv.

        Use upload_csv ONLY when the user wants to import grades or upload a CSV file.
        Process:

        1. Navigate to the target course.
        2. Open “Grades”.
        3. Open the dropdown menu near "Grader report"
        4. Click “Import”.
        5. Select “CSV file” upload.
        6. Use observe() to find the <input type="file"> element.
        7. Call upload_csv with file_path and selector.
        8. Then click "Upload grades" or “Import”.

        Never call upload_csv without first using observe() to confirm the correct input selector.
        """

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
        NavigateTool(),
        ActTool(),
        ObserveTool(),
        ExtractTool(),
        UploadFileTool(),
        UploadCSVTool()
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
    global TOTAL_PROMPT_TOKENS, TOTAL_COMPLETION_TOKENS, TOTAL_COST

    STAGEHAND["client"] = await get_config()
    STAGEHAND["page"] = STAGEHAND["client"].page

    # agent = make_agent()

    session_id = f"cli:{uuid.uuid4()}"

    print("Entering LMS")
    await entering_lms()

    print("Chat with agent (enter 'exit' to quit)")
    while True:
        prompt = input("> ") or " "
        if prompt == "exit":
            break

        with get_openai_callback() as cb:
            tracked_llm = ChatOpenAI(
                model="gpt-4.1-mini",
                temperature=0.2,
                api_key=os.getenv("OPENAI_API_KEY"),
            ).bind(callbacks=[cb])
            

            agent = make_agent(llm=tracked_llm)

            res = await agent.ainvoke(
                {"input": prompt},
                config={
                    "configurable": {"session_id": session_id},
                    "callbacks": [cb],
                },
            )
        # Per-call output
        print(res["output"])
        print("\n=== Token Usage ===")
        print(f"Prompt tokens:     {cb.prompt_tokens}")
        print(f"Completion tokens: {cb.completion_tokens}")
        print(f"Total tokens:      {cb.total_tokens}")
        print(f"Cost:              ${cb.total_cost:.6f}\n")

        # Accumulate totals
        TOTAL_PROMPT_TOKENS += cb.prompt_tokens
        TOTAL_COMPLETION_TOKENS += cb.completion_tokens
        TOTAL_COST += cb.total_cost

    # Print total cost at end
    print("\n===== SESSION TOTAL COST =====")
    print(f"Total prompt tokens:     {TOTAL_PROMPT_TOKENS}")
    print(f"Total completion tokens: {TOTAL_COMPLETION_TOKENS}")
    print(f"Grand total tokens:      {TOTAL_PROMPT_TOKENS + TOTAL_COMPLETION_TOKENS}")
    print(f"Grand total cost:        ${TOTAL_COST:.6f}")
    print("==============================\n")

    print("Bye!")
    await STAGEHAND["client"].close()

asyncio.run(main())
