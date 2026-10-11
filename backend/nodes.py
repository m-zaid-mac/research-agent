import asyncio

from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
import re
from bedrock import get_llm
from tools import web_search
import os
llm = get_llm()

# Flip to False to go back to one-search-at-a-time.
PARALLEL_SEARCH = True

NUMBERED_SOURCES = os.getenv("NUMBERED_SOURCES", "0") == "1"

NUMBERED_ANALYST_PROMPT = (
    "You are a research analyst. Based on the following research gathered on\n"
    "{topic}, write a comprehensive, well-structured report.\n"
    "\n"
    "Use Markdown with clear sections: Executive Summary, Key Findings, Analysis.\n"
    "Each source below has a number like [3]. Cite claims with those exact numbers,\n"
    "placed right after the claim. Only state facts that the numbered sources support.\n"
    "End with a section titled '## Sources' listing only the sources you cited, as\n"
    "'n. Title - URL', using the same number and copying the URL exactly.\n"
    "Never cite a source that is not in the list.\n"
    "\n"
    "RESEARCH DATA:\n"
)
# Prompts live here as plain concatenated strings rather than triple-quoted
# blocks. Same result, but no multi-line string for an editor to mis-tokenize,
# and the indentation of the code no longer leaks into the prompt text.
PLANNER_PROMPT = (
    "You are a research planner. Given this topic: {topic}\n"
    "\n"
    "Generate exactly 4 specific, focused sub-questions that together would\n"
    "produce a comprehensive research report. Return ONLY a numbered list,\n"
    "one per line."
)

ANALYST_PROMPT = (
    "You are a research analyst. Based on the following research gathered on\n"
    "{topic}, write a comprehensive, well-structured report.\n"
    "\n"
    "Use Markdown with clear sections: Executive Summary, Key Findings, Analysis.\n"
    "Cite sources inline with numbered markers like [1] or [2][3], placed right\n"
    "after the claim they support. End with a section titled '## Sources' that\n"
    "lists each cited source as 'n. Title - URL', numbered to match the markers.\n"
    "Only cite URLs that appear in the research data.\n"
    "\n"
    "RESEARCH DATA:\n"
)


async def _emit(config: RunnableConfig, type_: str, content: str) -> dict:
    """Push one trace event to the client immediately, and return it.

    The emit callback is injected per request through LangGraph's config, so
    nodes stay decoupled from the transport. If nothing is injected (a unit
    test, a CLI run), emitting is a no-op and the node still works.
    """
    event = {"type": type_, "content": content}
    emit = (config or {}).get("configurable", {}).get("emit")
    if emit:
        await emit(event)
    return event


async def decompose_node(state: dict, config: RunnableConfig) -> dict:
    """Break the topic into 4 focused sub-questions."""
    topic = state["topic"]
    events = [await _emit(config, "decompose", f"Planning research: {topic}")]

    prompt = PLANNER_PROMPT.format(topic=topic)

    response = await llm.ainvoke([HumanMessage(content=prompt)])
    lines = [l.strip() for l in response.content.strip().split("\n") if l.strip()]
    questions = [re.sub(r"^\d+[.)]\s*", "", l) for l in lines if l[0].isdigit()]

    events.append(
        await _emit(config, "decompose", f"Breaking into {len(questions)} sub-questions")
    )
    return {
        **state,
        "sub_questions": questions,
        "trace": state.get("trace", []) + events,
    }

def _format_results(results: list[dict]) -> str:
    """Format Tavily-shaped results as text for the synthesizer, keeping URLs so they can be cited."""
    return "\n\n".join(
        f"Title: {r.get('title', '')}\nURL: {r.get('url', '')}\nContent: {r.get('content', '')}"
        for r in results
    )

async def _search_one(question: str, config: RunnableConfig) -> tuple[dict, list[dict]]:
    """Search one sub-question. Never raises; a failure becomes a trace event."""
    events = [await _emit(config, "search", f"Searching: {question}")]
    sources: list[dict] = []
    try:
        search = (config or {}).get("configurable", {}).get("search")
        if search:  # injected by agentbench (record/replay)
            resp = await search(question)
            result = _format_results(resp["results"])
            sources = resp["results"]
        else:       # normal app behavior, unchanged
            result = await web_search(question)
    except Exception as exc:
        events.append(
            await _emit(config, "search", f"Search failed ({type(exc).__name__}): {question}")
        )
        result = ""
    else:
        events.append(await _emit(config, "search", f"Found results: {question}"))
    return {"question": question, "results": result, "sources": sources}, events


async def search_node(state: dict, config: RunnableConfig) -> dict:
    """Run a web search per sub-question."""
    questions = state["sub_questions"]

    if PARALLEL_SEARCH:
        pairs = await asyncio.gather(*(_search_one(q, config) for q in questions))
    else:
        pairs = [await _search_one(q, config) for q in questions]

    results = [r for r, _ in pairs]
    # Each coroutine returns its own event list, so nothing is appended to a
    # shared list concurrently. The original code mutated state["trace"] in
    # place, which would have been a race once searches ran in parallel.
    events = [e for _, evs in pairs for e in evs]

    return {
        **state,
        "search_results": results,
        "trace": state.get("trace", []) + events,
    }


async def synthesize_node(state: dict, config: RunnableConfig) -> dict:
    """Synthesize all search results into a structured report."""
    events = [await _emit(config, "synthesize", "Writing report")]

    # context is appended rather than passed through .format(), because search
    # results routinely contain literal { and } and .format would choke on the
    # template if the braces were in it.
    if NUMBERED_SOURCES and any(item.get("sources") for item in state["search_results"]):
        # Number every retrieved source once (same URL from two sub-questions keeps
        # one number) so the model cites real, retrieved sources by number.
        context, seen = "", {}
        for item in state["search_results"]:
            context += f"\n\n## Sub-question: {item['question']}\n"
            for r in item.get("sources", []):
                url = r.get("url", "")
                seen.setdefault(url, len(seen) + 1)
                context += (f"\n[{seen[url]}] {r.get('title', '')}\nURL: {url}\n"
                            f"Content: {r.get('content', '')}\n")
        prompt = NUMBERED_ANALYST_PROMPT.format(topic=state["topic"]) + context
    else:
        context = ""
        for item in state["search_results"]:
            context += f"\n\n## Sub-question: {item['question']}\n{item['results']}"
        prompt = ANALYST_PROMPT.format(topic=state["topic"]) + context

    response = await llm.ainvoke([HumanMessage(content=prompt)])
    events.append(await _emit(config, "synthesize", "Report generation complete"))

    return {
        **state,
        "report": response.content,
        "trace": state.get("trace", []) + events,
    }
