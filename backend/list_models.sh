#!/bin/bash

# Script to list available models in your DigitalOcean subscription

echo "🔍 Fetching available models from DigitalOcean..."
echo ""

if [ -z "$MODEL_ACCESS_KEY" ]; then
    echo "❌ ERROR: MODEL_ACCESS_KEY not set"
    echo "Run: export MODEL_ACCESS_KEY='your-key'"
    exit 1
fi

echo "Available models:"
echo "================="
echo ""

curl -s https://inference.do-ai.run/v1/models \
  -H "Authorization: Bearer $MODEL_ACCESS_KEY" | python3 -m json.tool

echo ""
echo "💡 To use a model, copy its 'id' field and update:"
echo "   backend/jury/langgraph_flow.py (lines 20-23)"

