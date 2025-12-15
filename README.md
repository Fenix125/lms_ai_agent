![Logo of the project](assets/lms_agent.png)

# LMS Agent

LLM-driven agent for the Ukrainian Catholic University Moodle (learn.ucu.edu.ua) browser actions for you.

## What is this project?

-   Chat-first automation assistant for UCU's LMS.
-   Wraps Stagehand browser automation with LangChain tool-calling.
-   Runs locally from the CLI and signs into Moodle with your credentials.

## What it does

-   Navigate Moodle (dashboard, courses, archives) and read data with observe/extract.
-   Perform deterministic actions like clicking buttons, filling forms, and following links.
-   Retrieve grades or course info; supports teacher-gradebook workflows.
-   Upload files or CSVs through Moodle's file picker when requested.
-   Keeps short-term conversation history per session.

> **Important:** The agent executes real actions against `learn.ucu.edu.ua`. Use a test account or proceed carefully in production.

## How it works

-   **Stagehand client** (`agent/stagehand_client.py`): boots a session with Stagehand and exposes `page`/`client` globally via `agent/runtime.py`.
-   **Authentication** (`agent/auth.py`): opens the LMS login page and fills `LMS_USERNAME`/`LMS_PASSWORD` placeholders
-   **LLM + tools** (`agent/chat.py`): builds a LangChain tool-calling agent with `navigate`, `observe`, `act`, `extract`, `upload_file`, and `upload_csv`. The system prompt in `agent/prompt.py` describes the Moodle domain to the agent and outlines important workflows.
-   **History** (`agent/history.py`): stores in-memory chat history per session id.
-   **CLI loop** (`agent/chat.py`): reads user input, routes it through the agent, streams tool calls to Stagehand, and prints the final answer.

## Requirements

-   Python 3.12+.
-   Access to the UCU LMS account you intend to use.
-   Stagehand credentials (API key and project id).
-   An LLM provider key: OpenAI (default) or Google Gemini.

## Setup

1. Create and activate a virtual environment.
    ```bash
    python -m venv .venv
    source .venv/bin/activate  # or .venv\\Scripts\\activate on Windows
    ```
2. Install dependencies.
    ```bash
    pip install -r requirements.txt
    ```
3. Copy the env template and fill it.
    ```bash
    cp .env.example .env
    ```
4. Set the required keys in `.env` (see the config section below). Keep `.env` private.

## Configuration (.env)

| Variable                                        | Purpose / notes                                                   | Default                    |
| ----------------------------------------------- | ----------------------------------------------------------------- | -------------------------- |
| `LMS_USERNAME`, `LMS_PASSWORD`                  | Credentials for `learn.ucu.edu.ua` login.                         | required                   |
| `LMS_BASE_URL`                                  | Base URL of the LMS.                                              | `https://learn.ucu.edu.ua` |
| `BROWSERBASE_API_KEY`, `BROWSERBASE_PROJECT_ID` | Keys for the Browserbase project used by Stagehand.               | optional                   |
| `STAGEHAND_ENV`                                 | Stagehand environment (`LOCAL` by default).                       | `LOCAL`                    |
| `STAGEHAND_VERBOSE`                             | Verbosity level for Stagehand logs.                               | `2`                        |
| `STAGEHAND_MODEL_NAME`                          | Model Stagehand uses for browser reasoning.                       | `openai/gpt-4.1-mini`      |
| `STAGEHAND_MODEL_API_KEY`                       | API key for the Stagehand model (falls back to `OPENAI_API_KEY`). | empty                      |
| `LLM_PROVIDER`                                  | `openai` or `google`.                                             | `openai`                   |
| `LLM_TEMPERATURE`                               | Sampling temperature for the chat model.                          | `0.4`                      |
| `OPENAI_API_KEY`, `OPENAI_MODEL`                | OpenAI key and model when `LLM_PROVIDER=openai`.                  | model: `gpt-4o-mini`       |
| `GOOGLE_API_KEY`, `GOOGLE_MODEL`                | Google key and model when `LLM_PROVIDER=google`.                  | model: `gemini-2.5-flash`  |

> **Note:** `agent/config.py` calls `require(...)`, so the required fields must be set before running or the app will exit. If you want to omit
> something change it there

## Running the agent

-   Start the CLI chat (OpenAI by default):
    ```bash
    python -m agent.chat
    ```
-   After startup the agent logs into the LMS automatically, then waits for your prompts. Type `exit` to quit; Stagehand will close the browser session on shutdown.

## Links

-   Repository: https://github.com/Fenix125/lms_ai_agent
-   Frameworks/Libraries: [Stagehand](https://www.stagehand.dev), [Browserbase](https://www.browserbase.com), [LangChain](https://www.langchain.com), [Playwright](https://playwright.dev/python/)

## License

The code in this project is licensed under the MIT License. See 'LICENSE' for details.
