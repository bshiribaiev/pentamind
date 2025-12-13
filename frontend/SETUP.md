# Pentamind Frontend Setup Guide

## Prerequisites

- Node.js 18+ installed
- Rust installed (for Tauri)
- Backend running at `http://localhost:8000`

---

## Installation

### 1. Install Dependencies

```bash
cd frontend
npm install
```

This installs:
- Tauri 2
- React 19
- Tailwind CSS 4
- Lucide Icons
- TypeScript

### 2. Verify Backend is Running

```bash
curl http://localhost:8000/health
# Should return: {"ok":true}
```

If not, start the backend:
```bash
cd ../backend
source venv/bin/activate
python3 -m uvicorn main:app --reload
```

---

## Running

### Development Mode

```bash
npm run tauri dev
```

This will:
1. Start Vite dev server
2. Launch Tauri window
3. Enable hot-reload

**Window will appear as a frameless, always-on-top overlay!**

### Production Build

```bash
npm run tauri build
```

Output: `src-tauri/target/release/Pentamind.app` (Mac) or `.exe` (Windows)

---

## Features

### Hotkey
Press `Cmd+Shift+P` (Mac) or `Ctrl+Shift+P` (Windows) to toggle overlay

### Task Types
- 📝 **Summarize** - Condense long text
- 🔍 **Research** - Deep analysis with Perplexity search
- 🧠 **Solve** - Problem solving with reasoning models
- ⚡ **Code** - Code generation and debugging
- ✍️ **Rewrite** - Rephrase and improve text

### Modes
- **Best**: Highest quality, may use premium models
- **Fast**: Quick responses, optimized for speed
- **Cheap**: Cost-effective, uses efficient models

### Timeline
Watch execution steps light up in real-time:
1. classify_task
2. choose_model
3. execute
4. verify
5. fallback (if needed)

### Scoreboard
- See which models were considered
- View latency and cost tier
- Force rerun with specific model (click 🔄)

### Replay Viewer
Click "Show Execution Replay" to see:
- Full trace with timestamps
- Model selections
- Data passed between steps
- Error messages (if any)

---

## Troubleshooting

### "Cannot connect to backend"
```bash
# Check backend is running
curl http://localhost:8000/health

# If not, start it
cd backend
python3 -m uvicorn main:app --reload
```

### "npm install fails"
```bash
# Clear cache and reinstall
rm -rf node_modules package-lock.json
npm install
```

### "Tauri build fails"
```bash
# Make sure Rust is installed
rustc --version

# If not: https://rustup.rs/
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
```

### "Window not showing"
Check console for errors - likely backend connection issue

### "Hotkey not working"
Try closing and reopening the app, or check if another app is using that hotkey

---

## Customization

### Change Backend URL

Edit `src/App.tsx`:
```typescript
const API_URL = 'http://your-backend:8000';
```

### Change Hotkey

Edit `src/App.tsx`:
```typescript
if ((e.metaKey || e.ctrlKey) && e.shiftKey && e.key === 'P') {
  // Change 'P' to another key
}
```

### Change Theme Colors

Edit `tailwind.config.js` or `src/App.css`

### Change Window Behavior

Edit `src-tauri/tauri.conf.json`:
- `decorations`: false = frameless
- `transparent`: true = transparency
- `alwaysOnTop`: true = stays on top
- `resizable`: true/false

---

## File Structure

```
frontend/
├── src/
│   ├── App.tsx                    # Main app logic
│   ├── App.css                    # Dark theme styles
│   ├── main.tsx                   # React entry point
│   └── components/
│       ├── PentamindOverlay.tsx   # Main overlay component
│       ├── Timeline.tsx           # Execution timeline
│       ├── Scoreboard.tsx         # Model comparison
│       └── ResponseViewer.tsx     # Result display
├── src-tauri/
│   ├── tauri.conf.json           # Window configuration
│   └── src/
│       └── main.rs               # Rust entry point
├── package.json
├── tailwind.config.js
└── index.html
```

---

## Development Workflow

```bash
# Terminal 1: Backend
cd backend
python3 -m uvicorn main:app --reload

# Terminal 2: Frontend
cd frontend
npm run tauri dev
```

Make changes to React components → Hot reload automatically!

---

**Ready to launch!** 🚀

```bash
cd frontend
npm install
npm run tauri dev
```

