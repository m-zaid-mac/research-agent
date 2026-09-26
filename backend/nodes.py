import asyncio

from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig

from bedrock import get_llm
from tools import web_search

llm = get_llm()

# Flip to False to go back to one-search-at-a-time.
PARALLEL_SEARCH = True

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
    "Use Markdown with clear sections: Executive Summary, Key Findings,\n"
    "Analysis, Sources & Further Reading. Be specific and cite sources inline.\n"
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
    questions = [l.lstrip("1234567890). ") for l in lines if l[0].isdigit()]

    events.append(
        await _emit(config, "decompose", f"Breaking into {len(questions)} sub-questions")
    )
    return {
        **state,
        "sub_questions": questions,
        "trace": state.get("trace", []) + events,
    }


async def _search_one(question: str, config: RunnableConfig) -> tuple[dict, list[dict]]:
    """Search one sub-question. Never raises; a failure becomes a trace event."""
    events = [await _emit(config, "search", f"Searching: {question}")]
    try:
        result = await web_search(question)
    except Exception as exc:
        events.append(
            await _emit(config, "search", f"Search failed ({type(exc).__name__}): {question}")
        )
        result = ""
    else:
        events.append(await _emit(config, "search", f"Found results: {question}"))
    return {"question": question, "results": result}, events


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

    context = ""
    for item in state["search_results"]:
        context += f"\n\n## Sub-question: {item['question']}\n{item['results']}"

    # context is appended rather than passed through .format(), because search
    # results routinely contain literal { and } and .format would choke on the
    # template if the braces were in it.
    prompt = ANALYST_PROMPT.format(topic=state["topic"]) + context

    response = await llm.ainvoke([HumanMessage(content=prompt)])
    events.append(await _emit(config, "synthesize", "Report generation complete"))

    return {
        **state,
        "report": response.content,
        "trace": state.get("trace", []) + events,
    }
