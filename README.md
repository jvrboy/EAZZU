# EAZZU

**Unified agentic developer + trading + AI + MCP toolkit** — one CLI, one
Python package, **bring your own API keys**. Ships everything you need to
chat with an LLM that can drive shell commands, files, network utilities,
dev-toolkits, MCP servers, a code runner, and a full library of
Deriv/Forex trading strategies — from a laptop or from an iPhone via
[**iSH**](https://ish.app).

```
 ███████╗ █████╗ ███████╗███████╗██╗   ██╗
 ██╔════╝██╔══██╗╚══███╔╝╚══███╔╝██║   ██║
 █████╗  ███████║  ███╔╝   ███╔╝ ██║   ██║
 ██╔══╝  ██╔══██║ ███╔╝   ███╔╝  ██║   ██║
 ███████╗██║  ██║███████╗███████╗╚██████╔╝
 ╚══════╝╚═╝  ╚═╝╚══════╝╚══════╝ ╚═════╝
```

**v1.5.0** — Everything in v1.4 plus a massive expansion: media editing & AI
media (crop, filters, adjustments, effects, generative fill, face retouch,
motion tracking, beat-sync, stabilization), creative & pro media tools
(layers, masking, color grading, node compositing, scopes), audio tools,
export & delivery, smart workflow tools, next-gen experimental tools
(3D reconstruction, avatars, AR, interactive video), visual automation
canvas with 23 node types, camera/surveillance tools, screenshot & screen
recording, DAW/music production (30 tools), 3D modeling & AI asset gen
(22 tools), AI coding assistant (24 tools), local AI model runner (20 tools),
75 cross-cutting tools (file mgmt, productivity, design, devops, security,
collaboration, analytics, hardware, learning, voice, gaming), full 14-stage
app-generation pipeline system + 13 additional domain pipelines, 55+ AI
provider registry with unlimited multi-key support, and 31 utility tools —
**400+ tools total**, all pure-Python and iSH-friendly.

**v1.5.1 — Quality-of-life update** adds the CLI polish a toolkit this size
deserves: a new `doctor` diagnostics command, tool-registry discovery
(`tools list|count|info|groups`), a persistent `config` command for defaults
(provider, model, color mode, web port, editor, shell policy), an `update`
helper that git-pulls and reinstalls in-place, a `commands` listing with
one-liner descriptions, bash/zsh/fish shell completion (one command
install), a `-V` short flag and `--no-color` (with `NO_COLOR` /
`EAZZU_NO_COLOR` env support), friendlier top-level error handling
(`EAZZU_DEBUG=1` for tracebacks), plus CI expanded to Python 3.13 with
syntax/lint/wheel-install checks and a fix for an indentation bug in
`eazzu.audio.engine`.

---

## ✨ What's inside

| Module                | What it does                                  |
| --------------------- | --------------------------------------------- |
| `eazzu.agent`         | ReAct-style tool-using LLM agent + autonomous loop + persistent memory |
| `eazzu.providers`     | 80+ AI providers behind one API               |
| `eazzu.tools`         | 400+ tools: shell, files, net, trade, dev, research, music, web, deriv, image, MCP, code, artifacts, memory + docs, data, slides, notes, tasks, projects, diagrams, workflows, BI, search, language, accessibility + media edit/AI/creative/pro, audio, export, smart, nextgen, automation canvas, surveillance, screenshot, screen record, DAW, 3D, AI coding, local AI, crosscut, pipelines, provider registry, utilities |
| `eazzu.mcp`           | MCP client framework (HuggingFace, TradingView, MT5, filesystem, fetch, GitHub) |
| `eazzu.trading`       | Scalpers, signal bots, backtest engines, real-time Deriv API, 22+ advanced indicators |
| `eazzu.bot`           | Telegram bot interface (long polling, per-user agents) |
| `eazzu.cli_ui`        | Pure-stdlib ANSI terminal renderer (panels, tables, spinners, progress bars) |
| `eazzu.dev`           | AI analyzer, debugger, runner, extractor      |
| `eazzu.net`           | VPN core, IP utilities                        |
| `eazzu.media`         | Media converters, downloaders, organizers, image tools |
| `eazzu.web`           | Static chat web UI served via `eazzu web`     |

---

## 🚀 Install

### Windows (CMD / PowerShell)
```powershell
# Install Python 3.9+ from python.org (check "Add Python to PATH"), then:
git clone https://github.com/jvrboy/EAZZU.git
cd EAZZU
pip install -e .            # base (works in CMD, PowerShell, Windows Terminal)
pip install -e .[all]       # install every optional dependency in one go
eazzu                       # launch the CLI anywhere
```
For Telegram bot control: `eazzu keys set telegram_bot <your-bot-token>` then `eazzu telegram`.

### macOS
```bash
brew install python3 git
git clone https://github.com/jvrboy/EAZZU.git && cd EAZZU
pip3 install -e .
pip3 install -e .[all]
eazzu
```

### Linux (Ubuntu / Debian / Fedora / Arch)
```bash
sudo apt install python3-pip git python3-tk scrot   # fedora: dnf install ... / arch: pacman -S ...
git clone https://github.com/jvrboy/EAZZU.git && cd EAZZU
pip install -e .
pip install -e .[all]
eazzu
```

### iOS via iSH (Alpine Linux on iPhone/iPad)
```sh
apk add python3 py3-pip git
git clone https://github.com/jvrboy/EAZZU.git && cd EAZZU
sh ish/bootstrap.sh      # installs minimal deps for iSH
eazzu                    # launch
```

### Google Colab
```python
!git clone https://github.com/jvrboy/EAZZU.git
%cd EAZZU
!pip install -q -e .[all]
import eazzu
# Use the agent programmatically:
from eazzu import Agent
agent = Agent(provider="auto")
agent.ask("build me a pomodoro timer app")
# Or launch the Telegram bot:
!eazzu telegram &
# Mount Google Drive for persistent keys/output:
from eazzu.tools.platform_tools import colab_mount
colab_mount()
```

### Any platform: one-shot install of optional groups
```bash
eazzu install --list          # see available groups (trading,image,pdf,slides,automation,web,audio,all)
eazzu install trading image   # install groups
eazzu install -y all          # install everything non-interactively
eazzu install --packages rich httpx   # arbitrary pip packages
```
Missing dependencies auto-install on first use when you set `EAZZU_AUTOINSTALL=1` (interactive shells); otherwise run `eazzu install <group>`.

### Launch at any time
Once installed with `pip install -e .`, the `eazzu` command is available globally in any shell:
```bash
eazzu              # banner + help
eazzu chat         # start agentic chat with auto-routing across all keys
eazzu telegram     # start the Telegram bot (control your computer from your phone)
eazzu doctor       # environment diagnostics
```

---

## 🔑 Bring your own keys

```bash
eazzu keys add gemini       AIza...          # append a key (supports many per provider)
eazzu keys add gemini       AIza...          # add as many as you want — 15, 50, …
eazzu keys add openrouter   sk-or-...
eazzu keys add cerebras     cjk-...
eazzu keys add nvidia_nim   nvapi-...
eazzu keys add groq         gsk_...
eazzu keys add deepseek     sk-...
eazzu keys add openai       sk-...           # any LLM provider works; all are rotated
eazzu keys add telegram_bot 123456:ABC-...   # for Telegram bot
eazzu keys list             # show providers + key counts
eazzu keys show gemini      # show masked keys (safe to paste in logs)
eazzu keys remove gemini 1  # remove the 1st key for gemini (1-indexed)
```

You can also set keys via comma-or-newline-separated environment variables
(e.g. `GEMINI_API_KEY=k1,k2,k3`) or by editing `~/.eazzu/keys.enc` — the
router automatically picks up every key it finds. Keys are encrypted at rest
with **Fernet**.

### 🔀 Multi-provider auto-routing (v1.6.0)

By **default** (`EAZZU_PROVIDER=auto`, the new default), EAZZU does **not**
pin to a single provider. Instead, a `ProviderRouter` discovers every LLM
provider that has at least one API key configured and treats each
`(provider, key)` pair as an independent endpoint.

Behavior you asked for:

* You say *"hi"* → the router picks a random healthy endpoint and responds.
  Gemini key #7, OpenRouter key #3, Cerebras key #12, NVIDIA NIM key #4 —
  whatever is healthy.
* If a key is **out of tokens / rate-limited / suspended / billing-exhausted
  / down**, the router instantly fails over to the next key on the next
  provider. It keeps switching until one works — **you do not need to
  retry**.
* Mid-task (during an autonomous `eazzu loop` run, a chat turn with tool
  calls, the Telegram bot, …) if a key burns out **mid-stream** the same
  transparent failover happens: the LLM call is re-issued to another
  endpoint and the task continues.
* Per-endpoint health is tracked in-process: strikes, cooldowns (honoring
  `Retry-After`), average latency, success rate. State persists to
  `~/.eazzu/router_stats.json` between sessions.
* Bad-request / invalid-argument errors (HTTP 400 from the LLM itself, not
  the key) do **not** trigger failover — those are prompt bugs, not
  provider/key problems.

Choose a routing strategy with `--router-strategy` (or `eazzu config set
router_strategy <name>`):

| Strategy     | Behavior                                                    |
| ------------ | ----------------------------------------------------------- |
| `random`     | Uniform pick over healthy endpoints (default, fastest spin-up) |
| `healthiest` | Weight by success rate (prefer the keys that "just work")   |
| `fastest`    | Weight by inverse average latency                           |
| `cheapest`   | Prefer providers with the lowest known per-token pricing    |

You can still pin a single provider the old way: `eazzu chat --provider
openai`, or `eazzu config set default_provider openai`.

Inspect and manage the router at the CLI:

```bash
eazzu router status              # table: endpoint, key (masked), model, ok/tot, latency, last error
eazzu router status --json       # machine-readable
eazzu router status --strategy cheapest
eazzu router test                # send a tiny PONG ping to every configured endpoint
eazzu router test --json         # per-endpoint latency/ok/error
eazzu router refresh             # re-scan env/keystore after adding keys
eazzu router reset               # clear all health state / cooldowns
```

Inside chat you can also type `/router` to see the live health table.

---

## 💻 Full computer control via CLI & Telegram (v1.7.0)

Every platform (Windows / macOS / Linux) is controllable through the agent and
a new `eazzu computer` CLI — and, crucially, through Telegram.

```bash
eazzu computer screenshot -o desktop.png     # take a screenshot (Pillow/mss/screencapture)
eazzu computer desktop                      # list desktop files with icons (📁/📄)
eazzu computer ls ~/Documents              # arbitrary directory listing
eazzu computer info file.txt                # size, dates, permissions
eazzu computer open resume.pdf              # OS default opener (start/xdg-open/open)
eazzu computer shell   "ipconfig"           # bash/sh (POSIX) or auto
eazzu computer cmd     "dir C:\\Users"      # Windows cmd.exe /c
eazzu computer powershell "Get-Process"     # Windows PowerShell (pwsh on POSIX)
eazzu computer processes                    # running processes (tasklist / ps)
eazzu computer window                       # title of foreground window
eazzu computer clipboard                    # read clipboard
eazzu computer clipboard --write "hi"       # write clipboard
eazzu computer alert "Done!"                # popup dialog (MessageBox/osascript/zenity)
eazzu computer ... keyboard_type/mouse_click/mouse_move  # HID via pyautogui if installed
```

All of these are registered as tools the agent can call autonomously, so
human-language requests like *"take a screenshot of my desktop, list every
file, and show me the active window"* work out of the box — and they work
**from Telegram**.

---

## 🤖 Telegram bot — full remote computer control

```bash
eazzu telegram                  # start the long-polling bot
eazzu telegram --check          # verify token and exit
eazzu telegram --allowed-users 12345,67890
```

Send `/menu` to get an inline-keyboard control panel with:

| Button          | What it does                                              |
| --------------- | --------------------------------------------------------- |
| 💬 Chat         | Natural-language agentic chat with full tool access       |
| 🖥️ Desktop      | Lists desktop files + shows active window                 |
| 📸 Screenshot   | Snap a screenshot and send it back as a photo             |
| 📁 Files        | Browse any directory with inline folders/files, tap to open |
| 💻 Shell        | Run cmd/PowerShell/bash (`/shell <cmd>`)                  |
| 📊 Status       | EAZZU version, platform, Python, provider info            |
| 🔀 Router       | Multi-provider routing health (keys alive/failed/cooled)  |
| 🛠️ Tools        | Lists the available computer-control tools                |

Keep-alive pings: while the agent is thinking the bot edits a "⏳ working…"
message every 2.5s so you see it's still alive. Screenshots come back as
photos, packaged apps come back as downloadable documents.

You can also talk to it in plain English: *"screenshot my desktop and list
every file on it"*, *"run `ipconfig`"*, *"what's on my clipboard?"* — it
dispatches the right tools and replies with the result.

---

## 🧱 Production-ready app builder (v1.7.0)

```bash
eazzu app create "pomodoro timer" --language html     # scaffold a real HTML/CSS/JS app
eazzu app create "discord bot"   --language python    # python package w/ main.py
eazzu app build  "landing page"  --language html     # create → run → screenshot → zip
eazzu app run    <dir>             # auto-detect start cmd, supports --background/--port
eazzu app fix    <dir> "<error>"   # append to FIX_LOG.txt for iterative fixing
eazzu app package <dir> --fmt zip  # bundle the project
```

The agent can iteratively write/fix/run/rerun until the app starts cleanly
(`create_app`/`run_app`/`fix_app`/`package_app`/`build_app` are all registered
as agent tools). When screenshots succeed (Playwright/Selenium installed;
otherwise a desktop screenshot is taken), they're surfaced to Telegram and
to the CLI.

---

## 🧬 Self-improving agent (v1.7.0)

Ask the agent to improve itself and it can safely clone its own repo into
a sandbox, make changes, run the full test suite (`pytest` + `compileall` +
`ruff`), commit, push to `main`, and copy the changes back into the live
install — gated behind explicit `self_*` tools so nothing happens without
your say-so:

```bash
eazzu self status                  # where am I installed? is it a git clone?
eazzu self clone                   # clone repo into ~/.eazzu/clones/eazzu-<ts>/
eazzu self test  <clone-dir>       # pytest -q + compileall + ruff E9/F
eazzu self install <clone-dir>     # pip install -e for smoke import
eazzu self commit <clone-dir> -m "..."
eazzu self push   <clone-dir>      # merges feature branch into main and pushes
eazzu self apply  <clone-dir>      # copy changed files back into live install
```

The agent also has all these as tools, so *"add a feature that does X,
test it, and push it"* is a single prompt.

---

## 🔌 freemodel.dev provider (v1.7.0)

Two new providers registered: `freemodel` (OpenAI-compatible, defaults to
`gpt-5.5` at `https://api.freemodel.dev/v1`) and `freemodel_codex`. Both
use the `FREEMODEL_API_KEY` env var / keystore entry, and are fully
compatible with the multi-key router:

```bash
eazzu keys add freemodel  fmk_...
eazzu keys add freemodel  fmk_...
eazzu router test           # PONG-ping every key, see which are alive
```

---

## 🛠️ CLI quality-of-life (v1.5.1)

```bash
eazzu doctor                       # environment diagnostics — Python, deps, keys, disk, network
eazzu doctor --fix                 # auto-fix fixable issues (e.g. create ~/.eazzu)
eazzu doctor --json                # machine-readable report

eazzu commands                     # list every subcommand with a one-line description
eazzu tools count                  # tool-count breakdown by group (400+ tools across ~50 groups)
eazzu tools list -q "trade"        # search tools by name/description substring
eazzu tools info ip_info           # show description/params/example for a single tool
eazzu tools groups                 # list tool groups with counts

eazzu config list                  # show persistent settings + defaults
eazzu config set default_provider groq
eazzu config set color never       # 'auto' | 'always' | 'never'
eazzu config set web_port 9000
eazzu config get web_port
eazzu config reset                 # reset ~/.eazzu/config.json to defaults

eazzu update                       # git pull --ff-only + pip install -e .
eazzu update --full -y             # reinstall with [full] extras, skip confirmation

eazzu --install-completion         # install bash/zsh/fish tab-completion (auto-detects shell)
eval "$(eazzu --_completion-script bash)"   # load completion in current shell only

eazzu -V                           # short version flag (also works after subcommands, e.g. `eazzu chat -V`)
eazzu --no-color ...               # disable ANSI colors (also honors $NO_COLOR / $EAZZU_NO_COLOR)
EAZZU_DEBUG=1 eazzu chat           # print full tracebacks if something throws
```

The config file lives at `~/.eazzu/config.json` (override with `$EAZZU_CONFIG`).

---

## 💬 Agentic chat

```bash
export EAZZU_PROVIDER=openai
eazzu chat                         # interactive
eazzu ask "list every python file under ./eazzu and count total lines"
```

The agent can call 80+ tools autonomously including shell, files, network,
web search, code execution, MCP servers, trading analysis, and more.

---

## 🔄 Autonomous agentic loop (v1.3)

The `loop` command runs the agent in an autonomous cycle — it plans,
executes, checks completion, and repeats until the task is done or the
max iteration count is reached.

```bash
eazzu loop "research the best EUR/USD scalping strategies and write a summary"
eazzu loop "analyze the codebase and create a refactor plan" --max-iterations 10
```

The loop uses `TASK_COMPLETE` and `TASK_BLOCKED` markers to determine when
to stop. Each iteration's reply, tool calls, and elapsed time are displayed.

---

## 🧠 Persistent working memory (v1.3)

JSON-backed persistent memory at `~/.eazzu/memory.json` with facts,
history, tasks, scratchpad, and artifacts.

```bash
eazzu memory snapshot               # full memory state
eazzu memory set api_endpoint https://api.example.com
eazzu memory get api_endpoint
eazzu memory facts                  # list all facts
eazzu memory history --limit 20     # recent history
eazzu memory tasks --status pending
eazzu memory scratchpad             # view scratchpad
eazzu memory set-scratchpad "working on auth flow..."
eazzu memory artifacts              # list stored artifacts
eazzu memory reset                  # clear all memory
```

In chat, use `/memory` to view the current memory snapshot.

---

## 🔌 MCP framework (v1.3)

Model Context Protocol client with stdio and HTTP transports. Six default
servers configured:

| Server       | Transport | Description |
| ------------ | --------- | ----------- |
| HuggingFace  | HTTP      | Search models/datasets/spaces/papers, model info, files, whoami |
| TradingView  | HTTP      | 16 indicators, 5 Pine Script strategies, chart/screener URLs, webhook receiver |
| MT5          | stdio     | MetaTrader 5 bridge (native or REST fallback): account, symbols, ticks, rates, positions, orders |
| filesystem   | stdio     | Read, write, list, search, delete, mkdir (sandboxed) |
| fetch        | stdio     | HTTP fetch, GET, POST |
| GitHub       | HTTP      | GitHub API adapter |

```bash
eazzu mcp list                      # list all configured servers
eazzu mcp status                    # ping all servers
eazzu mcp connect huggingface       # connect and list tools
eazzu mcp tools tradingview         # list tools on a server
eazzu mcp call huggingface search_models '{"query": "bert"}'
```

---

## 🐍 Code runner & interpreter (v1.3)

Subprocess-isolated Python execution plus persistent interactive sessions
with pickled namespaces.

```bash
eazzu code eval "print(2**10)"       # evaluate Python code
eazzu code python ./script.py        # run a Python file
eazzu code interactive "x=5" --session mysession
eazzu code interactive "x**2" --session mysession   # x persists
eazzu code interpret "sum(range(100))"
eazzu code script ./run.sh --interpreter bash
eazzu code shell "ls -la"            # run shell command
eazzu code sessions                  # list active sessions
```

---

## 📦 Artifacts creator (v1.3)

Create, store, and export structured project artifacts (HTML, Markdown,
JSON, Python scripts, configs) in persistent memory.

```bash
eazzu artifact html "My Page" "<h1>Hello</h1>"
eazzu artifact markdown "README" "# Title\n\nContent..."
eazzu artifact json config '{"key": "value"}'
eazzu artifact python my_script ./script.py
eazzu artifact create myapp html ./index.html
eazzu artifact list                  # list all artifacts
eazzu artifact get <id>               # get artifact by ID
eazzu artifact export <id> ./output.html
eazzu artifact export-all ./artifacts/
```

---

## 📈 Advanced technical analysis (v1.3)

22+ pure-Python technical indicators with no third-party dependencies.

```bash
eazzu analyze ./candles.json                              # full analysis
eazzu analyze ./candles.json --indicator vwap
eazzu analyze ./candles.json --indicator williams --period 14
eazzu analyze ./candles.json --indicator mfi --period 14
eazzu analyze ./candles.json --indicator cci --period 20
ezzu analyze ./candles.json --indicator obv
eazzu analyze ./candles.json --indicator aroon --period 25
eazzu analyze ./candles.json --indicator cmo --period 14
eazzu analyze ./candles.json --indicator trix --period 12
eazzu analyze ./candles.json --indicator keltner
eazzu analyze ./candles.json --indicator donchian --period 20
eazzu analyze ./candles.json --indicator heikin
eazzu analyze ./candles.json --indicator renko
eazzu analyze ./candles.json --indicator pivot --method camarilla
eazzu analyze ./candles.json --indicator mtf
```

Indicators: VWAP, VWMA, Hull MA, Keltner Channels, Donchian Channels,
ATR, Williams %R, MFI, CCI, OBV, Aroon, CMO, TRIX, DEMA, TEMA, ZigZag,
Heikin-Ashi, Renko, Pivot Points (classic/Camarilla/Woodie), Correlation,
Multi-timeframe analysis, and full_analysis (all at once).

---

## 🌐 Web research & any-site auth (v1.3)

Enhanced research pipeline with multi-query deep search, article extraction,
and authentication to any site.

```bash
eazzu research "transformer architecture explained" --max-sources 5

# Authenticate to any site (form login, token, or custom header)
# Then make authenticated requests
```

Agent tools: `deep_search`, `research_topic`, `site_login`, `site_request`,
`list_site_sessions`, `site_logout`, `extract_article`, `batch_fetch`.

Site auth supports three methods:
- **form**: POST credentials as form data, captures cookies
- **token**: Store a bearer token for later requests
- **header**: Store a custom auth header (e.g. `X-API-Key: ...`)

---

## 🤖 Telegram bot (v1.3)

Lightweight Telegram bot that exposes the EAZZU agent through chat. Uses
stdlib urllib for the Telegram Bot API (no third-party deps).

```bash
# Set your bot token (from @BotFather)
eazzu keys set telegram_bot 123456:ABC-DEF...

# Verify the token
eazzu telegram --check

# Run the bot (blocks until Ctrl-C)
eazzu telegram

# Restrict to specific Telegram user IDs
eazzu telegram --allowed-users 123456789,987654321

# Use a different LLM provider
eazzu telegram --provider anthropic --model claude-3-opus
```

Bot commands: `/start`, `/reset`, `/help`, `/tools`. Each user gets their
own agent instance for conversation continuity.

---

## 📈 Trading intelligence

EAZZU packages a technical-analysis knowledge base under
`eazzu/trading/knowledge/`.

```bash
eazzu trade knowledge
eazzu trade analyze --candles ./candles.json --symbol R_75 --timeframe 5m
eazzu trade signal --candles ./candles.json --symbol R_75 --timeframe 5m \
  --ledger ~/.eazzu/signal_ledger.json
eazzu trade track summary --ledger ~/.eazzu/signal_ledger.json
eazzu trade track resolve SIGNAL_ID --candles ./future-candles.json \
  --ledger ~/.eazzu/signal_ledger.json
eazzu trade list
eazzu trade backtest --strategy deriv_scalper --symbol R_75 --days 30
```

> Generated signals are educational, analysis-only outputs.

---

## 📝 Productivity suite (v1.4)

Twelve pure-Python tool modules expose 90+ tools to the agent.
No external runtime required — everything works on iSH/Alpine.

| Module | Tools | What it does |
| ------ | ----- | ------------ |
| `eazzu.tools.docs_tools` | `doc_*` | Document authoring: text formatting, styles, templates, alignment, page layout, TOC, footnotes, word count, readability, export (md/txt/html/pdf) |
| `eazzu.tools.data_tools` | `data_*` | Spreadsheets & analytics: safe formula evaluator, cell lookup, filter/sort, group-by aggregation, pivot tables, descriptive stats, moving averages, linear regression, XLOOKUP, CSV parse |
| `eazzu.tools.slides_tools` | `slides_*` | Presentations: deck builder, themes, transitions/animations, design suggestions, export to HTML/Markdown/JSON/PPTX, outline import |
| `eazzu.tools.notes_tools` | `notes_*` | Knowledge capture: notebooks, sections, pages, tags, full-text + tag search, wiki-links, JSON-persisted |
| `eazzu.tools.tasks_tools` | `task_*`, `plan_*` | To-do & planning: lists, due dates, priorities, recurrence, subtasks, My Day, Kanban plans with buckets |
| `eazzu.tools.projects_tools` | `project_*` | Project management: dependencies (FS/SS/FF/SF), Gantt data, critical path, baselines, variance, earned value (CPI/SPI), resource leveling |
| `eazzu.tools.diagram_tools` | `diagram_*` | Diagramming: Mermaid flowchart/sequence/ERD/Gantt/mindmap/state/class, Graphviz DOT, swimlanes, fishbone |
| `eazzu.tools.workflow_tools` | `workflow_*` | Automation engine: triggers, conditions, approvals, delays, loops, retries, run history |
| `eazzu.tools.bi_tools` | `bi_*` | Business intelligence: SVG charts (bar/line/pie/doughnut/scatter/gauge/funnel), KPI cards, dashboards, natural-language Q&A over data |
| `eazzu.tools.search_tools` | `search_*` | Instant answers: math, unit & currency conversion, definitions, time, web search via fetcher |
| `eazzu.tools.language_tools` | `lang_*` | Global & i18n: translation requests, RTL/bidi, Unicode normalization, script detection, furigana/pinyin, localized date/number/currency, proofreading |
| `eazzu.tools.accessibility_tools` | `a11y_*` | Accessibility: WCAG contrast checking, alt-text suggestions, reading-order analysis, keyboard & ARIA audits, color-blind simulation |

All modules follow the existing `TOOLS: list[dict]` convention and are
registered in `eazzu/tools/__init__.py` automatically.

---

## 🎬 Media & AI media suite (v1.5)

Seventeen new tool modules covering media editing, AI-powered media,
creative composition, pro video tools, audio, export, smart workflows,
next-gen experimental tools, automation canvas, surveillance, screenshots,
screen recording, DAW, 3D modeling, AI coding, local AI, cross-cutting tools,
pipelines, provider registry, and utilities — 300+ new tools.

| Module | Tools | What it does |
| ------ | ----- | ------------ |
| `media_edit_tools` | `media_*` | Crop, filters, adjustments, effects, background removal/change, trim, manipulation, merge, blend, opacity, object removal, texturing |
| `media_ai_tools` | `ai_*` | Generative fill/replace, text-to-image/video, image-to-video, face retouch/swap, rotoscoping, auto-reframe, motion tracking, speech-to-text, voiceover, lip sync, silence detect, scene detect, beat-sync, Ken Burns, depth map, relight, sky replace, weather effects, time remap, frame interpolate, stabilize, deflicker |
| `media_creative_tools` | `creative_*` | Layer system, masking, blend-if, vector shapes, text/typography, stickers/GIFs, transitions, split screen, chroma key, duotone, vignette, grain engine |
| `media_pro_tools` | `pro_*` | Curves/levels, scopes (waveform/vectorscope/RGB parade), match frame, node compositing, proxy workflow, batch processing, presets/templates, version history, collaboration, cloud render |
| `media_audio_tools` | `audio_*` | Ducking, noise removal, voice enhance, mixer (EQ/compressor/reverb), music generation, SFX library |
| `media_export_tools` | `export_*` | Multi-format export, platform presets, HDR, bitrate/codec control, watermark, direct publish |
| `media_smart_tools` | `smart_*` | Prompt-to-edit, auto-edit, highlight reel, content search, emotion tagging, copyright check, accessibility check |
| `media_nextgen_tools` | `nextgen_*` | 3D reconstruction (NeRF), avatar gen, AR preview, interactive video, multimodal reference, semantic timeline, auto storyboard, style lock |
| `automation_canvas_tools` | `canvas_*` | 23 node-based automation tools: create canvas, add/connect nodes, conditional branching, data merge, webhook listener, scheduler, error handler, sub-workflows, env manager, version control, approval steps, rate limiter, queue, batch, event bus, marketplace, AI suggest, data transform, idempotency, execution history, cost estimator, workflow-to-API |
| `surveillance_tools` | `surveillance_*` | 22 camera/surveillance tools: dashboard, motion zones, object filter, face recognition, plate reader, intercom, timeline, storage, streaming, night vision, PTZ, snapshot, privacy mask, alerts, timelapse, access control, relay, AI summary, anomaly detection, health monitor, cross-camera tracking, outdoor mode |
| `screenshot_tools` | `screenshot_*` | 20 screenshot tools: capture modes, delayed, multi-monitor, annotate, auto-blur, OCR, upload, history, auto-crop, color picker, compare, batch, workspace, clipboard, redact, to-markdown, filename, chained, sticker, perspective |
| `screen_record_tools` | `record_*` | 21 screen recording tools: start/stop, keystroke viz, green screen, cursor highlight, zoom-follow, trim/split/merge, silence remove, filler cut, chapter markers, transcription, face tracking, multi-scene, region lock, draw/annotate, controls, multi-export, adaptive bitrate, bookmark, caption burn, tutorial converter, face blur |
| `daw_tools` | `daw_*` | 30 music production tools: timeline, stem separation, chord suggest, key/tempo detect, live loop, MIDI humanize, modular synth, sidechain, pitch correct, time stretch, mixing assistant, mastering, reference match, sample search, drum groove, freeze, comping, video scoring, spatial audio, collaboration, controller map, latency report, sample convert, loop detect, session template, voice-to-instrument, beat slice, granular, spectral edit, noise reduction |
| `three_d_tools` | `three_d_*` | 22 3D modeling tools: text-to-mesh, image-to-mesh, retopology, UV unwrap, PBR texture, rig, motion retarget, LOD, decimate, voxel-to-mesh, photogrammetry, sculpt, material graph, lighting, turntable, export, physics sim, blendshape, hair groom, terrain, style transfer, to-lineart |
| `ai_coding_tools` | `code_*` | 24 AI coding tools: repo chat, inline complete, refactor, test gen, bug reproducer, commit msg, PR review, vuln scan, codebase Q&A, migration, dead code, doc gen, regex builder, SQL builder, API mock, agentic runner, sandbox, translate, profiler, complexity score, arch diagram, terminal explain, env setup, snapshot |
| `local_ai_tools` | `local_ai_*` | 20 local AI tools: download, quantize, dashboard, routing, offline, RAG, prompt profiles, fine-tune, LoRA, prompt library, API endpoint, memory, embeddings, STT/TTS, vision, batch, context summarize, benchmark, model card, update check |
| `crosscut_tools` | various | 75 cross-cutting tools across 13 categories: file mgmt, productivity, content creation, design, devops, security, collaboration, universal AI, analytics, hardware, learning, voice, gaming |
| `pipeline_tools` | `pipeline_*` | 32 pipeline tools: 14-stage app generation (intake → delivery), cross-cutting concerns (orchestrator, memory, guardrails, observability, budget, human-loop, retry, versioning, feedback), optional extensions (deploy, app-store, i18n, a11y, monetization, analytics, SEO, marketing), and `pipeline_run_all` |
| `pipeline_extra_tools` | `pipeline_*` | 13 additional domain pipelines: data analysis, content creation, research, security audit, migration, onboarding, compliance, devops, ML training, customer support, hiring, product launch, incident response |
| `provider_registry_tools` | `provider_*` | 12 provider registry tools: list 55+ providers, add/remove/rotate/test unlimited API keys per provider, get config, set default, get usage, categories, add custom, health check |
| `extra_tools` | `extra_*` | 31 utility tools: QR/barcode gen, password gen, UUID gen, hash compute, base64/URL codec, JSON formatter, CSV<->JSON, Markdown<->HTML, color picker, lorem ipsum, chronometer, world clock, unit converter, mortgage/BMI/tip calc, random picker, text diff/stats, slug gen, cron parser, regex tester, ASCII art, morse code, ROT13, binary codec |

---

## 🛠  Dev toolkit

```bash
eazzu dev analyze ./src
eazzu dev run scripts/hello.py
```

---

## 🌐 Network + web UI

```bash
eazzu net ip 8.8.8.8
eazzu net dns example.com
eazzu net http https://api.github.com
eazzu web --port 8787          # serves the bundled Neural chat webapp
```

---

## 📊 Real-time forex data (Deriv public API)

No API token required for market data (app_id 1089).

```bash
eazzu deriv ping
eazzu deriv symbols
eazzu deriv tick frxEURUSD
eazzu deriv candles R_75 --count 50 --granularity 60
eazzu deriv rates --base USD
eazzu deriv collect-ticks R_100 --count 20
eazzu deriv snapshot --symbols frxEURUSD,frXGBPUSD,R_75
```

---

## 🎵 Music suite

```bash
eazzu music melody --key C --scale minor --mood sad --bars 8
eazzu music chords --key G --style jazz --bars 4
eazzu music drums --genre trap --steps 16
eazzu music bass --key F --scale minor --genre dnb --bars 4
eazzu music structure --genre house
eazzu music scales
eazzu music euclidean --steps 16 --pulses 5 --rotation 2
eazzu music analyze ./audio.json
```

---

## 🖼  Image suite

```bash
eazzu image gradient --width 512 --height 512 --direction diagonal --color1 10,20,90 --color2 200,180,255
eazzu image plasma --width 512 --height 512 --scale 0.03
eazzu image mandelbrot --width 512 --height 512 --max-iter 120 --zoom 2 --cx -0.745
eazzu image noise --width 256 --height 256 --seed 7
eazzu image checkerboard --width 256 --height 256 --cells 10
eazzu image pil
```

---

## 🌍 Web access tools

```bash
eazzu webtools get https://example.com
eazzu webtools extract https://en.wikipedia.org/wiki/Forex
eazzu webtools links https://news.ycombinator.com
eazzu webtools meta https://github.com
eazzu webtools search "deriv api documentation"
eazzu webtools json https://api.github.com/repos/jvrboy/EAZZU
eazzu webtools download https://example.com/file.zip ./file.zip
eazzu webtools url https://user:pass@example.com:8080/path?q=1#frag
```

---

## 🎨 Enhanced CLI UI (v1.3)

Pure-stdlib ANSI terminal renderer — panels, tables, progress bars,
spinners, trees, status lines, and colored output without any third-party
dependencies. Degrades gracefully on terminals without ANSI support.

---

## 🧪 Tests

```bash
pip install pytest
pytest -q
```

---

## 🗂  Project layout

```
EAZZU/
├── eazzu/
│   ├── agent/            # tool-using LLM loop + autonomous loop + memory
│   ├── providers/        # 80+ AI providers
│   ├── tools/            # tool registry (mcp, code, artifacts, memory, ...)
│   │   ├── docs_tools.py       # document authoring & export (v1.4)
│   │   ├── data_tools.py       # spreadsheets, formulas, pivot, stats (v1.4)
│   │   ├── slides_tools.py     # presentations & decks (v1.4)
│   │   ├── notes_tools.py      # notebooks & wiki (v1.4)
│   │   ├── tasks_tools.py      # to-do & Kanban plans (v1.4)
│   │   ├── projects_tools.py   # PM, Gantt, EVM, baselines (v1.4)
│   │   ├── diagram_tools.py    # Mermaid & Graphviz generators (v1.4)
│   │   ├── workflow_tools.py   # automation engine (v1.4)
│   │   ├── bi_tools.py         # SVG charts, KPIs, dashboards, NLQ (v1.4)
│   │   ├── search_tools.py     # instant answers & conversions (v1.4)
│   │   ├── language_tools.py   # i18n, bidi, phonetic guides (v1.4)
│   │   └── accessibility_tools.py  # WCAG, alt-text, audits (v1.4)
│   ├── mcp/              # MCP client framework + 6 default servers
│   ├── trading/          # Deriv API, MT5 bridge, advanced analysis, intelligence
│   ├── bot/              # Telegram bot interface
│   ├── audio/            # music production suite + advanced_music DSP
│   ├── dev/              # dev toolkit (analyzer, debugger, runner, extractor)
│   ├── net/              # VPN core + IP utilities
│   ├── media/            # media converters + image tools
│   ├── web/              # static chat web UI
│   ├── cli_ui.py         # pure-stdlib ANSI terminal renderer
│   ├── cli.py            # unified `eazzu` CLI
│   └── __main__.py
├── ish/
├── tests/
├── pyproject.toml
└── README.md
```

---

## 📜 License

MIT — merged & rebuilt from the user-supplied source archives.
