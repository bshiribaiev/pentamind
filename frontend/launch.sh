#!/bin/bash

# Pentamind Frontend Launcher
# Run this to start the desktop app

echo "🧠 Pentamind Frontend Launcher"
echo "=============================="
echo ""

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
    echo ""
fi

# Check if backend is running
echo "🔍 Checking backend..."
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ Backend is running!"
else
    echo "⚠️  Backend not detected at http://localhost:8000"
    echo "   Please start the backend first:"
    echo "   cd ../backend && python3 -m uvicorn main:app --reload"
    echo ""
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo ""
echo "🚀 Launching Pentamind..."
echo "   Press Cmd+Shift+P to toggle overlay"
echo ""

npm run tauri dev

