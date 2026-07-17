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
| `eazzu.tools`         | new                                                                               | Shell, files, net, trade, dev, research tools |
| `eazzu.trading`       | `Bot2 / Deriv / deriv_scalper / deriv-perpetual-scalper / forexstream / …`        | Scalpers, signal bots, backtest engines       |
| `eazzu.dev`           | `Devtool/devtoolkit`                                                              | AI analyzer, debugger, runner, extractor      |
| `eazzu.net`           | `UltraVPN / Ip / ip_generator / network_toolkit_pro`                              | VPN core, IP utilities                        |
| `eazzu.media`         | `Tools/swiss_knife`                                                               | Media converters, downloaders, organizers     |
| `eazzu.tools.deep_research` | `deep-research`                                                             | Server + client deep-research pipeline        |
| `eazzu.web`           | `Neural-AI-ChatApp`                                                               | Static chat web UI served via `eazzu web`     |

---

## 🚀 Install

```bash
git clone https://github.com/EAZZU/EAZZU.git
cd EAZZU
pip install -e .            # base install (works on iSH)
pip install -e '.[full]'    # everything (pandas, rich, ws-client)
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
| `list_strategies`| Show bundled trading strategies                            |
| `backtest_strategy` | Prepare a backtest run                                  |
| `analyze_code`   | Static/AI code analysis via devtoolkit                     |
| `run_file`       | Execute a script through the vendored runner              |
| `web_search`     | Quick DuckDuckGo instant-answer lookup                     |

Tool calls are surfaced through a portable JSON protocol so **strict text-only
models work too** — no function-calling API required.

---

## 📈 Trading

```bash
eazzu trade list
eazzu trade backtest --strategy deriv_scalper --symbol R_75 --days 30
eazzu trade live --i-understand-risk
```

Live trading is intentionally guarded by the `--i-understand-risk` flag — the
underlying runners live under `eazzu.trading.*` and require your own Deriv API
token.

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
│   ├── trading/          # merged Deriv/Forex bots + trading system
│   ├── dev/toolkit/      # merged devtoolkit
│   ├── net/              # VPN core + IP utilities
│   ├── media/swiss_knife # media converters
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
