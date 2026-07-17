# 🇨🇭 Swiss Knife v2.0

**The Ultimate Multi-Tool Platform** — Download, tag, convert, organize, analyze, and automate everything with an AI-powered brain.

```
╔══════════════════════════════════════════════════════════════════╗
║                    🇨🇭 SWISS KNIFE v2.0                          ║
╠══════════════════════════════════════════════════════════════════╣
║  [Brain]  [Memory]  [Vision]  [Pipeline]  [Kernel]  [Plugins]  ║
╠══════════════════╦══════════════════╦════════════════════════════╣
║  📥 Download     ║  🎵 Audio Tagger ║  👁️  Vision System        ║
║  🎬 Video        ║  🎶 Shazam-like  ║  🖼️  Image Analysis        ║
║  🎧 Audio        ║  🏷️  Auto-tag     ║  🔍 OCR                    ║
║  📁 Files        ║  📝 Lyrics       ║  🎯 Object Detection       ║
║  🌐 1000+ Sites  ║  🎨 Album Art    ║  🧠 AI Understanding       ║
╠══════════════════╬══════════════════╬════════════════════════════╣
║  🔄 Converter    ║  📂 Organizer    ║  🔧 System Tools           ║
║  📹 Video        ║  📺 TV Shows     ║  📊 System Info            ║
║  🎵 Audio        ║  🎬 Movies       ║  🌐 Network Utils          ║
║  🖼️  Images       ║  📸 Photos       ║  ⚡ Process Monitor        ║
╠══════════════════╩══════════════════╩════════════════════════════╣
║                    🧠 AI BRAIN SYSTEM                             ║
║         Multi-step reasoning • Memory • Learning • Planning       ║
╚══════════════════════════════════════════════════════════════════╝
```

---

## 🚀 Quick Start

### Installation

```bash
# 1. Clone or download the project
cd swiss_knife

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Install ffmpeg (required for media conversion)
# Ubuntu/Debian:
sudo apt install ffmpeg chromaprint-tools tesseract-ocr

# macOS:
brew install ffmpeg chromaprint tesseract

# Windows:
choco install ffmpeg chromaprint tesseract
```

### Basic Usage

```bash
# Download video from YouTube
python main.py download "https://youtube.com/watch?v=..."

# Download audio only (MP3)
python main.py download "https://youtube.com/watch?v=..." --audio-only --format mp3

# Auto-tag your music library (Shazam-like!)
python main.py tag ~/Music --auto-rename

# Analyze an image with AI vision
python main.py vision photo.jpg

# Convert video format
python main.py convert video.avi --format mp4

# Smart organize files
python main.py organize ~/Downloads --mode smart

# Create a workflow pipeline
python main.py pipeline "Download playlist and convert all to mp3"

# Ask the AI brain
python main.py brain "How do I batch download YouTube videos?"

# Interactive mode
python main.py interactive
```

---

## 🏗️ Architecture

### Micro-Kernel Plugin System
The core uses a micro-kernel pattern:
- **Minimal core** — Just the kernel, memory, and brain
- **Tools as plugins** — Each tool is self-contained and can be added/removed
- **Message passing** — Tools communicate through the kernel
- **Hook system** — Extensible event system

### Brain System
Human-like cognitive architecture:
- **Perception** → Understands what you're asking
- **Analysis** → Breaks down complex requests
- **Reasoning** → Multi-step logical thinking
- **Planning** → Creates action plans
- **Reflection** → Self-evaluates and improves
- **Memory** → Learns from experience

### Memory System
Multi-tier memory like the human brain:
- **Sensory** → Raw input buffer (very short-term)
- **Working** → Current context and focus
- **Short-term** → Recent interactions
- **Long-term** → Important knowledge (persistent)
- **Episodic** → Specific experiences
- **Semantic** → Facts and concepts
- **Procedural** → Learned skills/workflows

### Pipeline Planner
Automatically creates multi-step workflows:
1. You describe what you want in natural language
2. Brain analyzes and creates a plan
3. Pipeline executes steps in order
4. Parallel execution where possible
5. Error handling and retries built-in

