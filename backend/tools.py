import asyncio
import os

from dotenv import load_dotenv
from tavily import TavilyClient

load_dotenv()
client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

MAX_RESULTS = 5


def _search_sync(query: str) -> str:
    """The original synchronous search. Unchanged, just renamed."""
    results = client.search(query=query, max_results=MAX_RESULTS)
    output = []
    for r in results["results"]:
        output.append(f"**{r['title']}**\n{r['content']}\nSource: {r['url']}\n")
    return "\n---\n".join(output)


async def web_search(query: str) -> str:
    """Run the blocking Tavily call on a worker thread.

    TavilyClient is synchronous. Calling it directly from an async node would
    block the event loop, which stalls the SSE generator and defeats the whole
    point of streaming. asyncio.to_thread hands it to the default executor so
    the loop stays free to flush queued events to the client.
    """
    return await asyncio.to_thread(_search_sync, query)
