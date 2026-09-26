import asyncio
import json
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from agent import agent

log = logging.getLogger("research-agent")

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ResearchRequest(BaseModel):
    topic: str


@app.post("/research")
async def research(req: ResearchRequest):
    # The graph runs as a background task and pushes events onto this queue.
    # The generator below drains the queue and flushes each event to the
    # client as it arrives, so the client sees work as it happens instead of
    # a replay after the run finishes.
    queue: asyncio.Queue = asyncio.Queue()

    async def emit(event: dict) -> None:
        await queue.put(("trace", event))

    async def runner() -> None:
        try:
            final = await agent.ainvoke(
                {
                    "topic": req.topic,
                    "sub_questions": [],
                    "search_results": [],
                    "report": "",
                    "trace": [],
                },
                config={"configurable": {"emit": emit}},
            )
            await queue.put(("report", {"report": final["report"]}))
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            log.exception("research run failed")
            await queue.put(("error", {"message": f"{type(exc).__name__}: {exc}"}))
        finally:
            await queue.put(("done", {}))

    async def event_stream():
        task = asyncio.create_task(runner())
        try:
            while True:
                kind, payload = await queue.get()
                yield {"event": kind, "data": json.dumps(payload)}
                if kind == "done":
                    break
        finally:
            # Fires on normal completion and on client disconnect, when
            # sse_starlette closes the generator. Without this, a user who
            # closes the tab leaves the graph running and burning Bedrock
            # and Tavily calls with nowhere to send the result.
            if not task.done():
                task.cancel()

    # ping= sends a comment frame on idle so proxies don't drop the
    # connection during the long synthesize step.
    return EventSourceResponse(event_stream(), ping=15)


@app.get("/health")
def health():
    return {"status": "ok"}
