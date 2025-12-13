# Pentamind UI Guide

## Visual Layout

```
┌─────────────────────────────────────────────────────────────────┐
│  ✨ Pentamind             Intelligent Multi-Model Routing    ✖  │
├─────────────────────────────┬───────────────────────────────────┤
│                             │                                   │
│  INPUT PANEL                │  RESULTS PANEL                    │
│  ───────────                │  ─────────────                    │
│                             │                                   │
│  Input Text                 │  ⚡ Execution Pipeline            │
│  ┌─────────────────────┐   │  ┌───────────────────────────┐   │
│  │                     │   │  │ ◉───◉───◉───◉───◉        │   │
│  │  Type or paste      │   │  │ classify → choose → ...   │   │
│  │  your text here...  │   │  └───────────────────────────┘   │
│  │                     │   │                                   │
│  │                     │   │  🧠 Task Analysis                 │
│  └─────────────────────┘   │  ┌───────────────────────────┐   │
│                             │  │ Intent: code              │   │
│  Task Type                  │  │ Format: text              │   │
│  ┌───┬───┬───┬───┬───┐    │  │ Confidence: 95%           │   │
│  │📝 │🔍 │🧠 │⚡ │✍️ │    │  └───────────────────────────┘   │
│  └───┴───┴───┴───┴───┘    │                                   │
│   Sum Res Sol Cod Rew      │  ✨ Processed by: llama3.3-70b   │
│                             │                                   │
│  Mode                       │  📄 Response                      │
│  ┌─────────────────────┐   │  ┌───────────────────────────┐   │
│  │ Best│Fast│Cheap │   │  │ Here's a binary search...  │   │
│  └─────────────────────┘   │  │                           │   │
│                             │  │ def binary_search(arr):   │   │
│  ┌─────────────────────┐   │  │     ...                   │   │
│  │  🚀 Run Analysis    │   │  └───────────────────────────┘   │
│  └─────────────────────┘   │                                   │
│                             │  🏆 Model Scoreboard              │
│                             │  ┌───────────────────────────┐   │
│                             │  │ 🏆 llama3.3-70b    150ms  │🔄│
│                             │  │    deepseek-r1     200ms  │🔄│
│                             │  └───────────────────────────┘   │
│                             │                                   │
│                             │  [ Show Execution Replay ]        │
└─────────────────────────────┴───────────────────────────────────┘
```

---

## Color Scheme

### Background Gradients:
```
Main: #0a0e1a → #1e293b → #0a0e1a
      (slate-950 → slate-900 → slate-950)
```

### Accent Colors:
```
Primary: #8b5cf6 (violet-500) → #d946ef (fuchsia-500)
Glow:    rgba(139, 92, 246, 0.5)
Success: #10b981 (green-500)
Warning: #f59e0b (yellow-500)
Error:   #ef4444 (red-500)
```

### Text:
```
Primary:   #ffffff (white)
Secondary: #cbd5e1 (slate-300)
Muted:     #64748b (slate-500)
Dimmed:    #475569 (slate-600)
```

---

## Component Breakdown

### 1. Header
```
┌─────────────────────────────────────────┐
│  ✨ Pentamind                        ✖  │
│     Intelligent Multi-Model Routing     │
└─────────────────────────────────────────┘
```
- Gradient icon (violet → fuchsia)
- Title in white
- Subtitle in slate-400
- Close button (X) in top right

---

### 2. Input Panel (Left)

#### Textarea:
```
┌────────────────────────────────┐
│ Type or paste your text...     │
│                                 │
│                                 │
│                                 │
└────────────────────────────────┘
```
- Dark slate background
- White text
- Violet focus ring
- Mono font

#### Task Buttons:
```
┌────┬────┬────┬────┬────┐
│ 📝 │ 🔍 │ 🧠 │ ⚡ │ ✍️ │
│Sum.│Res.│Sol.│Cod.│Rew.│
└────┴────┴────┴────┴────┘
```
- Selected: Gradient background (unique per task)
- Unselected: Dark slate, hover effect

#### Mode Toggle:
```
┌────────────────────────────┐
│ │ Best │ Fast │ Cheap │   │
└────────────────────────────┘
```
- Selected: Violet background + glow
- Unselected: Transparent + hover
- Pills inside dark container

#### Submit Button:
```
┌────────────────────────────┐
│    🚀 Run Analysis         │
└────────────────────────────┘
```
- Gradient: violet → fuchsia
- Glow effect on hover
- Loading state: spinner + "Processing..."

---

### 3. Results Panel (Right)

