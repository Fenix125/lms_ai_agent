import os, asyncio
from dotenv import load_dotenv
from stagehand import Stagehand, StagehandConfig
from pydantic import BaseModel, Field

load_dotenv()

class EthicsInfo(BaseModel):
    section_title: str = Field(..., description="Heading text of the Artificial intelligence section")
    summary: str = Field(..., description="2–3 sentence summary")

async def main():
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
    page = sh.page

    await page.goto("https://en.wikipedia.org/wiki/Artificial_intelligence")
    await page.act("scroll to (or open) the ' Artificial intelligence' section so it is visible")

    info = await page.extract(
        instruction=(
            "From the 'Artificial intelligence' section on top of this page, return the exact section"
            "heading, a concise 2–3 sentence summary in your own words, and "
            "3–5 key topics or concerns mentioned there."
        ),
        schema=EthicsInfo,
        max_output_tokens=400
    )
    print("\n---------------------------", info, "\n---------------------------")

    await sh.close()

asyncio.run(main())
