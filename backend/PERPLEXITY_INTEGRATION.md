# 🔍 Perplexity Integration Guide

## Overview

Your JuryCursor backend now integrates **Perplexity Search** for research and citation-heavy tasks! This gives your AI agents access to real-time web search results.

---

## 🎯 What It Does

When a task requires research or citations:

1. **Perplexity searches** the web for relevant information
2. **Finds top sources** with titles and URLs
3. **Feeds results to the LLM** as context
4. **LLM synthesizes** information with proper citations
5. **Sources are included** in the final response

---

## 🚀 Quick Setup

### 1. Get Perplexity API Key

Visit: https://www.perplexity.ai/

- Sign up for an account
- Get your API key from settings

### 2. Set Environment Variable

```bash
export PERPLEXITY_API_KEY="your-perplexity-api-key-here"
```

Or add to `.env` file:

```bash
echo "PERPLEXITY_API_KEY=your-key-here" >> .env
```

### 3. Install Perplexity Package

```bash
cd backend
source venv/bin/activate
pip install perplexityai
```

### 4. Test Integration

```bash
python test_perplexity.py
```

---

## ✅ When Perplexity is Used

Perplexity automatically activates for:

### **1. Tasks with `needs_citations=true`**

```json
{
  "task": "research",
  "input": "Explain the latest developments in quantum computing"
}
```

### **2. Research Tasks**

```bash
curl -X POST http://localhost:8000/run_jury \
  -H "Content-Type: application/json" \
  -d '{
    "task": "research",
    "input": "Compare React vs Vue performance benchmarks",
    "mode": "best"
  }'
```

### **3. Solve Tasks Needing Context**

```json
{
  "task": "solve",
  "input": "What are the current best practices for API security in 2025?"
}
```

---

## 📊 Response Format

When Perplexity is used, responses include:

### **1. Citations in Response**

```
React generally performs better in large-scale applications [1], while Vue
excels in smaller projects with faster initial load times [2].

---
**Sources:**
[1] React Performance Benchmarks 2025 - https://example.com/react-benchmarks
[2] Vue.js Speed Analysis - https://example.com/vue-speed
[3] Framework Comparison Study - https://example.com/comparison
```

### **2. Trace Information**

```json
{
  "trace": [
    {
      "step": "execute",
      "model": "deepseek-r1-distill-llama-70b",
      "latency_ms": 1234,
      "data": {
        "perplexity_used": true,
        "sources_found": 5,
        "sources": [
          "[1] Article Title - https://...",
          "[2] Another Source - https://..."
        ]
      }
    }
  ]
}
```

---

## 🎭 Example Usage

### **Research Task with Citations**

```python
import requests

response = requests.post('http://localhost:8000/run_jury', json={
    "task": "research",
    "input": "What are the pros and cons of microservices architecture?",
    "mode": "best"
})

data = response.json()
print(data['final'])  # Includes citations
print(data['trace'][-1]['data'])  # Shows Perplexity was used
```

**Output includes:**

- Well-researched answer
- Citations like [1], [2], [3]
- Source list at the end
- Trace showing Perplexity usage

---

## 🔧 How It Works

### **Backend Flow:**

```
User Query
    ↓
Classify Task → needs_citations=true
    ↓
Choose Model → DeepSeek R1 (reasoning model)
    ↓
Execute Node:
    ├→ Check if Perplexity needed
    ├→ Perform Perplexity search (5 results)
    ├→ Format results as context
    ├→ Add to LLM prompt
    ├→ LLM synthesizes with citations
    └→ Append source list
    ↓
Return with sources
```

### **Code Location:**

- **Integration:** `backend/agent/perplexity_search.py`
- **Usage:** `backend/agent/langgraph_flow.py` (execute node)

---

## ⚙️ Configuration

### **Adjust Results Count**

In `langgraph_flow.py`:

```python
search_data = search_with_perplexity(state.input, max_results=5)  # Change 5 to your preference
```

### **Customize When to Use**

In `langgraph_flow.py`:

```python
use_perplexity = (
    task_spec.needs_citations or
    state.task in ["research", "solve"] and task_spec.intent == "reasoning"
)
```

---

## 🚫 Without Perplexity

If `PERPLEXITY_API_KEY` is not set:

- ✅ Backend still works normally
- ✅ Research tasks use LLM knowledge only
- ⚠️ No real-time web search
- ⚠️ No source citations

The backend gracefully falls back to standard LLM responses.

---

## 💰 Cost Considerations

Perplexity API pricing (check current rates):

- ~$0.001-0.005 per search
- Only used when needed
- Dramatically improves research quality

**Smart routing means:**

- Coding tasks → No Perplexity (not needed)
- Math puzzles → No Perplexity (not needed)
- Research → Perplexity (high value)

---

## 📈 Testing Perplexity

### **Test Script**

```bash
python test_perplexity.py
```

**This checks:**

- ✅ API key is set
- ✅ SDK is installed
- ✅ Search works
- ✅ Results are formatted correctly

### **Live Test**

```bash
curl -X POST http://localhost:8000/run_jury \
  -H "Content-Type: application/json" \
  -d '{
    "task": "research",
    "input": "What is LangGraph and how does it work?",
    "mode": "best"
  }' | jq '.trace[-1].data.perplexity_used'
```

Should return: `true`

---

## 🎯 Demo Tips

When showcasing Perplexity integration:

1. **Compare with/without:**

   - Show research question without Perplexity
   - Then show same question WITH Perplexity
   - Highlight the source citations

2. **Show the trace:**

   - Display `perplexity_used: true`
   - Show sources found count
   - Display actual URLs

3. **Real-time data:**
   - Ask about recent events
   - Show it gets current information
   - Highlight this vs LLM's training data cutoff

---

## 🐛 Troubleshooting

### **"ModuleNotFoundError: No module named 'perplexity'"**

```bash
pip install perplexityai
```

### **"PERPLEXITY_API_KEY not set"**

```bash
export PERPLEXITY_API_KEY="your-key"
```

### **Search returns no results**

- Check API key is valid
- Ensure internet connection
- Check Perplexity API status

### **Want to disable Perplexity temporarily**

```bash
unset PERPLEXITY_API_KEY
```

---

## 📚 API Reference

### **search_with_perplexity(query, max_results)**

Performs a web search using Perplexity.

**Parameters:**

- `query` (str): Search query
- `max_results` (int): Max results to return (default: 5)

**Returns:**

```python
{
    "success": True,
    "query": "search query",
    "results": [
        {"title": "...", "url": "...", "snippet": "..."},
        ...
    ],
    "source": "perplexity",
    "count": 5
}
```

### **format_search_results_for_llm(search_data)**

Formats search results for LLM consumption.

**Returns:** Formatted string with numbered sources.

---

## 🎉 Benefits

✅ **Real-time information** - Not limited to LLM training data  
✅ **Source citations** - Builds trust and credibility  
✅ **Better research** - Leverages web knowledge  
✅ **Automatic routing** - Only used when beneficial  
✅ **Graceful fallback** - Works without API key

---

**Your backend is now supercharged with web search!** 🚀🔍
