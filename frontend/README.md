# Pentamind Desktop Overlay

Dark-themed desktop overlay for intelligent multi-model AI routing.

## Features

✨ **Frameless Always-on-Top Window** - Floats above all apps  
⌨️ **Global Hotkey** - Press `Cmd+Shift+P` (Mac) or `Ctrl+Shift+P` (Windows) to toggle  
🎯 **5 Task Types** - Summarize, Research, Solve, Code, Rewrite  
⚡ **3 Modes** - Best, Fast, Cheap  
📊 **Live Timeline** - Watch execution steps light up in real-time  
🏆 **Model Scoreboard** - Compare models + force rerun with any model  
🔄 **Execution Replay** - Expand trace to see every step  
🌐 **Backend Integration** - Connects to Pentamind API  

---

## Quick Start

### 1. Install Dependencies

```bash
cd frontend
npm install
```

### 2. Start Backend (Required)

```bash
cd ../backend
source venv/bin/activate
export MODEL_ACCESS_KEY="your-do-key"
export PERPLEXITY_API_KEY="your-perplexity-key"  # Optional
export GEMINI_API_KEY="your-gemini-key"  # Optional
python3 -m uvicorn main:app --reload
```

### 3. Start Frontend

```bash
cd frontend
npm run tauri dev
```

---

## Configuration

### Backend URL

Default: `http://localhost:8000`

To change, update `src/App.tsx`:
```typescript
const API_URL = 'http://localhost:8000';
```

### Hotkey

Default: `Cmd+Shift+P` / `Ctrl+Shift+P`

To change, update `src/App.tsx` hotkey listener.

---

## Usage

### 1. Toggle Overlay
Press `Cmd+Shift+P` or click system tray icon

### 2. Enter Text
Paste or type your input in the text area

### 3. Select Task
Click one of the task buttons:
- 📝 Summarize
- 🔍 Research  
- 🧠 Solve
- ⚡ Code
- ✍️ Rewrite

### 4. Choose Mode
- **Best**: Highest quality (may be slower/costly)
- **Fast**: Quick results
- **Cheap**: Most cost-effective

### 5. Run Analysis
Click "Run Analysis" and watch the magic happen!

### 6. View Results
- **Timeline**: See execution steps lighting up
- **Response**: View the AI's answer
- **Scoreboard**: Compare models used
- **Replay**: Expand to see detailed trace

### 7. Force Rerun
Click the 🔄 button next to any model in the scoreboard to force rerun with that specific model.

---

## Development

### Run in Dev Mode
```bash
npm run tauri dev
```

### Build for Production
```bash
npm run tauri build
```

Output will be in `src-tauri/target/release/`

---

## Window Configuration

### Frameless Window
The window has no title bar - drag anywhere to move it.

### Always on Top
The window stays above all other windows.

### Transparency
Uses a dark semi-transparent background for modern look.

To modify window settings, edit `src-tauri/tauri.conf.json`:
```json
{
  "decorations": false,    // Frameless
  "transparent": true,     // Transparent background
  "alwaysOnTop": true,     // Always visible
  "resizable": true        // Can resize
}
```

---

## Tech Stack

- **Framework**: Tauri v2
- **UI**: React 19 + TypeScript
- **Styling**: Tailwind CSS 4
- **Icons**: Lucide React
- **Backend**: FastAPI (Python)

---

## Troubleshooting

### "Cannot connect to backend"
Make sure backend is running:
```bash
cd backend
python3 -m uvicorn main:app --reload
```

### "Hotkey not working"
Check if another app is using the same hotkey combination.

### "Window doesn't stay on top"
Check `tauri.conf.json` has `"alwaysOnTop": true`

### "Styles not loading"
```bash
npm install
npm run dev
```

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Cmd+Shift+P` / `Ctrl+Shift+P` | Toggle overlay |
| `Cmd+W` / `Ctrl+W` | Close overlay |
| `Enter` (in textarea) | Submit (with Cmd/Ctrl held) |

---

## Design Philosophy

**Dark Innovation Theme:**
- Dark slate backgrounds (#0a0e1a → #1e293b)
- Violet/Fuchsia accents (#8b5cf6, #d946ef)
- Glass morphism effects
- Smooth animations
- Glow effects on active elements

---

**Built for MLH DO Hackathon** 🚀
