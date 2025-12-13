# Pentamind Architecture

## System Overview

```
┌──────────────────────────────────────────────────────────────┐
│                                                              │
│                    🧠 PENTAMIND SYSTEM                       │
│                                                              │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│                       FRONTEND LAYER                         │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌────────────────────────────────────────────────────┐     │
│  │   Tauri Desktop App (Frameless, Always-on-Top)    │     │
│  │   ─────────────────────────────────────────────────│     │
│  │                                                     │     │
│  │   React 19 + TypeScript + Tailwind CSS 4          │     │
│  │                                                     │     │
│  │   Components:                                      │     │
│  │   • PentamindOverlay    (main UI)                 │     │
│  │   • Timeline            (execution viz)            │     │
│  │   • Scoreboard          (model comparison)         │     │
│  │   • ResponseViewer      (result display)           │     │
│  └────────────────────────────────────────────────────┘     │
│                                                              │
│  Features:                                                   │
│  • Global hotkey (Cmd+Shift+P)                             │
│  • 5 task types (Summarize, Research, Solve, Code, Rewrite)│
│  • 3 modes (Best, Fast, Cheap)                             │
│  • Live timeline with animations                            │
│  • Model scoreboard with force-rerun                        │
│  • Execution replay viewer                                  │
│                                                              │
└──────────────────────────────────────────────────────────────┘
                              │
                              │ HTTP POST
                              │ http://localhost:8000/run_jury
                              ▼
┌──────────────────────────────────────────────────────────────┐
│                       BACKEND LAYER                          │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌────────────────────────────────────────────────────┐     │
│  │            FastAPI Server (Python 3.11+)           │     │
│  │   ─────────────────────────────────────────────────│     │
│  │                                                     │     │
│  │   Endpoints:                                       │     │
│  │   • GET  /health          → {"ok": true}          │     │
│  │   • POST /infer           → Single model call      │     │
│  │   • POST /run_jury        → LangGraph workflow     │     │
│  └────────────────────────────────────────────────────┘     │
│                                                              │
└──────────────────────────────────────────────────────────────┘
                              │
                              │ Invoke
                              ▼
┌──────────────────────────────────────────────────────────────┐
│                    LANGGRAPH WORKFLOW                        │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│   START                                                      │
│     │                                                        │
│     ▼                                                        │
│  ┌─────────────────┐                                        │
│  │ classify_task   │  Analyze intent, format, confidence    │
│  │ Model: llama3-8b│  Output: task_spec JSON                │
│  └─────────────────┘                                        │
│     │                                                        │
│     ▼                                                        │
│  ┌─────────────────┐                                        │
│  │ choose_model    │  Select best model based on:           │
│  │                 │  • task_spec.intent                    │
│  └─────────────────┘  • Input length                        │
│     │                  • Citations needed                    │
│     │                                                        │
│     ├─ intent=="code"      → llama3.3-70b-instruct          │
│     ├─ intent=="reasoning" → deepseek-r1-distill-llama-70b  │
│     ├─ input_len > 10K    → gemini-1.5-flash-latest         │
│     ├─ input_len > 50K    → gemini-1.5-pro-latest           │
│     └─ else               → llama3.3-70b-instruct (fallback)│
│     │                                                        │
│     ▼                                                        │
│  ┌─────────────────┐                                        │
│  │ execute         │  Run selected model                    │
│  │                 │  + Perplexity search (if needed)       │
│  └─────────────────┘                                        │
│     │                                                        │
│     ▼                                                        │
│  ┌─────────────────┐                                        │
│  │ verify          │  Check output validity:                │
│  │                 │  • JSON parseable?                     │
│  └─────────────────┘  • Diff format correct?                │
│     │                  • Non-empty?                          │
│     │                                                        │
│     ├─ Valid ─────────────────────────────────┐            │
│     │                                           │            │
│     ▼                                           ▼            │
│  ┌─────────────────┐                         END           │
│  │ fallback        │                                        │
│  │ Use: llama3.3   │  (Winner result returned)             │
│  │ -70b-instruct   │                                        │
│  └─────────────────┘                                        │
│     │                                                        │
│     └──────────────────────────────────────────┐            │
│                                                 │            │
│                                                 ▼            │
│                                               END           │
│                                                              │
└──────────────────────────────────────────────────────────────┘
                              │
                              │ API Calls
                              ▼
┌──────────────────────────────────────────────────────────────┐
│                      MODEL PROVIDERS                         │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────────────────────────────┐               │
│  │      DigitalOcean Serverless Inference   │               │
│  │   https://inference.do-ai.run/v1         │               │
│  │   ─────────────────────────────────────   │               │
│  │   • llama3-8b-instruct       (router)    │               │
│  │   • llama3.3-70b-instruct    (coding)    │               │
│  │   • deepseek-r1-distill-70b  (reasoning) │               │
│  └──────────────────────────────────────────┘               │
│                                                              │
│  ┌──────────────────────────────────────────┐               │
│  │        Google Gemini API                 │               │
│  │   generativelanguage.googleapis.com      │               │
│  │   ─────────────────────────────────────   │               │
│  │   • gemini-1.5-flash-latest (1M tokens)  │               │
│  │   • gemini-1.5-pro-latest   (2M tokens)  │               │
│  └──────────────────────────────────────────┘               │
│                                                              │
│  ┌──────────────────────────────────────────┐               │
│  │        Perplexity Search API             │               │
│  │   api.perplexity.ai                      │               │
│  │   ─────────────────────────────────────   │               │
│  │   • Web search with citations            │               │
│  │   • Real-time information                │               │
│  └──────────────────────────────────────────┘               │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

## Data Flow

### Request Flow:

```
User Input
   │
   │ 1. User types text
   │ 2. Selects task type (e.g., Code)
   │ 3. Chooses mode (e.g., Best)
   │ 4. Clicks "Run Analysis"
   │
   ▼