---

## 📥 Universal Downloader

Download from 1000+ sites including YouTube, Spotify, SoundCloud, Vimeo, TikTok, Twitter, Instagram, Facebook, Reddit, and more.

```bash
# Download best quality video
python main.py download "https://youtube.com/watch?v=..."

# Download audio (MP3 320kbps)
python main.py download "URL" --audio-only --format mp3

# Download audio (WAV lossless)
python main.py download "URL" --audio-only --format wav

# Download audio (FLAC)
python main.py download "URL" --audio-only --format flac

# Download with subtitles
python main.py download "URL" --format mp4

# Download playlist
python main.py download "PLAYLIST_URL"

# Download and extract audio automatically
python main.py download "URL" -a -f mp3
```

**Features:**
- 🎬 Video: MP4, MKV, AVI, MOV, WebM (any quality up to 4K/8K)
- 🎵 Audio: MP3, WAV, FLAC, M4A, AAC, OGG, OPUS (any bitrate)
- 📝 Subtitles: Download and embed subtitles
- 🖼️ Thumbnails: Auto-download and embed
- 📋 Playlists: Download entire playlists
- 📊 Progress: Real-time download progress
- 🔴 Streams: Record live streams (HLS/DASH)

---

## 🎵 Audio Tagger (Shazam-like!)

The crown jewel — identifies unknown audio files like Shazam, then fetches complete metadata.

### The Problem
You have files named:
- `Track 01.mp3`
- `Unknown Artist - Song.mp3`
- `audio_recording_123.wav`

### The Solution
Swiss Knife will:
1. 🔊 **Listen** — Generate audio fingerprint (like Shazam does)
2. 🆔 **Identify** — Match against AcoustID database
3. 📋 **Fetch Metadata** — Artist, title, album, year, genre
4. 📝 **Fetch Lyrics** — Synced lyrics with timing (.lrc format)
5. 🎨 **Download Album Art** — High-quality cover image
6. 🏷️ **Embed Everything** — Tags + artwork + lyrics inside the file
7. 📝 **Rename** — "Track 01.mp3" → "Artist Name - Song Title.mp3"

```bash
# Tag all music in a directory
python main.py tag ~/Music

# Tag with auto-rename
python main.py tag ~/Downloads/Music --auto-rename

# The tool will:
# 1. Scan for audio files
# 2. Fingerprint each one (10 seconds sample)
# 3. Identify the song
# 4. Fetch metadata from MusicBrainz + Last.fm
# 5. Fetch synced lyrics from LRCLIB (free!)
# 6. Download album artwork from iTunes
# 7. Embed all tags + artwork + lyrics
# 8. Rename to "Artist - Title.mp3"
```

### Supported Formats
- MP3 (ID3v2.3/v2.4)
- FLAC (Vorbis comments)
- M4A (MP4 atoms)
- OGG (Vorbis comments)
- WMA

### Lyrics Sources
- **LRCLIB** — Free, synced lyrics, no API key needed
- **Genius** — Largest lyrics database (needs API key)
- **Musixmatch** — Synced lyrics (needs API key)

### Metadata Sources
- **AcoustID** — Audio fingerprinting (free API key)
- **MusicBrainz** — Comprehensive music metadata
- **Last.fm** — Artist info, tags, similar artists
- **iTunes** — Album artwork

---

## 👁️ Vision System

Actually **SEES** images, not just reads filenames.

```bash
# Describe an image
python main.py vision photo.jpg

# Extract text from image (OCR)
python main.py vision document.png --action read_text

# Full analysis
python main.py vision image.jpg --action analyze

# Batch process directory
python main.py vision ~/Photos --action describe
```

**Capabilities:**
- 📝 **Description** — Natural language description of image content
- 🔍 **OCR** — Extract text from images and documents
- 🎯 **Object Detection** — Identify objects in the scene
- 🏞️ **Scene Recognition** — Indoor/outdoor/urban/etc.
- 🎨 **Color Analysis** — Dominant colors
- 👥 **Face Detection** — Count and locate faces

