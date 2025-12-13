#!/bin/bash

# JuryCursor Backend Start Script

set -e

echo "🚀 Starting JuryCursor Backend..."
echo ""

# Check if MODEL_ACCESS_KEY is set
if [ -z "$MODEL_ACCESS_KEY" ]; then
    echo "❌ ERROR: MODEL_ACCESS_KEY environment variable is not set"
    echo ""
    echo "Please set it using:"
    echo "  export MODEL_ACCESS_KEY='your-key-here'"
    echo ""
    echo "Or create a .env file with:"
    echo "  MODEL_ACCESS_KEY=your-key-here"
    echo ""
    exit 1
fi

echo "✓ MODEL_ACCESS_KEY is set"

# Check if dependencies are installed
if ! python3 -c "import fastapi" 2>/dev/null; then
    echo ""
    echo "📦 Installing dependencies..."
    pip3 install -r requirements.txt
fi

echo "✓ Dependencies installed"
echo ""

# Start the server
echo "🌐 Starting server at http://localhost:8000"
echo "📚 API docs available at http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop"
echo ""

exec python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload

