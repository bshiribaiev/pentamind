# Pentamind Backend

Production-ready FastAPI backend with intelligent multi-model routing via LangGraph.

## Overview

Pentamind automatically routes tasks to the best AI model based on task classification:

- **Coding tasks** → `anthropic-claude-sonnet-4`
- **Reasoning tasks** → `deepseek-r1-distill-llama-70b`
- **General tasks** → `openai-gpt-5` (fallback)
- **Task classification** → `openai-gpt-4o-mini` (router)

All models are accessed through **DigitalOcean Serverless Inference**.

## Features

✅ Intelligent LangGraph-based routing workflow  
✅ Automatic fallback on verification failures  
✅ Comprehensive error handling (timeouts, API errors, validation)  
✅ Full execution traces for UI replay  
✅ Production-ready logging and monitoring  
✅ OpenAPI documentation (FastAPI)

---

## Quick Start

### 1. Installation

```bash
cd backend
pip install -r requirements.txt
```

### 2. Configuration

Set your DigitalOcean model access key:

```bash
export MODEL_ACCESS_KEY="your-digitalocean-model-access-key"
```

Or create a `.env` file:

```bash
echo "MODEL_ACCESS_KEY=your-key-here" > .env
```

### 3. Run Server

```bash
uvicorn main:app --reload
```

Server runs at: **http://localhost:8000**

API Documentation: **http://localhost:8000/docs**

---

## API Endpoints

### `GET /health`

Health check endpoint.

**Response:**

```json
{
  "ok": true
}
```

---

### `POST /infer`

Generic single-model inference wrapper.

**Request:**

```json
{
  "model": "llama3.3-70b-instruct",
  "messages": [{ "role": "user", "content": "Say pong" }],
  "max_tokens": 200,
  "temperature": 0.2
}
```

**Response:**

```json
{
  "final": "pong",
  "model": "llama3.3-70b-instruct",
  "latency_ms": 123,
  "usage": {
    "prompt_tokens": 10,
    "completion_tokens": 5,
    "total_tokens": 15
  },
  "trace": [
    {
      "step": "infer",
      "model": "llama3.3-70b-instruct",
      "latency_ms": 123
    }
  ]
}
```

**Example with curl:**

```bash
curl -X POST http://localhost:8000/infer \
  -H "Content-Type: application/json" \
  -d '{
    "model": "openai-gpt-4o-mini",
    "messages": [{"role": "user", "content": "Hello!"}],
    "max_tokens": 100,
    "temperature": 0.7
  }'
```

---

### `POST /run_jury`

Run the intelligent LangGraph routing pipeline.

**Request:**

```json
{
  "task": "code",
  "input": "Write a Python function to calculate fibonacci numbers",
  "mode": "best"
}
```

**Parameters:**

- `task`: One of `summarize`, `research`, `solve`, `code`, `rewrite`
- `input`: User's input text
- `mode`: One of `best`, `fast`, `cheap` (currently all use "best" logic)

**Response:**

```json
{
  "final": "def fibonacci(n):\n    if n <= 1:\n        return n\n    return fibonacci(n-1) + fibonacci(n-2)",
  "winner_model": "anthropic-claude-sonnet-4",
  "task_spec": {
    "intent": "code",
    "format": "text",
    "needs_citations": false,
    "confidence": 0.95
  },
  "scoreboard": [
    {
      "model": "anthropic-claude-sonnet-4",
      "quality": 0.9,
      "latency_ms": 1234,
      "cost_tier": "high",
      "notes": "Best for coding tasks"
    },
    {
      "model": "deepseek-r1-distill-llama-70b",
      "quality": 0.0,
      "latency_ms": 0,
      "cost_tier": "med",
      "notes": ""
    },
    {
      "model": "openai-gpt-5",
      "quality": 0.0,
      "latency_ms": 0,
      "cost_tier": "high",
      "notes": ""
    }
  ],
  "trace": [
    {
      "step": "classify_task",
      "model": "openai-gpt-4o-mini",
      "latency_ms": 234,
      "data": {
        "intent": "code",
        "format": "text",
        "needs_citations": false,
        "confidence": 0.95
      }
    },
    {
      "step": "choose_model",
      "latency_ms": 0,
      "data": {
        "winner": "anthropic-claude-sonnet-4",
        "intent": "code"
      }
    },
    {
      "step": "execute",
      "model": "anthropic-claude-sonnet-4",
      "latency_ms": 1234
    },
    {
      "step": "verify",
      "latency_ms": 0,
      "data": {
        "passed": true,
        "notes": ["Non-empty response"]
      }
    }
  ]
}
```

**Example with curl:**

```bash
curl -X POST http://localhost:8000/run_jury \
  -H "Content-Type: application/json" \
  -d '{
    "task": "code",
    "input": "Create a REST API endpoint in Python",
    "mode": "best"
  }'
```

