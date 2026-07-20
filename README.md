# EAZZU

**Unified agentic developer + trading + AI toolkit** — one CLI, one Python
package, **bring your own API keys**. Ships everything you need to chat with
an LLM that can drive shell commands, files, network utilities, dev-toolkits
and a full library of Deriv/Forex trading strategies — from a laptop or from
an iPhone via [**iSH**](https://ish.app).

```
 ███████╗ █████╗ ███████╗███████╗██╗   ██╗
 ██╔════╝██╔══██╗╚══███╔╝╚══███╔╝██║   ██║
 █████╗  ███████║  ███╔╝   ███╔╝ ██║   ██║
 ██╔══╝  ██╔══██║ ███╔╝   ███╔╝  ██║   ██║
 ███████╗██║  ██║███████╗███████╗╚██████╔╝
 ╚══════╝╚═╝  ╚═╝╚══════╝╚══════╝ ╚═════╝
```

---

## ✨ What's inside

| Module                | Source (merged from)                                                              | What it does                                  |
| --------------------- | --------------------------------------------------------------------------------- | --------------------------------------------- |
| `eazzu.agent`         | new                                                                               | ReAct-style tool-using LLM agent              |
| `eazzu.providers`     | `ai_connector`                                                                    | 80+ AI providers behind one API               |
| `eazzu.tools`         | new                                                                               | Shell, files, net, trade, dev, research, music, web, deriv, image tools |
| `eazzu.trading`       | `Bot2 / Deriv / deriv_scalper / deriv-perpetual-scalper / forexstream / …`        | Scalpers, signal bots, backtest engines, **real-time Deriv API** |
| `eazzu.dev`           | `Devtool/devtoolkit`                                                              | AI analyzer, debugger, runner, extractor      |
| `eazzu.net`           | `UltraVPN / Ip / ip_generator / network_toolkit_pro`                              | VPN core, IP utilities                        |
| `eazzu.media`         | `Tools/swiss_knife`                                                               | Media converters, downloaders, organizers, **image tools** |
| `eazzu.tools.deep_research` | `deep-research`                                                             | Server + client deep-research pipeline        |
| `eazzu.web`           | `Neural-AI-ChatApp`                                                               | Static chat web UI served via `eazzu web`     |

---

## 🚀 Install

```bash
git clone https://github.com/EAZZU/EAZZU.git
cd EAZZU
pip install -e .            # base install (works on iSH)
pip install -e '.[full]'    # everything (pandas, rich, ws-client, pillow)
```

### iOS via iSH

```sh
apk add python3 py3-pip git
git clone https://github.com/EAZZU/EAZZU.git && cd EAZZU
sh ish/bootstrap.sh
```

`ish/bootstrap.sh` handles Alpine/musl-specific tweaks (build tools, pip
prefer-binary, `.eazzu` config dir) and pins to the base install so the
package works on-device with no compiler.

---

## 🔑 Bring your own keys

```bash
eazzu keys set openai      sk-...
eazzu keys set anthropic   sk-ant-...
eazzu keys set groq        gsk_...
eazzu keys set deepseek    sk-...
eazzu keys list
```

Keys are encrypted with **Fernet** (via `cryptography`) and stored under
`~/.eazzu/keys.enc` — never plain-text in your shell history.

Any of the 80+ providers registered under `eazzu.providers.providers`
(OpenAI, Anthropic, Groq, Mistral, DeepSeek, xAI, Together, Fireworks, Ollama,
LM Studio, OpenRouter, HuggingFace, Cohere, …) works — check with:

```bash
eazzu providers                     # grouped by category
eazzu providers --category llm      # just LLMs
```

---

## 💬 Agentic chat

```bash
export EAZZU_PROVIDER=openai       # default provider
eazzu chat                         # interactive
eazzu ask "list every python file under ./eazzu and count total lines"
```

The agent can call the following tools autonomously:

| Tool             | Purpose                                                    |
| ---------------- | ---------------------------------------------------------- |
| `shell`          | Run a whitelisted shell command (`EAZZU_SHELL_ALLOW=...`)  |
| `read_file`      | Read utf-8 text (scoped to `EAZZU_FS_ROOT`)                |
| `write_file`     | Write / append utf-8 text                                  |
| `list_dir`       | List entries (glob supported)                              |
| `http_get`       | Fetch a URL, return status + body                          |
| `dns_lookup`     | Resolve a hostname                                         |
| `ip_info`        | Classify an IP address                                     |
| `list_strategies`| Show bundled trading strategies and analysis capabilities  |
| `backtest_strategy` | Prepare a legacy backtest run without an order          |
| `list_trading_knowledge` | Validate and list all packaged trading-reference JSON documents |
| `analyze_market` | Analyze supplied OHLCV data across indicators, structure, price action, liquidity, volume, volatility, and regime |
| `generate_signal` | Produce and optionally record an analysis-only confluence signal from supplied OHLCV data |
| `resolve_signal` | Resolve a recorded signal against later candles and learn only from clear outcomes |
| `signal_tracker_summary` | Show signal outcomes and bounded per-evidence learning state |
| `analyze_code`   | Static/AI code analysis via devtoolkit                     |
| `run_file`       | Execute a script through the vendored runner              |
| `web_search`     | Quick DuckDuckGo instant-answer lookup                     |

### New in v1.2 — advanced tool suites

| Tool suite | Tools | Purpose |
| --- | --- | --- |
| **Music** (`eazzu.tools.music_tools`) | `ai_melody`, `ai_chord_progression`, `ai_drum_pattern`, `ai_arpeggio`, `ai_bass_line`, `ai_song_structure`, `find_scales`, `euclidean_rhythm`, `mixing_console_state`, `auto_master`, `generate_midi_file`, `analyze_audio`, `split_stems` | AI composition, synthesis, analysis, MIDI, mastering |
| **Advanced music** (`eazzu.audio.advanced_music`) | `granular_synthesize`, `spectral_dft`, `spectral_freeze`, `harmonic_analysis`, `detect_pitch_autocorrelation`, `generate_counterpoint`, `generate_fugue`, `markov_melody`, `chord_voicing`, `write_wav`, `apply_distortion`, `apply_chorus`, `apply_compressor`, `generate_polyrhythm`, `swing_quantize` | Extended DSP, spectral processing, generative algorithms |
| **Web access** (`eazzu.tools.web_tools`) | `http_get`, `http_post`, `http_head`, `extract_text`, `extract_links`, `extract_meta`, `web_search`, `fetch_json`, `download_file`, `url_info` | Fetch, scrape, search, extract content from the web |
| **Deriv real-time** (`eazzu.tools.deriv_tools`) | `deriv_ping`, `deriv_active_symbols`, `deriv_tick`, `deriv_ticks_history`, `deriv_candles`, `deriv_candles_range`, `deriv_proposal`, `deriv_website_status`, `deriv_time`, `deriv_exchange_rates`, `deriv_collect_ticks`, `deriv_collect_candles`, `deriv_price_snapshot` | Real-time forex / synthetic-index data via Deriv public API (app_id 1089) |
| **Image** (`eazzu.tools.image_tools`) | `generate_gradient`, `generate_noise`, `generate_checkerboard`, `generate_plasma`, `generate_mandelbrot`, `adjust_brightness/contrast/gamma`, `grayscale`, `invert`, `sepia`, `box_blur`, `sharpen`, `edge_detect`, `color_balance`, `threshold`, `resize_nearest/bilinear`, `rotate_90`, `flip`, `crop`, `histogram`, `average_color`, `dominant_color`, `brightness_stats`, `blend`, `overlay_text`, `encode_ppm/png`, `pil_*` | Procedural generation, filters, transforms, analysis, codecs |

Tool calls are surfaced through a portable JSON protocol so **strict text-only
models work too** — no function-calling API required.

---

## 📈 Trading intelligence

EAZZU now packages the uploaded technical-analysis knowledge base under
`eazzu/trading/knowledge/`. The twelve JSON documents remain intact and are
validated at runtime. Instrument profiles, session references, and the master
guide are surfaced as **reference context**; only supplied OHLCV candle data
is used to calculate an analysis or signal.

| Capability | What it does | Boundary |
| --- | --- | --- |
| Knowledge browser | Lists and validates all packaged reference JSON documents | Read-only; no document content is executed |
| Multi-method analysis | Combines trend, market structure, momentum, volatility, price action, liquidity, volume, regime, and reference context | Requires local caller-supplied OHLCV JSON; no price feed is fetched |
| Confluence signal generator | Requires multiple independent evidence domains, records every contribution, and abstains in weak or choppy conditions | Produces an analysis-only hypothesis, never a broker order or position size |
| Signal tracker | Resolves recorded signals against later candles and learns bounded evidence weights after clear outcomes | Ambiguous intrabar stop/target events are not used for learning |

```bash
# Inspect all packaged knowledge documents
eazzu trade knowledge

# Analyze local OHLCV candle data
eazzu trade analyze --candles ./candles.json --symbol R_75 --timeframe 5m

# Generate and record an analysis-only signal
eazzu trade signal --candles ./candles.json --symbol R_75 --timeframe 5m \
  --ledger ~/.eazzu/signal_ledger.json

# Inspect performance and adaptive evidence statistics
eazzu trade track summary --ledger ~/.eazzu/signal_ledger.json

# Resolve a recorded signal using candles that occurred after its entry
eazzu trade track resolve SIGNAL_ID --candles ./future-candles.json \
  --ledger ~/.eazzu/signal_ledger.json

# Legacy interfaces remain available
eazzu trade list
eazzu trade backtest --strategy deriv_scalper --symbol R_75 --days 30
eazzu trade live --i-understand-risk
```

The analysis and signal commands accept a top-level JSON candle list, or an
object containing `candles`, `data`, `history`, or `ohlcv`. Each candle must
include numeric `open`, `high`, `low`, and `close` values; `epoch`, `time`, or
`timestamp` and `volume` are optional. At least thirty valid candles are
required, while longer histories provide more stable long-trend context.

> Generated signals are educational, analysis-only outputs. They do not fetch
> market data, submit orders, calculate position sizes, or guarantee a trading
> outcome. Live trading remains separately guarded by `--i-understand-risk`.

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

EAZZU v1.2 ships a real-time Deriv API client (`eazzu.trading.deriv_api`) that
uses Deriv's default public application (app_id 1089) — **no API token
required** for market data. Tick, candle, symbol, proposal and exchange-rate
calls work out of the box. Streaming uses `websocket-client` when available
and falls back to a REST poll loop on iSH/Alpine.

```bash
eazzu deriv ping                       # verify connectivity
eazzu deriv symbols                     # list tradeable symbols
eazzu deriv tick frxEURUSD              # latest EUR/USD quote
eazzu deriv candles R_75 --count 50 --granularity 60   # 1-minute candles
eazzu deriv rates --base USD            # exchange rates
eazzu deriv collect-ticks R_100 --count 20             # stream 20 ticks
eazzu deriv snapshot --symbols frxEURUSD,frXGBPUSD,R_75
```

> Market-data only. No orders are placed and no account token is required.

---

## 🎵 Music suite

The full pure-Python audio suite (synthesis, sequencing, mixing, MIDI,
sampling, effects, mastering, visualization, stem separation, voice
synthesis, Vinny AI composer) is now exposed as agent tools and CLI commands.

```bash
eazzu music melody --key C --scale minor --mood sad --bars 8
eazzu music chords --key G --style jazz --bars 4
eazzu music drums --genre trap --steps 16
eazzu music bass --key F --scale minor --genre dnb --bars 4
eazzu music structure --genre house
eazzu music scales                     # list all scales
eazzu music euclidean --steps 16 --pulses 5 --rotation 2
eazzu music analyze ./audio.json        # BPM, key, LUFS, spectrum, transients
```

---

## 🖼  Image suite

A pure-stdlib image toolkit (procedural generation, filters, transforms,
analysis, PPM/PNG codecs) plus optional Pillow-enhanced operations.

```bash
eazzu image gradient --width 512 --height 512 --direction diagonal --color1 10,20,90 --color2 200,180,255
eazzu image plasma --width 512 --height 512 --scale 0.03
eazzu image mandelbrot --width 512 --height 512 --max-iter 120 --zoom 2 --cx -0.745
eazzu image noise --width 256 --height 256 --seed 7
eazzu image checkerboard --width 256 --height 256 --cells 10
eazzu image pil                         # check Pillow availability
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

## 🧪 Tests

```bash
pip install pytest
pytest -q
```

The smoke suite covers: CLI wiring, agent tool dispatch, provider registry,
and file/network tool safety (path escape, command allow-list).

---

## 🗂  Project layout

```
EAZZU/
├── eazzu/
│   ├── agent/            # tool-using LLM loop
│   ├── providers/        # 80+ AI providers (was `ai_connector`)
│   ├── tools/            # tool registry surfaced to the agent
│   ├── trading/          # legacy bots plus analysis-only intelligence modules
│   │   ├── intelligence/ # knowledge access, analysis, confluence signals, tracker
│   │   ├── knowledge/    # 12 packaged technical-analysis JSON documents
│   │   └── deriv_api.py  # real-time Deriv public API client
│   ├── audio/            # full music production suite + advanced_music DSP
│   ├── dev/toolkit/      # merged devtoolkit
│   ├── net/              # VPN core + IP utilities
│   ├── media/            # media converters + image tools (font5x7, codecs)
│   ├── tools/            # tool registry (music, web, deriv, image, ...)
│   ├── tools/deep_research
│   ├── web/chat/         # Neural chat web UI
│   ├── cli.py            # unified `eazzu` CLI
│   └── __main__.py
├── ish/
│   ├── bootstrap.sh      # Alpine/iSH installer
│   └── README.md
├── tests/
├── .github/workflows/ci.yml
├── pyproject.toml
└── README.md
```

---

## 📜 License

MIT — merged & rebuilt from the user-supplied source archives.
