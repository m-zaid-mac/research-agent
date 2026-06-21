from bedrock import get_llm
from tools import web_search
from langchain_core.messages import HumanMessage

llm = get_llm()

def decompose_node(state: dict) -> dict:
    """Break the topic into 3-5 focused sub-questions."""
    topic = state["topic"]
    prompt = f"""You are a research planner. Given this topic: "{topic}"
    
Generate exactly 4 specific, focused sub-questions that together would produce
a comprehensive research report. Return ONLY a numbered list, one per line."""
    
    response = llm.invoke([HumanMessage(content=prompt)])
    lines = [l.strip() for l in response.content.strip().split("\n") if l.strip()]
    questions = [l.lstrip("1234567890). ") for l in lines if l[0].isdigit()]
    
    return {**state, "sub_questions": questions, "trace": state.get("trace", []) + [
        {"type": "decompose", "content": f"Breaking into {len(questions)} sub-questions"}
    ]}

def search_node(state: dict) -> dict:
    """Run web searches for all sub-questions."""
    results = []
    trace = state.get("trace", [])
    
    for q in state["sub_questions"]:
        trace.append({"type": "search", "content": f"Searching: {q}"})
        result = web_search(q)
        results.append({"question": q, "results": result})
    
    return {**state, "search_results": results, "trace": trace}

def synthesize_node(state: dict) -> dict:
    """Synthesize all search results into a structured report."""
    context = ""
    for item in state["search_results"]:
        context += f"\n\n## Sub-question: {item['question']}\n{item['results']}"
    
    prompt = f"""You are a research analyst. Based on the following research gathered on 
"{state['topic']}", write a comprehensive, well-structured report.

Use Markdown with clear sections: Executive Summary, Key Findings, Analysis, 
Sources & Further Reading. Be specific and cite sources inline.

RESEARCH DATA:
{context}"""
    
    response = llm.invoke([HumanMessage(content=prompt)])
    return {**state, "report": response.content, "trace": state["trace"] + [
        {"type": "synthesize", "content": "Report generation complete"}
    ]}