from langgraph.graph import StateGraph, END
from typing import TypedDict, List, Any
from nodes import decompose_node, search_node, synthesize_node

class AgentState(TypedDict):
    topic: str
    sub_questions: List[str]
    search_results: List[dict]
    report: str
    trace: List[dict]

def build_graph():
    graph = StateGraph(AgentState)
    
    graph.add_node("decompose", decompose_node)
    graph.add_node("search", search_node)
    graph.add_node("synthesize", synthesize_node)
    
    graph.set_entry_point("decompose")
    graph.add_edge("decompose", "search")
    graph.add_edge("search", "synthesize")
    graph.add_edge("synthesize", END)
    
    return graph.compile()

agent = build_graph()