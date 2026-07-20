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

**v1.4.0** — Everything in v1.3 plus a full productivity suite: document
authoring, spreadsheets & analytics, presentations, notes & wiki, tasks &
plans, project & portfolio management, diagramming, workflow automation,
business intelligence & charts, instant-answer search, language & i18n, and
accessibility tooling — 90+ tools total, all pure-Python and iSH-friendly.

---

## ✨ What's inside

| Module                | What it does                                  |
| --------------------- | --------------------------------------------- |
| `eazzu.agent`         | ReAct-style tool-using LLM agent + autonomous loop + persistent memory |
| `eazzu.providers`     | 80+ AI providers behind one API               |
| `eazzu.tools`         | 90+ tools: shell, files, net, trade, dev, research, music, web, deriv, image, MCP, code, artifacts, memory + docs, data, slides, notes, tasks, projects, diagrams, workflows, BI, search, language, accessibility |
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

```bash
git clone https://github.com/jvrboy/EAZZU.git
cd EAZZU
pip install -e .            # base install (works on iSH)
pip install -e '.[full]'    # everything (pandas, rich, ws-client, pillow)
```

### iOS via iSH

```sh
apk add python3 py3-pip git
git clone https://github.com/jvrboy/EAZZU.git && cd EAZZU
sh ish/bootstrap.sh
```

---

## 🔑 Bring your own keys

```bash
eazzu keys set openai      sk-...
eazzu keys set anthropic   sk-ant-...
eazzu keys set groq        gsk_...
eazzu keys set deepseek    sk-...
eazzu keys set telegram_bot  123456:ABC-...   # for Telegram bot
eazzu keys list
```

Keys are encrypted with **Fernet** and stored under `~/.eazzu/keys.enc`.

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
eazzu analyze ./candles.json --indicator obv
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

Twelve new pure-Python tool modules expose 90+ tools total to the agent.
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
ezzu deriv candles R_75 --count 50 --granularity 60
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
