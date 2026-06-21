from tavily import TavilyClient
import os
from dotenv import load_dotenv
load_dotenv()
client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

def web_search(query: str) -> str:
    results = client.search(query=query, max_results=5)
    output = []
    for r in results["results"]:
        output.append(f"**{r['title']}**\n{r['content']}\nSource: {r['url']}\n")
    return "\n---\n".join(output)