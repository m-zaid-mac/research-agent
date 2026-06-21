from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse
from pydantic import BaseModel
from agent import agent
import json
import asyncio

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class ResearchRequest(BaseModel):
    topic: str

@app.post("/research")
async def research(req: ResearchRequest):
    async def event_stream():
        loop = asyncio.get_event_loop()
        
        # Run the agent (it's synchronous — wrap in executor)
        final_state = await loop.run_in_executor(
            None,
            lambda: agent.invoke({"topic": req.topic, "trace": [], "sub_questions": [], "search_results": [], "report": ""})
        )
        
        # Stream the trace events
        for event in final_state["trace"]:
            yield {"event": "trace", "data": json.dumps(event)}
            await asyncio.sleep(0.1)
        
        # Stream the final report
        yield {"event": "report", "data": json.dumps({"report": final_state["report"]})}
        yield {"event": "done", "data": "{}"}
    
    return EventSourceResponse(event_stream())

@app.get("/health")
def health():
    return {"status": "ok"}