Frontend (React)
   │
   │ POST /run_jury
   │ {
   │   "task": "code",
   │   "input": "Write a quicksort",
   │   "mode": "best"
   │ }
   │
   ▼
Backend (FastAPI)
   │
   │ Invoke LangGraph
   │
   ▼
LangGraph Workflow
   │
   ├─ 1. classify_task
   │    ├─ Call: llama3-8b-instruct
   │    └─ Return: {"intent":"code","format":"text",...}
   │
   ├─ 2. choose_model
   │    └─ Logic: intent=="code" → llama3.3-70b-instruct
   │
   ├─ 3. execute
   │    ├─ Call: llama3.3-70b-instruct
   │    └─ Return: code implementation
   │
   ├─ 4. verify
   │    └─ Check: output valid? ✅
   │
   └─ END
   │
   ▼
Response
   │
   │ {
   │   "final": "def quicksort(arr): ...",
   │   "winner_model": "llama3.3-70b-instruct",
   │   "task_spec": {...},
   │   "scoreboard": [...],
   │   "trace": [...]
   │ }
   │
   ▼
Frontend Display
   │
   ├─ Timeline: Show all steps with latencies
   ├─ Response: Display generated code
   ├─ Scoreboard: Show model comparison
   └─ Replay: Full trace available
```

---

## Component Responsibilities

### Frontend Components:

| Component              | Responsibility                              |
| ---------------------- | ------------------------------------------- |
| `App.tsx`              | Main app logic, state management, API calls |
| `PentamindOverlay.tsx` | Layout, input handling, UI orchestration    |
| `Timeline.tsx`         | Visualize execution steps with animations   |
| `Scoreboard.tsx`       | Display model comparison, handle reruns     |
| `ResponseViewer.tsx`   | Show final result, task analysis, winner    |

### Backend Modules:

| Module                 | Responsibility                       |
| ---------------------- | ------------------------------------ |
| `main.py`              | FastAPI server, route definitions    |
| `types.py`             | Pydantic models for request/response |
| `langgraph_flow.py`    | Workflow logic, node definitions     |
| `call_model.py`        | DigitalOcean API client              |
| `gemini_client.py`     | Google Gemini API client             |
| `perplexity_search.py` | Perplexity search integration        |

---

## Model Selection Logic

```python
def choose_model(state):
    task_spec = state["task_spec"]
    input_text = state["input"]

    # Long context → Gemini
    if len(input_text) > 50000:
        return "gemini-1.5-pro-latest"
    elif len(input_text) > 10000:
        return "gemini-1.5-flash-latest"

    # Intent-based routing
    if task_spec["intent"] == "code":
        return "llama3.3-70b-instruct"
    elif task_spec["intent"] == "reasoning":
        return "deepseek-r1-distill-llama-70b"
    else:
        return "llama3.3-70b-instruct"  # fallback