#### Timeline:
```
◉───◉───◉───◉───◉
classify choose execute verify
120ms   50ms   180ms   40ms
```
- Completed: Gradient circle + glow
- Active: Pulsing animation
- Pending: Grey circle
- Lines connect nodes

#### Task Analysis Card:
```
┌───────────────────────────┐
│ 🧠 Task Analysis          │
│ ────────────────────────  │
│ Intent:       code        │
│ Format:       text        │
│ Confidence:   95%         │
│ Citations:    Not needed  │
└───────────────────────────┘
```
- Dark slate background
- Grid layout
- Labels in slate-400
- Values in white/violet

#### Winner Badge:
```
┌───────────────────────────────┐
│ ✨ Processed by: llama3.3-70b │
└───────────────────────────────┘
```
- Gradient border
- Violet text
- Semi-transparent background

#### Response Viewer:
```
┌───────────────────────────┐
│ 📄 Response               │
│ ────────────────────────  │
│                           │
│ Here's the answer:        │
│                           │
│ def binary_search(...):   │
│     ...                   │
│                           │
└───────────────────────────┘
```
- Monospace font
- White text
- Scrollable
- Dark background

#### Scoreboard:
```
┌──────────────────────────────────┐
│ 🏆 Model Scoreboard              │
│ ────────────────────────────────│
│                                  │
│ 🏆 llama3.3-70b    150ms  low  🔄│
│    deepseek-r1     200ms  med  🔄│
│                                  │
└──────────────────────────────────┘
```
- Winner: Gradient background
- Others: Dark slate
- Latency in violet
- Cost tier color-coded
- Rerun button (🔄)

#### Replay Toggle:
```
┌──────────────────────────────────┐
│   [ Show Execution Replay ]      │
└──────────────────────────────────┘
```
- Dark button
- Expands trace below

#### Replay Viewer (Expanded):
```
┌──────────────────────────────────┐
│ Execution Trace                  │
│ ────────────────────────────────│
│                                  │
│ 1. classify_task      120ms      │
│    Model: llama3-8b-instruct     │
│    {"intent": "code", ...}       │
│                                  │
│ 2. choose_model       50ms       │
│    Model: None                   │
│    {...}                         │
│                                  │
└──────────────────────────────────┘
```
- Each step in card
- Step name in violet
- Model name in slate
- JSON data collapsed

---

## Animations

### 1. Glow Effect
```css
@keyframes glow {
  from { box-shadow: 0 0 10px rgba(139, 92, 246, 0.5); }
  to   { box-shadow: 0 0 30px rgba(139, 92, 246, 0.8); }
}
```

### 2. Pulse (Active Node)
```css
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50%      { opacity: 0.5; }
}
```

### 3. Spinner (Loading)
```css
@keyframes spin {
  from { transform: rotate(0deg); }
  to   { transform: rotate(360deg); }
}
```

---

## States

### Normal State:
- Overlay visible
- Input ready
- No response

### Processing State:
- Submit button disabled + spinner
- Timeline nodes animating
- "Processing..." message

### Complete State:
- Response visible
- Timeline complete (all green)
- Scoreboard populated
- Replay available

### Error State:
- Red alert banner
- Error message displayed
- Submit button enabled

---

## Hotkeys

| Key | Action |
|-----|--------|
| `Cmd+Shift+P` / `Ctrl+Shift+P` | Toggle overlay |
| `Cmd+W` / `Ctrl+W` | Close (if enabled) |
| `Cmd+Enter` / `Ctrl+Enter` | Submit (if in textarea) |
| `Esc` | Close overlay |

---

## Responsive Behavior

- **Window size**: 1200x800px
- **Minimum**: 800x600px
- **Panels**: 50/50 split
- **Overflow**: Scroll vertically
- **Text**: Wraps appropriately

---

## Dark Theme Details

### Glass Morphism:
```css
background: rgba(15, 23, 42, 0.8);
backdrop-filter: blur(12px);
```

### Gradient Borders:
```css
border: 1px solid transparent;
background: linear-gradient(135deg, #8b5cf6, #d946ef);
```

### Shadows:
```css
box-shadow: 0 0 20px rgba(139, 92, 246, 0.5);
```

---

## Icon Usage

- ✨ Pentamind logo (sparkles)
- ✖ Close button
- 📝 Summarize task
- 🔍 Research task
- 🧠 Solve task
- ⚡ Code task
- ✍️ Rewrite task
- 🚀 Submit button
- 🏆 Winner badge / Scoreboard
- 🔄 Rerun button
- 📄 Response viewer
- ⚠️ Error/warning

---

**The Result:** A beautiful, dark, innovative desktop overlay that feels like the future of AI interfaces! 🚀

