# 🧠 Neural.AI — Offline LLM Chat App

A **production-ready, mobile-first chatbot app** with local model support that runs **100% offline** in the browser. Built with pure JavaScript, HTML, and CSS — no build step, no framework, no server.

## ✨ Features

### Core
- 💬 **Chat interface** with markdown, code blocks, and streaming-style typing
- 🔒 **100% offline & private** — no internet needed after first load
- 📱 **Mobile-optimized** with side-bar navigation and safe-area insets
- 🎨 **Glassmorphism UI** with animated background orbs
- 💾 **Persistent storage** via IndexedDB (models, chats, files)
- ⚡ **PWA-ready** — installable as native mobile app

### AI Model Support
- 📦 **Import your own models**: `.gguf`, `.safetensors`, `.bin`, `.onnx`, `.pt`, `.pth`, `.ggml`, `.q4_0`, `.q4_1`, `.q5_0`, `.q5_1`, `.q8_0`
- 🔍 **Auto-detect** model format from file header (GGUF magic, safetensors JSON, ONNX)
- ✅ Activate / deactivate / export / delete
- 🧠 **Built-in Neural Engine** as fallback (Markov chain + intent matching + tokenizer)

### Content Generation
Fully offline pipelines for:
- 🎨 `/image <prompt>` — Procedural image synthesis (landscape, space, city, abstract, geometric, neural)
- 🌐 `/html <prompt>` — HTML page templates (landing, dashboard, form, portfolio, card, blog)
- 💻 `/code <prompt>` — Python & JavaScript code generation
- 🎵 `/music` — MIDI + WAV melody composition (Web Audio API)
- ▶️ `/run <code>` — Execute JavaScript in sandbox

### Code Sandbox
- **JavaScript** — Sandboxed execution with console capture
- **HTML** — Live iframe preview
- **Python** — Via Pyodide (cached after first load)

### AI Tools
- Image Generator, HTML Builder, Code Generator, MIDI Composer
- BPE-inspired Tokenizer visualizer
- Neural network micro-engine

## 🚀 Quick Start

```bash
# Serve locally with any static server
python3 -m http.server 8000
# Open http://localhost:8000
```

Or open `index.html` directly in a modern browser (Chrome/Safari/Firefox/Edge).

## 📁 Structure

```
local-ai-chat/
├── index.html              # Entry point
├── manifest.json           # PWA manifest
├── sw.js                   # Service worker (offline cache)
├── assets/icon.svg         # App icon
├── css/
│   ├── style.css           # Global + orbs + top bar
│   ├── sidebar.css         # Sidebar nav
│   ├── chat.css            # Chat messages & input
│   └── components.css      # Models/Sandbox/Tools/Settings
└── js/
    ├── storage.js          # IndexedDB wrapper
    ├── neural.js           # Neural engine (Markov + NN + tokenizer)
    ├── pipelines.js        # Image/HTML/Code/MIDI pipelines
    ├── models.js           # Model file manager
    ├── sandbox.js          # Safe code execution
    ├── chat.js             # Message handling
    ├── ui.js               # Toast/modal/markdown
    └── app.js              # Main controller
```

## 🎯 Command Reference

| Command | What it does |
|---|---|
| `/image <prompt>` | Generate an image procedurally |
| `/html <prompt>` | Build an HTML page |
| `/code <language> <task>` | Generate code (Python/JS) |
| `/music` or `/midi` | Compose a melody (playable + downloadable WAV/MIDI) |
| `/run <code>` | Execute JavaScript |

Or just chat naturally — intent is auto-detected.

## 📱 Installing as a Mobile App (PWA)

**iOS Safari:** Share → Add to Home Screen
**Android Chrome:** Menu → Install App / Add to Home Screen

The app then runs full-screen like a native mobile app.

## 🛡️ Privacy Statement

Every byte stays on your device:
- Models are stored in **IndexedDB** (Blob storage)
- Chats and files are stored locally
- No telemetry, no cloud, no accounts
- Works completely offline after first load

## ⚙️ Tech Stack

- **Vanilla JavaScript** (ES2020+)
- **IndexedDB** for persistent storage
- **Web Audio API** for music synthesis
- **Canvas API** for image generation
- **Service Worker** for offline caching
- **Web Speech API** for voice input (where supported)
- **Pyodide** for Python execution (optional, loaded on demand)

## 📝 License

MIT — Use it, ship it, remix it.
