# 🚀 JuryCursor Backend - START HERE

## What You Have

A **production-ready FastAPI backend** with intelligent AI model routing via LangGraph.

### ✅ Complete Implementation

- **3 API endpoints**: `/health`, `/infer`, `/run_jury`
- **Smart routing**: Automatically picks the best model for each task
- **Full tracing**: Every step logged for UI replay
- **Error handling**: Timeouts, retries, fallbacks
- **Docker ready**: Containerized and production-ready

---

## 🏃 Quick Start (3 Steps)

### 1️⃣ Set Your API Key

```bash
export MODEL_ACCESS_KEY="your-digitalocean-model-access-key"
```

### 2️⃣ Install & Start

```bash
cd backend
pip install -r requirements.txt
./start.sh
```

### 3️⃣ Test It

```bash
# In another terminal
python test_api.py
```

**That's it!** Server runs at http://localhost:8000

---

## 📖 Documentation

| File                        | Purpose                              |
| --------------------------- | ------------------------------------ |
| **QUICKSTART.md**           | 60-second setup guide                |
| **README.md**               | Complete documentation with examples |
| **PROJECT_SUMMARY.md**      | Architecture and design decisions    |
| **IMPLEMENTATION_NOTES.md** | Technical implementation details     |

---

## 🧪 Try It Now

### Health Check

```bash
curl http://localhost:8000/health
```

### Direct Model Call

```bash
curl -X POST http://localhost:8000/infer \
  -H "Content-Type: application/json" \
  -d '{
    "model": "openai-gpt-4o-mini",
    "messages": [{"role": "user", "content": "Hello!"}],
    "max_tokens": 50,
    "temperature": 0.7
  }'
```

### Intelligent Routing (⭐ Main Feature)

```bash
curl -X POST http://localhost:8000/run_jury \
  -H "Content-Type: application/json" \
  -d '{
    "task": "code",
    "input": "Write a Python function to reverse a string",
    "mode": "best"
  }'
```

---

## 🎯 How It Works

1. **User sends task** → "Write a quicksort function"
2. **Router classifies** → "This is a coding task"
3. **System chooses** → Claude Sonnet 4 (best for code)
4. **Model executes** → Generates the code
5. **System verifies** → Checks output format
6. **Returns result** → With full trace

**If verification fails** → Automatically retries with GPT-5

---

## 📊 Model Selection

| Task Type     | Selected Model  | Why                     |
| ------------- | --------------- | ----------------------- |
| **Coding**    | Claude Sonnet 4 | Best code generation    |
| **Reasoning** | DeepSeek R1     | Complex problem solving |
| **General**   | GPT-5           | Reliable fallback       |

---

## 🔍 What's Included

### Core Files

```
backend/
├── main.py                    # FastAPI server
├── jury/
│   ├── types.py              # Data models
│   ├── call_model.py         # API wrapper
│   └── langgraph_flow.py     # Routing workflow
└── requirements.txt           # Dependencies
```

### Bonus Files

```
├── test_api.py               # Test suite
├── verify_setup.py           # Setup checker
├── start.sh                  # Quick start script
├── Dockerfile                # Docker image
├── docker-compose.yml        # Orchestration
└── [Multiple .md docs]       # Documentation
```

---

## 🐳 Docker Option

### Build & Run

```bash
docker-compose up --build
```

### Or manually

```bash
docker build -t jurycursor-backend .
docker run -p 8000:8000 \
  -e MODEL_ACCESS_KEY="your-key" \
  jurycursor-backend
```

---

## 🔧 Troubleshooting

### ❌ "MODEL_ACCESS_KEY not set"

```bash
export MODEL_ACCESS_KEY="your-key"
```

### ❌ "Module not found"

```bash
pip install -r requirements.txt
```

### ❌ "Connection refused"

```bash
# Make sure server is running
./start.sh
```

### ❌ "Port 8000 in use"

```bash
# Use different port
uvicorn main:app --port 8001
```

---

## 📚 API Documentation

Once running, visit:

- **Interactive docs**: http://localhost:8000/docs
- **Alternative docs**: http://localhost:8000/redoc
- **Health check**: http://localhost:8000/health

---

## ✅ Verification

Run the setup checker:

```bash
python3 verify_setup.py
```

Should show:

```
✅ All checks passed!
```

---

## 🎓 Next Steps

1. **Test locally** → Run `python test_api.py`
2. **Read docs** → Check `README.md` for details
3. **Integrate frontend** → Use the `/run_jury` endpoint
4. **Deploy** → Use Docker or deploy to cloud
5. **Customize** → Modify prompts in `langgraph_flow.py`

---

## 💡 Key Features to Demo

1. **Intelligent Routing**

   - Send coding task → Gets Claude Sonnet 4
   - Send reasoning task → Gets DeepSeek R1
   - Show the scoreboard in response

2. **Full Tracing**

   - Every step logged with latency
   - Perfect for UI visualization
   - Shows model selection reasoning

3. **Automatic Fallback**

   - If output format is wrong
   - Automatically retries with GPT-5
   - No manual intervention needed

4. **Production Ready**
   - Comprehensive error handling
   - Docker support
   - Health checks
   - Structured logging

---

## 🎉 You're Ready!

Everything is set up and ready to run. Just:

1. Set `MODEL_ACCESS_KEY`
2. Run `./start.sh`
3. Test with `python test_api.py`

**Questions?** Check the documentation files or the inline code comments.

---

**Built for MLH DigitalOcean Hackathon** 🚀

Good luck with your demo! 🎊
