from langchain.tools import tool
import requests
from bs4 import BeautifulSoup
from tavily import TavilyClient
import os
from dotenv import load_dotenv

load_dotenv()

if not os.getenv("TAVILY_API_KEY"):
    raise RuntimeError("TAVILY_API_KEY is missing. Add it to your .env file.")

tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))


@tool
def web_search(query: str) -> str:
    """Search the web for recent and reliable information on a topic.
    Returns the title, URL and a snippet for each result."""
    results = tavily.search(query=query, max_results=5)

    out = []
    for r in results["results"]:
        out.append(
            f"Title: {r['title']}\n"
            f"URL: {r['url']}\n"
            f"Snippet: {r['content'][:300]}\n"
        )
    return "\n----\n".join(out)


@tool
def web_scrape(url: str) -> str:
    """Scrape a webpage. Input must be a full URL starting with http:// or https://.
    Returns the main readable text of the page, or an error message."""
    if not url.startswith(("http://", "https://")):
        return "Invalid URL: must start with http:// or https://"
    try:
        resp = requests.get(url, timeout=8, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        soup = BeautifulSoup(resp.content, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()
        main = soup.find("article") or soup.find("main") or soup
        return f"SOURCE: {url}\n" + main.get_text(separator="\n", strip=True)[:3000]
    except Exception as e:
        return f"Could not scrape {url}: {e}"