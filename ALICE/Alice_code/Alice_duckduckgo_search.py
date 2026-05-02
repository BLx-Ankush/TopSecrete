import os
import logging
from dotenv import load_dotenv
from datetime import datetime
from langchain.tools import tool
from duckduckgo_search import DDGS

# Load environment variables (kept for other tools)
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@tool
async def duckduckgo_search(query: str) -> str:
    """
    Performs a web search using DuckDuckGo (no API key needed) and returns
    the top 3 results with heading and summary only. Links are omitted to
    keep the response natural for voice.
    """

    logger.info(f"DuckDuckGo query प्राप्त हुई: {query}")

    try:
        with DDGS() as ddg:
            # Fetch concise text results
            results = list(ddg.text(query, max_results=3, safesearch="moderate"))
    except Exception as e:
        logger.error(f"DuckDuckGo search failed: {e}")
        return f"DuckDuckGo search में त्रुटि: {e}"

    if not results:
        logger.info("कोई results नहीं मिले।")
        return "कोई results नहीं मिले।"

    # Create a natural, speech-friendly summary
    formatted = "Here are the top results:\n"
    for i, item in enumerate(results, start=1):
        title = (item.get("title") or "No title").strip()
        snippet = (item.get("body") or item.get("description") or "").strip()
        if snippet:
            formatted += f"{i}. {title}. {snippet}\n\n"
        else:
            formatted += f"{i}. {title}.\n\n"

    return formatted.strip()

@tool
async def get_current_datetime() -> str:
    """
    Returns the current date and time in a human-readable format.

    Use this tool when the user asks for the current time, date, or wants to know what day it is.
    Example prompts:
    - "अब क्या time हो रहा है?"
    - "आज की तारीख क्या है?"
    - "What’s the time right now?"
    """

    now = datetime.now()
    formatted = now.strftime("%d %B %Y, %I:%M %p")  # Example: 31 July 2025, 04:22 PM
    return formatted