**Two modes:**
1. **Local** (OpenCV) — Works offline, no API key
2. **AI** (GPT-4 Vision) — Much more capable, needs OpenAI API key

---

## 🔄 Media Converter

Convert between any media formats.

```bash
# Convert video to MP4
python main.py convert video.avi --format mp4

# Convert with preset
python main.py convert video.mp4 --preset web

# Convert audio to MP3
python main.py convert audio.wav --format mp3 --preset audio_mp3

# Convert to high-quality FLAC
python main.py convert audio.mp3 --format flac --preset audio_high

# Convert image
python main.py convert photo.png --format jpg
```

**Presets:**
- `mp4_h264` — Standard MP4 (compatible everywhere)
- `mp4_h265` — HEVC (smaller file size)
- `web` — Web-optimized (fast start)
- `mobile` — Mobile-optimized (smaller)
- `audio_high` — Lossless FLAC
- `audio_mp3` — High-quality MP3 320kbps
- `audio_aac` — AAC 256kbps
- `gif` — Animated GIF

---

## 📂 Smart Organizer

Intelligent file and media organization.

```bash
# Smart auto-detect organization
python main.py organize ~/Downloads --mode smart

# Organize TV shows
python main.py organize ~/Downloads/Shows --mode tv

# Organize movies
python main.py organize ~/Downloads/Movies --mode movies

# Organize music
python main.py organize ~/Downloads/Music --mode music

# Organize photos
python main.py organize ~/Downloads/Photos --mode photos
```

**TV Shows:**
```
Before: Game.of.Thrones.S01E02.1080p.mkv
After:  TV Shows/Game Of Thrones/Season 01/Game Of Thrones - S01E02.mkv
```

**Movies:**
```
Before: The.Matrix.1999.1080p.mp4
After:  Movies/The Matrix (1999)/The Matrix.mp4
```

---

## 🧠 Brain System

The AI brain understands natural language and can plan complex workflows.

```bash
# Quick question
python main.py brain "How do I download a YouTube playlist as MP3?"

# Complex request
python main.py brain "I want to download all videos from a playlist, extract audio, tag them, and organize by artist"

# The brain will:
# 1. Understand your intent
# 2. Plan the steps
# 3. Execute the pipeline
```

**Cognitive Modules:**
- 👁️ **Perception** — Understands your request
- 🔍 **Analysis** — Breaks down complex problems
- 🧮 **Reasoning** — Logical multi-step thinking
- 📋 **Planning** — Creates action plans
- 💭 **Reflection** — Self-evaluates quality
- 💡 **Creativity** — Novel solutions
- 💾 **Memory** — Learns from experience

---

## 📋 Pipeline System

Create and execute automated workflows.

```bash
# Natural language pipeline
python main.py pipeline "Download YouTube video, extract audio as MP3, tag it"

# The system auto-generates steps:
# Step 1: Validate URL
# Step 2: Fetch media info
# Step 3: Download & extract audio
# Step 4: Auto-tag the file
# Step 5: Verify output
```

**Features:**
- ✅ Automatic step generation
- ⚡ Parallel execution where possible
- 🔄 Retry on failure
- 📊 Progress tracking
- 💾 Resume capability (checkpoints)

---

## 🔧 All Tools

| Tool | Category | What It Does |
|------|----------|-------------|
| `universal_downloader` | Media | Download from 1000+ sites |
| `audio_tagger` | Audio | Shazam-like ID + auto-tag |
| `vision` | Vision | Actually see images |
| `converter` | Media | Convert any format |
| `file_manager` | Files | Organize, search, cleanup |
| `organizer` | Media | Smart media library |
| `system` | System | Monitor, network, utils |
| `web_scraper` | Network | Scrape websites, APIs |

---

## 🔌 Plugin Development

Create your own tools:

```python
from core.kernel import ToolBase, ToolMetadata, MicroKernel

class MyTool(ToolBase):
    metadata = ToolMetadata(
        name="my_tool",
        version="1.0.0",
        description="My custom tool",
        category="custom",
        tags=["my", "tool"],
    )
    
    def execute(self, *args, **kwargs):
        # Your tool logic here
        return {"result": "Hello from my tool!"}
    
    def health_check(self):
        return {"status": "healthy"}

# Register with kernel
kernel.register_tool(MyTool)

# Execute
result = kernel.execute("my_tool")
```