```

---

## Error Handling

### Frontend Errors:

```
Network Error → Show red alert banner
Timeout       → Show "Request timed out" message
API 500       → Show "Backend error" + log details
```

### Backend Errors:

```
Model API Error → Try fallback model
Timeout         → Return error with trace so far
Invalid Input   → Return 422 with validation errors
Missing API Key → Graceful fallback (skip optional features)
```

---

## State Management

### Frontend State:

```typescript
{
  isVisible: boolean,           // Overlay shown?
  inputText: string,            // User input
  selectedTask: string,         // "code"|"research"|...
  selectedMode: "best"|"fast"|"cheap",
  isProcessing: boolean,        // Currently running?
  response: JuryResponse | null, // Result
  error: string | null          // Error message
}
```

### Backend State (LangGraph):

```python
{
  "task": str,                  # Original task type
  "input": str,                 # User input text
  "mode": str,                  # "best"|"fast"|"cheap"
  "task_spec": dict,            # Classification result
  "chosen_model": str,          # Selected model name
  "execution_output": str,      # Model response
  "verification_ok": bool,      # Passed verification?
  "final": str,                 # Final output
  "winner_model": str,          # Winning model
  "trace": List[dict]           # Execution trace
}
```

---

## Performance

### Latencies (typical):

| Step                   | Time             |
| ---------------------- | ---------------- |
| classify_task          | 100-200ms        |
| choose_model           | <10ms            |
| execute (code)         | 500-2000ms       |
| execute (reasoning)    | 1000-5000ms      |
| execute (long context) | 2000-10000ms     |
| verify                 | <50ms            |
| **Total**              | **1-12 seconds** |

### Optimizations:

- **Router model**: Use fast Llama 8B (not GPT-4)
- **Streaming**: Could add SSE for real-time updates
- **Caching**: Could cache task classifications
- **Parallel calls**: Could call multiple models in parallel

---

## Security

### API Keys:

- Stored in environment variables
- Never logged or exposed in traces
- Backend validates presence before calls

### CORS:

- Backend allows `localhost:1420` (Tauri dev)
- Production should restrict origins

### Input Validation:

- Pydantic models validate all inputs
- Max input length checks
- Sanitize outputs before display

---

## Deployment

### Backend:

```bash
# Local
uvicorn main:app --reload

# Production (DigitalOcean App Platform)
- Push to GitHub
- Connect DO App Platform
- Set env vars in dashboard
- Auto-deploy on push
```

### Frontend:

```bash
# Development
npm run tauri dev

# Build distributable
npm run tauri build

# Output:
# - macOS: .app bundle
# - Windows: .exe installer
# - Linux: .AppImage/.deb
```

---

## Tech Stack Summary

```
Frontend:
├── Tauri 2              (Desktop framework)
├── React 19             (UI library)
├── TypeScript           (Type safety)
├── Tailwind CSS 4       (Styling)
└── Lucide React         (Icons)

Backend:
├── Python 3.11+         (Language)
├── FastAPI              (Web framework)
├── LangGraph            (Workflow orchestration)
├── Pydantic             (Data validation)
├── httpx/requests       (HTTP clients)
├── uvicorn              (ASGI server)
└── pytest               (Testing)

AI Models:
├── DigitalOcean Inference (Llama, DeepSeek)
├── Google Gemini          (Long context)
└── Perplexity             (Web search)
```

---

## File Structure

```
hack-mlhdo/
├── backend/
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── types.py                  # Data models
│   │   ├── call_model.py             # DO API client
│   │   ├── gemini_client.py          # Gemini client
│   │   ├── perplexity_search.py      # Perplexity client
│   │   └── langgraph_flow.py         # Workflow logic
│   ├── main.py                        # FastAPI app
│   ├── requirements.txt               # Python deps
│   ├── test_api.py                    # Basic tests
│   ├── test_real_tasks.py             # Real-world tests
│   ├── test_perplexity.py             # Perplexity tests
│   ├── test_gemini.py                 # Gemini tests
│   └── README.md                      # Backend docs
│
├── frontend/
│   ├── src/
│   │   ├── App.tsx                    # Main app
│   │   ├── App.css                    # Styles
│   │   ├── main.tsx                   # Entry point
│   │   └── components/
│   │       ├── PentamindOverlay.tsx   # Main overlay
│   │       ├── Timeline.tsx           # Execution viz
│   │       ├── Scoreboard.tsx         # Model comparison
│   │       └── ResponseViewer.tsx     # Result display
│   ├── src-tauri/
│   │   ├── tauri.conf.json            # Window config
│   │   └── src/main.rs                # Rust entry
│   ├── package.json                    # Node deps
│   ├── tailwind.config.js              # Tailwind config
│   ├── README.md                       # Frontend docs
│   ├── SETUP.md                        # Setup guide
│   ├── QUICKSTART.md                   # Quick start
│   └── UI_GUIDE.md                     # UI reference
│
├── launch.sh                           # Complete launcher
├── START_HERE.md                       # Main entry point
├── PENTAMIND_OVERVIEW.md               # System overview
└── ARCHITECTURE.md                     # This file
```

---

**Pentamind: Five Models, One Mind** 🧠✨

**Complete, tested, and ready for demo!** 🚀