---

## LangGraph Workflow

The jury pipeline consists of these nodes:

1. **classify_task**: Uses `openai-gpt-4o-mini` to classify the task

   - Returns: `intent` (code/reasoning/general), `format` (text/diff/json), `needs_citations`, `confidence`

2. **choose_model**: Deterministic model selection based on intent

   - `code` → `anthropic-claude-sonnet-4`
   - `reasoning` → `deepseek-r1-distill-llama-70b`
   - `general` → `openai-gpt-5`

3. **execute**: Run the chosen model with task-specific prompt

4. **verify**: Validate output format

   - JSON: Parse validation
   - Diff: Check for diff markers
   - Text: Non-empty check

5. **fallback** (conditional): If verification fails, retry with `openai-gpt-5`

### Workflow Diagram

```
START → classify_task → choose_model → execute → verify → END
                                                      ↓
                                                  (if failed)
                                                      ↓
                                                  fallback → END
```

---

## Project Structure

```
backend/
├── main.py                    # FastAPI server and endpoints
├── jury/
│   ├── __init__.py
│   ├── types.py              # Pydantic models and types
│   ├── call_model.py         # DigitalOcean API wrapper
│   └── langgraph_flow.py     # LangGraph workflow
├── requirements.txt           # Python dependencies
└── README.md                 # This file
```

---

## Error Handling

The backend handles:

- ✅ **Missing environment variables**: Checked at startup and per-request
- ✅ **API timeouts**: Default 60s timeout with configurable overrides
- ✅ **Non-200 responses**: Logged and re-raised as `ModelAPIError`
- ✅ **Invalid payloads**: Pydantic validation with detailed error messages
- ✅ **Network errors**: Caught and wrapped with context
- ✅ **JSON parsing failures**: Graceful fallback to defaults
- ✅ **Verification failures**: Automatic fallback to GPT-5

All errors return structured JSON responses with:

```json
{
  "error": "error_type",
  "message": "Human-readable message",
  "details": {}
}
```

---

## Development

### Run with hot reload

```bash
uvicorn main:app --reload
```

### Run in production mode

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

### View logs

The application logs all requests, model calls, and errors to stdout:

```
2025-12-13 10:15:23 [INFO] main: POST /run_jury - task=code, mode=best
2025-12-13 10:15:23 [INFO] jury.langgraph_flow: Starting jury workflow: task=code, mode=best
2025-12-13 10:15:23 [INFO] jury.call_model: Calling model: openai-gpt-4o-mini (timeout=30.0s)
...
```

### Environment Variables

| Variable           | Required | Description                                      |
| ------------------ | -------- | ------------------------------------------------ |
| `MODEL_ACCESS_KEY` | ✅ Yes   | DigitalOcean model access key for authentication |

---

## Testing

### Test health endpoint

```bash
curl http://localhost:8000/health
```

### Test infer endpoint

```bash
curl -X POST http://localhost:8000/infer \
  -H "Content-Type: application/json" \
  -d '{
    "model": "openai-gpt-4o-mini",
    "messages": [{"role": "user", "content": "What is 2+2?"}],
    "max_tokens": 50,
    "temperature": 0.0
  }'
```

### Test jury routing

```bash
# Coding task (should route to Sonnet 4)
curl -X POST http://localhost:8000/run_jury \
  -H "Content-Type: application/json" \
  -d '{
    "task": "code",
    "input": "Write a quicksort implementation",
    "mode": "best"
  }'

# Reasoning task (should route to DeepSeek)
curl -X POST http://localhost:8000/run_jury \
  -H "Content-Type: application/json" \
  -d '{
    "task": "solve",
    "input": "Prove that sqrt(2) is irrational",
    "mode": "best"
  }'

# Summarization (should route to GPT-5)
curl -X POST http://localhost:8000/run_jury \
  -H "Content-Type: application/json" \
  -d '{
    "task": "summarize",
    "input": "Summarize this article: ...",
    "mode": "best"
  }'
```

---

## Production Deployment

### Using Docker (recommended)

Create a `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV MODEL_ACCESS_KEY=""

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Build and run:

```bash
docker build -t jurycursor-backend .
docker run -p 8000:8000 -e MODEL_ACCESS_KEY="your-key" jurycursor-backend
```

### Using systemd

Create `/etc/systemd/system/jurycursor.service`:

```ini
[Unit]
Description=JuryCursor Backend
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/jurycursor/backend
Environment="MODEL_ACCESS_KEY=your-key-here"
ExecStart=/usr/local/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl enable jurycursor
sudo systemctl start jurycursor
```

---

## License

MIT

---

## Support

For issues or questions, contact the hackathon team or open an issue.

**Built with ❤️ for MLH DO Hackathon**