---

## ⚙️ Configuration

Create `config.yaml`:

```yaml
# Audio settings
audio:
  fingerprint_duration: 10
  acoustid_api_key: "your-key-here"
  lastfm_api_key: "your-key-here"
  genius_api_key: "your-key-here"
  auto_rename: true
  naming_pattern: "{artist} - {title}"

# Brain settings
brain:
  model: "gpt-4"
  api_key: "your-openai-key"
  temperature: 0.7
  reasoning_depth: "deep"

# Download settings
download:
  default_quality: "best"
  download_dir: "downloads"
  max_concurrent: 3

# Vision settings
vision:
  ocr_engine: "easyocr"
  object_detection: true
```

Or use environment variables:
```bash
export ACOUSTID_API_KEY="your-key"
export LASTFM_API_KEY="your-key"
export GENIUS_API_KEY="your-key"
export OPENAI_API_KEY="your-key"
```

---

## 🆓 Free API Keys

Many features work without API keys, but for best results:

| Service | Key | Free Tier |
|---------|-----|-----------|
| AcoustID | [Get Key](https://acoustid.org/api-key) | Yes |
| Last.fm | [Get Key](https://www.last.fm/api) | Yes |
| Genius | [Get Key](https://genius.com/api-clients) | Yes |
| OpenAI | [Get Key](https://platform.openai.com) | Paid (optional) |

**Without API keys:**
- ✅ Downloader works fully
- ✅ Vision works locally (OpenCV)
- ✅ Converter works fully
- ✅ File manager works fully
- ✅ Organizer works fully
- ⚠️ Audio tagger: basic filename heuristics only
- ⚠️ Brain: pattern matching (no deep reasoning)

---

## 🛠️ Development

### Project Structure
```
swiss_knife/
├── main.py                 # CLI entry point
├── core/                   # Core systems
│   ├── kernel.py          # Micro-kernel plugin system
│   ├── brain.py           # AI reasoning engine
│   ├── memory.py          # Multi-tier memory system
│   ├── pipeline.py        # Workflow orchestration
│   └── vision.py          # Image understanding
├── tools/                  # Tool plugins
│   ├── downloader.py      # Universal downloader
│   ├── audio_tagger.py    # Audio identification
│   ├── vision_tool.py     # Vision tool
│   ├── converter.py       # Media converter
│   ├── file_manager.py    # File operations
│   ├── system_tool.py     # System utilities
│   ├── web_scraper.py     # Web scraping
│   └── organizer.py       # Smart organizer
├── utils/                  # Utilities
│   ├── logger.py          # Colored logging
│   └── config.py          # Configuration
├── plugins/                # User plugins directory
├── downloads/              # Default download directory
└── memory/                 # Persistent memory storage
```

### Running Tests
```bash
# Basic functionality test
python -c "from main import SwissKnife; app = SwissKnife(); app.cmd_status()"

# Test individual tools
python -c "from tools.downloader import UniversalDownloader; d = UniversalDownloader(); print(d.health_check())"
python -c "from tools.audio_tagger import AudioTagger; t = AudioTagger(); print(t.health_check())"
```

---

## 🤝 Contributing

This is a modular platform — new tools can be added easily:

1. Create a new file in `tools/`
2. Inherit from `ToolBase`
3. Define `metadata`
4. Implement `execute()`
5. The kernel auto-discovers it!

---

## 📜 License

MIT License — free to use, modify, and distribute.

---

## 🙏 Credits

- **yt-dlp** — The amazing media downloader
- **AcoustID/Chromaprint** — Audio fingerprinting
- **MusicBrainz** — Open music encyclopedia
- **LRCLIB** — Free synced lyrics
- **OpenAI** — GPT-4 Vision capabilities

---

**Made with ❤️ by AI — Swiss Knife: One tool to rule them all.**
