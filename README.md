# Autonomous AI Research Agent

A full-stack AI agent that takes a research topic, autonomously breaks it into sub-questions, searches the web, and synthesizes a comprehensive structured report — with a live agent trace visible in the UI as it works.

![Python](https://img.shields.io/badge/Python-3.13-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green)
![LangGraph](https://img.shields.io/badge/LangGraph-latest-purple)
![AWS Bedrock](https://img.shields.io/badge/AWS-Bedrock-orange)
![React](https://img.shields.io/badge/React-18-cyan)

---

## Demo

Enter a research topic → watch the agent decompose it into sub-questions → search the web in real time → synthesize a multi-source report with citations.

---

## Architecture

```
User topic
    │
    ▼
LangGraph Orchestrator
    │
    ├── Node 1: Decompose → breaks topic into 4 focused sub-questions
    │
    ├── Node 2: Search → runs Tavily web search per sub-question
    │
    └── Node 3: Synthesize → Claude on AWS Bedrock writes structured report
                                        │
                                        ▼
                          FastAPI SSE streaming endpoint
                                        │
                                        ▼
                          React frontend (live trace + report)
```

---

## Tech Stack

| Layer           | Technology                                               |
| --------------- | -------------------------------------------------------- |
| Agent framework | LangGraph                                                |
| LLM             | AWS Bedrock — Claude 3.5 Sonnet (cross-region inference) |
| Web search      | Tavily API                                               |
| Backend         | FastAPI + SSE streaming                                  |
| Frontend        | React, react-markdown                                    |

---

## Project Structure

```
research-agent/
├── backend/
│   ├── main.py         # FastAPI app, SSE streaming endpoint
│   ├── agent.py        # LangGraph graph definition
│   ├── nodes.py        # Graph nodes: decompose, search, synthesize
│   ├── tools.py        # Tavily web search wrapper
│   ├── bedrock.py      # AWS Bedrock LLM setup
│   ├── requirements.txt
│   └── .env            # API keys (not committed)
├── frontend/
│   └── src/
│       └── App.js      # React UI — topic input, agent trace, report view
└── README.md
```

---

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- AWS account with Bedrock access enabled for Claude 3.5 Sonnet
- Tavily API key (free at [tavily.com](https://tavily.com))

### Backend Setup

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file in the `backend/` folder:

```
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_DEFAULT_REGION=us-east-1
TAVILY_API_KEY=your_tavily_key
```

Start the server:

```bash
uvicorn main:app --reload --port 8000
```

API live at `http://localhost:8000` — health check at `http://localhost:8000/health`

### Frontend Setup

```bash
cd frontend
npm install
npm start
```

Frontend live at `http://localhost:3000`

---

## API Endpoints

### `POST /research`

Runs the full agent pipeline and streams results via SSE.

**Request:**

```json
{
  "topic": "Impact of AI on software engineering jobs in 2025"
}
```

**SSE Event stream:**

```
event: trace
data: {"type": "decompose", "content": "Breaking into 4 sub-questions"}

event: trace
data: {"type": "search", "content": "Searching: How is AI changing developer workflows?"}

event: report
data: {"report": "# Research Report\n\n## Executive Summary\n..."}

event: done
data: {}
```

### `GET /health`

Returns `{"status": "ok"}` — used for deployment health checks.

---

## Key Features

- **Autonomous decomposition** — Claude breaks any topic into focused, targeted sub-questions without user input
- **Real-time agent trace** — the UI shows each step as it happens: decompose → search → synthesize
- **Multi-source synthesis** — findings from all sub-questions are deduplicated and woven into a coherent report
- **Cited sources** — the final report includes inline source references and a further reading section
- **Streaming output** — SSE keeps the frontend live throughout the full pipeline run
- **Input locking** — the topic input is disabled while the agent is running to prevent mid-run changes

---

## AWS Bedrock Notes

This project uses the **cross-region inference profile** model ID pattern required by AWS Bedrock for newer Claude models:

```
us.anthropic.claude-sonnet-4-5-20250929-v1:0
```

Make sure this model is enabled in your AWS Bedrock console under **Model access** before running.

---

## Environment Variables

| Variable                | Description                     |
| ----------------------- | ------------------------------- |
| `AWS_ACCESS_KEY_ID`     | AWS IAM access key              |
| `AWS_SECRET_ACCESS_KEY` | AWS IAM secret key              |
| `AWS_DEFAULT_REGION`    | AWS region (default: us-east-1) |
| `TAVILY_API_KEY`        | Tavily search API key           |

---

## Author

**Mohammad Zaid**

- GitHub: [@m-zaid-mac](https://github.com/m-zaid-mac)
- LinkedIn: [mohammad-zaid](https://www.linkedin.com/in/mohammad-zaid-6a360b276/)
- Email: zaid.m@northeastern.edu
