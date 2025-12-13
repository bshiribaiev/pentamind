# 🧪 Testing Guide - Real-World Tasks

## Quick Start

### **Option 1: Automated Test Suite** (Recommended)

Run the comprehensive test with 8 real-world scenarios:

```bash
cd backend
source venv/bin/activate
python test_real_tasks.py
```

This will test:

- ✅ Coding tasks (binary search, refactoring, LRU cache)
- ✅ Reasoning tasks (math problems, logic puzzles)
- ✅ Research tasks (technical comparisons)
- ✅ Summarization tasks
- ✅ Rewriting tasks

---

### **Option 2: Manual curl Commands**

Test individual endpoints manually:

#### **Test 1: Coding Task**

```bash
curl -X POST http://localhost:8000/run_jury \
  -H "Content-Type: application/json" \
  -d '{
    "task": "code",
    "input": "Write a Python function to reverse a linked list",
    "mode": "best"
  }'
```

**Expected:** Routes to `llama3.3-70b-instruct` (coding model)

---

#### **Test 2: Reasoning Task**

```bash
curl -X POST http://localhost:8000/run_jury \
  -H "Content-Type: application/json" \
  -d '{
    "task": "solve",
    "input": "If 5 machines can produce 5 widgets in 5 minutes, how long does it take 100 machines to produce 100 widgets?",
    "mode": "best"
  }'
```

**Expected:** Routes to `deepseek-r1-distill-llama-70b` (reasoning model)

---

#### **Test 3: Summarization Task**

```bash
curl -X POST http://localhost:8000/run_jury \
  -H "Content-Type: application/json" \
  -d '{
    "task": "summarize",
    "input": "Summarize the benefits of using microservices architecture",
    "mode": "best"
  }'
```

**Expected:** Routes to `llama3.3-70b-instruct` (general model)

---

### **Option 3: Interactive API Docs**

Best for visual testing and exploration:

1. **Start server** (if not running)

   ```bash
   cd backend
   source venv/bin/activate
   python3 -m uvicorn main:app --reload
   ```

2. **Open browser**

   ```
   http://localhost:8000/docs
   ```

3. **Try POST /run_jury endpoint**
   - Click "Try it out"
   - Enter your test data
   - Click "Execute"
   - See the response with full trace!

---

## 📊 What to Look For

### **1. Correct Routing**

Check the `winner_model` in response:

| Task Type   | Expected Model                  |
| ----------- | ------------------------------- |
| `code`      | `llama3.3-70b-instruct`         |
| `solve`     | `deepseek-r1-distill-llama-70b` |
| `summarize` | `llama3.3-70b-instruct`         |
| `research`  | `llama3.3-70b-instruct`         |
| `rewrite`   | `llama3.3-70b-instruct`         |

### **2. Task Classification**

Check the `task_spec` in response:

```json
{
  "intent": "code", // Should match task type
  "format": "text", // text, json, or diff
  "needs_citations": false,
  "confidence": 0.85 // Higher = more certain
}
```

### **3. Execution Trace**

Check the `trace` array shows all steps:

```json
[
  { "step": "classify_task", "model": "llama3-8b-instruct", "latency_ms": 400 },
  { "step": "choose_model", "data": { "winner": "llama3.3-70b-instruct" } },
  { "step": "execute", "model": "llama3.3-70b-instruct", "latency_ms": 800 },
  { "step": "verify", "data": { "passed": true } }
]
```

### **4. Response Quality**

The `final` field should contain:

- Relevant answer to the question
- Proper formatting
- Complete response (not cut off)

---

## 🎯 Example Test Scenarios

### **Coding Tests**

```bash
# Algorithm implementation
"Write a function to find the longest palindromic substring"

# Bug fixing
"Fix this bug: def add(a,b): return a-b"

# Code review
"Review this code and suggest improvements: [code snippet]"
```

### **Reasoning Tests**

```bash
# Math problem
"A rectangle has perimeter 24. If length is twice the width, find dimensions"

# Logic puzzle
"Three people each have a different pet. Alice doesn't have a dog..."

# Complex analysis
"Analyze the time complexity of this algorithm: [code]"
```

### **General Tests**

```bash
# Summarization
"Summarize the key differences between SQL and NoSQL databases"

# Research
"Explain how blockchain technology works"

# Rewriting
"Make this more concise: [long text]"
```

---

## ⚡ Performance Expectations

| Metric                | Expected   |
| --------------------- | ---------- |
| **Total latency**     | 500-1500ms |
| **Router latency**    | 200-500ms  |
| **Execution latency** | 300-1000ms |
| **Success rate**      | 95%+       |

---

## 🐛 Troubleshooting

### **Server not responding**

```bash
# Check if server is running
curl http://localhost:8000/health

# If not, start it
cd backend
source venv/bin/activate
python3 -m uvicorn main:app --reload
```

### **401 errors**

```bash
# Check API key is set
echo $MODEL_ACCESS_KEY

# If not, set it
export MODEL_ACCESS_KEY="your-key-here"
```

### **Slow responses**

- First request is slower (cold start)
- Subsequent requests should be faster
- Check your internet connection

### **Wrong model routing**

- Check the `task_spec.intent` in response
- Router might classify differently than expected
- Adjust task description to be more specific

---

## 📈 Advanced Testing

### **Load Testing**

Test multiple requests:

```bash
# Run 10 requests
for i in {1..10}; do
  echo "Request $i"
  curl -s -X POST http://localhost:8000/run_jury \
    -H "Content-Type: application/json" \
    -d '{"task":"code","input":"Write hello world","mode":"best"}' \
    | jq '.winner_model, .trace[-1].latency_ms'
  echo ""
done
```

### **Test Fallback Mechanism**

Force a verification failure (advanced):

```bash
# Request JSON format for a task that won't produce JSON
curl -X POST http://localhost:8000/run_jury \
  -H "Content-Type: application/json" \
  -d '{
    "task": "code",
    "input": "Write code to return JSON: {\"hello\": \"world\"}",
    "mode": "best"
  }'
```

Check trace for `fallback` step.

---

## 🎓 For Your Demo

### **Best Tasks to Showcase:**

1. **Coding Task** - Shows smart routing to coding model

   ```
   "Create a REST API endpoint in Python using FastAPI"
   ```

2. **Math Puzzle** - Shows reasoning model in action

   ```
   "If I have 6 apples and give away half, then double what's left, how many do I have?"
   ```

3. **Code Review** - Shows practical use case
   ```
   "Review this code for security issues: [vulnerable code]"
   ```

### **What to Highlight:**

- ✨ Different tasks route to different models automatically
- 📊 Full trace shows AI "thinking process"
- ⚡ Sub-second response times
- 🎯 High-quality responses from specialized models
- 🔄 Automatic fallback if something fails

---

## 📞 Quick Reference

| Command                             | Purpose             |
| ----------------------------------- | ------------------- |
| `python test_real_tasks.py`         | Run full test suite |
| `curl http://localhost:8000/health` | Check server status |
| `curl http://localhost:8000/docs`   | View API docs       |
| `python test_api.py`                | Run basic tests     |

---

**Happy Testing! 🚀**
