"""``eazzu`` — one CLI to rule them all.

Sub-commands
------------
* ``chat``           interactive agentic chat (BYO API keys)
* ``ask``            one-shot agent query, prints answer & exits
* ``loop``           autonomous agentic loop — works until task is complete
* ``keys``           set / get / list / delete provider keys (encrypted)
* ``providers``      list every registered provider, optionally by category
* ``trade``          knowledge / analysis / signal generation / adaptive tracking
* ``deriv``          real-time forex / synthetic-index data from Deriv public API
* ``dev``            code analysis + run via vendored devtoolkit
* ``research``       deep web research pipeline
* ``net``            ip-info · dns · http-get
* ``web``            launch the bundled Neural chat web UI locally
* ``music``          AI composition, synthesis, analysis, MIDI, mastering
* ``image``          procedural generation, filters, transforms, codecs
* ``webtools``       fetch, search, scrape, extract web content
* ``mcp``            MCP server management (HuggingFace, TradingView, MT5, etc.)
* ``code``           code runner and interpreter (Python, shell, multi-language)
* ``artifact``       create and export project artifacts
* ``memory``         persistent working memory management
* ``telegram``       run the EAZZU Telegram bot
* ``analyze``        advanced technical analysis (22+ indicators)
* ``version``        print the installed version
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from typing import Optional

from eazzu.cli_ui import banner, panel, table, kv, status_line, rule, C, colorize, set_color


def _emit(obj) -> None:
    if isinstance(obj, (dict, list)):
        print(json.dumps(obj, indent=2, default=str))
    else:
        print(obj)


def _apply_globals(args) -> None:
    """Apply global flags (--no-color, config defaults, etc.) before dispatching."""
    # Color: explicit CLI flag beats env beats config.
    if getattr(args, "no_color", False):
        set_color(False)
    else:
        from eazzu.config import get_config
        cfg = get_config()
        mode = cfg.get("color", "auto")
        if mode == "never":
            set_color(False)
        elif mode == "always":
            set_color(True)
        else:
            set_color(None)


# -------------------------------------------------------------------- VERSION #
def cmd_version(_args) -> int:
    from eazzu import __version__
    print(f"eazzu {__version__}")
    return 0


def _resolve_agent_args(args):
    """Resolve provider/model/strategy from args > env > config."""
    provider = args.provider
    model = args.model
    strategy = getattr(args, "router_strategy", None)
    if provider is None:
        provider = os.environ.get("EAZZU_PROVIDER")
    if model is None:
        model = os.environ.get("EAZZU_MODEL")
    try:
        from eazzu.config import get_config
        cfg = get_config()
        if provider is None:
            provider = cfg.get("default_provider") or "auto"
        if model is None:
            model = cfg.get("default_model")
        if strategy is None:
            strategy = cfg.get("router_strategy", "random")
    except Exception:
        if provider is None:
            provider = "auto"
    return provider, model, strategy


# ---------------------------------------------------------------- CHAT / ASK #
def cmd_chat(args) -> int:
    from eazzu.agent import Agent
    provider, model, strategy = _resolve_agent_args(args)
    agent = Agent(provider=provider, model=model, router_strategy=strategy or "random")
    print(banner())
    if provider.lower() == "auto" and agent.router:
        print(f"Router: {strategy} · {agent.router.status()['total_endpoints']} endpoints, "
              f"{agent.router.status()['healthy']} healthy")
    else:
        print(f"Provider: {provider}  ·  Model: {model or '(default)'}")
    print(f"Tools: {len(agent.tools)} registered")
    print("Type '/exit' to quit · '/reset' to clear · '/tools' to list tools · '/memory' for memory · '/router' for health\n")
    while True:
        try:
            user = input("you › ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if not user:
            continue
        if user in {"/exit", "/quit"}:
            return 0
        if user == "/reset":
            agent.reset()
            print(status_line("history cleared", "ok"))
            continue
        if user == "/tools":
            for t in agent.tools:
                print(f"  {colorize('·', C.DIM)} {t['name']:24s} {t['description'][:60]}")
            continue
        if user == "/memory":
            from eazzu.agent.memory import WorkingMemory
            _emit(WorkingMemory().snapshot())
            continue
        if user == "/router":
            if agent.router:
                _emit(agent.router.status())
            else:
                print(status_line(f"router not active (fixed provider: {agent.provider})", "info"))
            continue
        print("bot › ", end="", flush=True)
        turn = agent.ask(user, on_token=lambda c: (sys.stdout.write(c), sys.stdout.flush()))
        if not turn.reply and not turn.tool_calls:
            print("(no response)")
        else:
            if agent.last_route and agent.last_route.get("attempts", 0) > 1:
                print(f"\n  {colorize('⤷', C.DIM)} routed via {agent.last_route['endpoint']} "
                      f"({agent.last_route['attempts']} attempts)", end="")
            print()
        for tc in turn.tool_calls:
            print(f"  {colorize('⤷', C.DIM)} tool `{colorize(tc['name'], C.CYAN)}` args={tc['args']}")


def cmd_ask(args) -> int:
    from eazzu.agent import Agent
    provider, model, strategy = _resolve_agent_args(args)
    agent = Agent(provider=provider, model=model, router_strategy=strategy or "random")
    turn = agent.ask(args.prompt)
    if not args.json:
        _emit(turn.reply)
        if agent.last_route:
            ep = agent.last_route.get("endpoint") or agent.last_route.get("provider")
            att = agent.last_route.get("attempts", 1)
            lat = agent.last_route.get("latency_ms", 0) or 0
            tag = f"[via {ep} · {att} attempt(s) · {lat:.0f}ms]"
            print(f"\n  {colorize(tag, C.DIM)}", file=sys.stderr)
        return 0
    payload = {
        "reply": turn.reply,
        "tool_calls": turn.tool_calls,
        "latency_ms": turn.latency_ms,
        "cost_usd": turn.cost_usd,
    }
    if agent.last_route:
        payload["route"] = agent.last_route
    _emit(payload)
    return 0


# --------------------------------------------------------------------- LOOP #
def cmd_loop(args) -> int:
    from eazzu.agent.loop import run_loop
    provider, model, strategy = _resolve_agent_args(args)
    print(banner())
    route_mode = f"router={strategy or 'random'}" if provider.lower() == "auto" else f"provider={provider}"
    print(f"Starting autonomous loop (max {args.max_iterations} iterations, {route_mode})\n")
    def on_step(step):
        it = step['iteration']
        print(f"\n{rule(f'Iteration {it}')}")
        print(f"  {colorize('Reply:', C.CYAN)} {step['reply'][:200]}...")
        if step['tool_calls']:
            for tc in step['tool_calls']:
                print(f"  {colorize('Tool:', C.YELLOW)} {tc['name']}")
        route = step.get("route")
        if route:
            print(f"  {colorize('Routed via:', C.DIM)} {route.get('endpoint', route.get('provider'))} "
                  f"({route.get('attempts', 1)} attempt(s))")
        print(f"  {colorize('Elapsed:', C.DIM)} {step['elapsed_s']}s")
    extra_kwargs = {}
    if provider.lower() == "auto":
        extra_kwargs["router_strategy"] = strategy or "random"
    result = run_loop(args.task, provider=provider, model=model,
                      max_iterations=args.max_iterations, on_step=on_step, **extra_kwargs)
    print(f"\n{rule('Result')}")
    _emit(result)
    return 0 if result["status"] == "complete" else 1


# ---------------------------------------------------------------------- KEYS #
def cmd_keys(args) -> int:
    from eazzu.providers import ConfigManager
    from eazzu.providers.router import mask_key, _split_keys
    cm = ConfigManager()
    action = args.action
    if action == "set":
        # set replaces all keys for a provider; for multi-key append use `add`.
        cm.set(args.provider, args.value)
        n = len(_split_keys(args.value))
        print(status_line(f"{n} key(s) stored for '{args.provider}' (encrypted at ~/.eazzu/)", "ok"))
    elif action == "add":
        n = cm.add_key(args.provider, args.value)
        print(status_line(f"added key for '{args.provider}' (total {n} keys for this provider)", "ok"))
    elif action == "get":
        # Print primary/first key (preserves backward compat).
        all_keys = cm.list_keys(args.provider)
        print(all_keys[0] if all_keys else "(not set)")
    elif action == "show":
        # Show masked keys for a provider (safe to print).
        all_keys = cm.list_keys(args.provider)
        if not all_keys:
            print(f"(no keys for '{args.provider}')")
            return 0
        for i, k in enumerate(all_keys, 1):
            src = "env" if _is_env_key(cm, args.provider, k) else "file"
            print(f"  {i:2d}. {mask_key(k)}  ({src})")
        print(f"\n{len(all_keys)} key(s) total for '{args.provider}'")
    elif action == "remove":
        target = args.value if hasattr(args, "value") and args.value else args.index
        remaining = cm.remove_key(args.provider, target)
        print(status_line(f"removed key; {len(remaining)} remain for '{args.provider}'", "ok"))
    elif action == "delete":
        cm.delete(args.provider)
        print(status_line(f"deleted all keys for '{args.provider}'", "ok"))
    elif action == "list":
        providers = cm.list_stored()
        if not providers:
            print("(no keys stored)")
            return 0
        from eazzu.cli_ui import table
        rows = []
        for p in providers:
            n = len(cm.list_keys(p))
            rows.append([p, str(n), mask_key((cm.list_keys(p) or [""])[0])])
        # Merge in env-only providers not in file.
        import os as _os
        from eazzu.providers.core.config import ENV_VAR_MAP
        seen = set(providers)
        for p, env in ENV_VAR_MAP.items():
            if p in seen:
                continue
            if _os.environ.get(env):
                ks = _split_keys(_os.environ[env])
                if ks:
                    rows.append([p, str(len(ks)), mask_key(ks[0]) + " (env)"])
        print(table(["Provider", "Keys", "First key"], rows))
    return 0


def _is_env_key(cm, provider: str, key: str) -> bool:
    """Check if `key` comes from an environment variable (vs encrypted keystore)."""
    import os as _os
    from eazzu.providers.core.config import ENV_VAR_MAP
    from eazzu.providers.router import _split_keys
    for env_name in (ENV_VAR_MAP.get(provider.lower()), f"{provider.upper()}_API_KEY"):
        if env_name and _os.environ.get(env_name):
            if key in _split_keys(_os.environ[env_name]):
                return True
    return False


# ----------------------------------------------------------------- PROVIDERS #
def cmd_providers(args) -> int:
    from eazzu import get_connector
    c = get_connector()
    if args.category:
        _emit(c.providers(args.category))
    else:
        _emit(c.categories())
    return 0


# --------------------------------------------------------------------- TRADE #
def _load_trade_candles(args):
    from eazzu.trading.intelligence.io import load_candles
    candles, metadata = load_candles(args.candles)
    symbol = getattr(args, "symbol", None) or metadata.get("symbol")
    timeframe = getattr(args, "timeframe", None) or metadata.get("timeframe")
    return candles, symbol, timeframe


def cmd_trade(args) -> int:
    action = args.trade_action
    if action == "list":
        from eazzu.tools.trade_tools import list_strategies
        _emit(list_strategies())
        return 0
    if action == "backtest":
        from eazzu.tools.trade_tools import backtest_strategy
        _emit(backtest_strategy(args.strategy, args.symbol, args.days))
        return 0
    if action == "knowledge":
        from eazzu.tools.trade_tools import list_trading_knowledge
        _emit(list_trading_knowledge())
        return 0
    if action in {"analyze", "signal"}:
        try:
            candles, symbol, timeframe = _load_trade_candles(args)
            if action == "analyze":
                from eazzu.trading.intelligence import TechnicalAnalysisEngine
                _emit(TechnicalAnalysisEngine().analyze(candles, symbol=symbol, timeframe=timeframe).to_dict())
            else:
                from eazzu.trading.intelligence import AdaptiveSignalTracker, SignalGenerator
                tracker = AdaptiveSignalTracker(args.ledger)
                result = SignalGenerator(tracker=tracker).generate(candles, symbol=symbol, timeframe=timeframe, min_confidence=args.min_confidence, risk_multiple=args.risk_multiple, reward_multiple=args.reward_multiple, expiry_bars=args.expiry_bars)
                if result.get("signal") and not args.no_record:
                    result["tracking"] = tracker.record_signal(result["signal"])
                else:
                    result["tracking"] = {"recorded": False, "reason": "no_signal" if not result.get("signal") else "record_disabled"}
                _emit(result)
            return 0
        except (OSError, ValueError) as exc:
            print(f"trade {action} failed: {exc}", file=sys.stderr)
            return 2
    if action == "track":
        from eazzu.trading.intelligence import AdaptiveSignalTracker
        tracker = AdaptiveSignalTracker(args.ledger)
        try:
            if args.track_action == "summary":
                _emit({"summary": tracker.summary(), "recent_signals": tracker.list_signals(args.limit)})
            elif args.track_action == "resolve":
                from eazzu.trading.intelligence.io import load_candles
                candles, _ = load_candles(args.candles)
                _emit(tracker.resolve_signal(args.signal_id, candles))
            else:
                return 1
            return 0
        except (OSError, ValueError, KeyError) as exc:
            print(f"trade track {args.track_action} failed: {exc}", file=sys.stderr)
            return 2
    if action == "live":
        if not args.i_understand_risk:
            print(status_line("refusing to start live trading without --i-understand-risk", "error"))
            return 2
        print("Live trading harness is intentionally stubbed here — configure your API credentials and use the dedicated runners under `eazzu.trading.*`.")
        return 0
    return 1


# ----------------------------------------------------------------------- DEV #
def cmd_dev(args) -> int:
    if args.dev_action == "analyze":
        from eazzu.tools.dev_tools import analyze_code
        _emit(analyze_code(args.path))
    elif args.dev_action == "run":
        from eazzu.tools.dev_tools import run_file
        _emit(run_file(args.path, " ".join(args.args or [])))
    return 0


# ------------------------------------------------------------------ RESEARCH #
def cmd_research(args) -> int:
    from eazzu.tools.research_tools_v2 import research_topic
    print(status_line(f"Researching: {args.query}", "info"))
    result = research_topic(args.query, max_sources=args.max_sources)
    _emit(result)
    return 0


# ----------------------------------------------------------------------- NET #
def cmd_net(args) -> int:
    from eazzu.tools import net_tools
    if args.net_action == "ip":
        _emit(net_tools.ip_info(args.address))
    elif args.net_action == "dns":
        _emit(net_tools.dns_lookup(args.hostname))
    elif args.net_action == "http":
        _emit(net_tools.http_get(args.url))
    return 0


# ----------------------------------------------------------------------- WEB #
def cmd_web(args) -> int:
    import http.server, socketserver
    from pathlib import Path
    root = Path(__file__).parent / "web" / "chat"
    if not root.exists():
        print("web app assets missing"); return 1
    os.chdir(root)
    port = args.port
    handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", port), handler) as httpd:
        print(f"Serving EAZZU web at http://localhost:{port}  (Ctrl-C to stop)")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print()
    return 0


# ------------------------------------------------------------------- DERIV #
def cmd_deriv(args) -> int:
    from eazzu.trading import deriv_api
    action = args.deriv_action
    if action == "ping":
        _emit(deriv_api.ping())
    elif action == "symbols":
        _emit(deriv_api.get_active_symbols())
    elif action == "tick":
        _emit(deriv_api.get_tick(args.symbol))
    elif action == "history":
        _emit(deriv_api.get_ticks_history(args.symbol, args.count, args.style))
    elif action == "candles":
        _emit(deriv_api.get_candles(args.symbol, args.count, args.granularity))
    elif action == "status":
        _emit(deriv_api.get_website_status())
    elif action == "time":
        _emit(deriv_api.get_time())
    elif action == "rates":
        _emit(deriv_api.get_exchange_rates(args.base))
    elif action == "proposal":
        _emit(deriv_api.get_proposal(args.contract_type, args.symbol, args.amount, args.basis, args.currency, args.duration, args.duration_unit))
    elif action == "collect-ticks":
        _emit(deriv_api.collect_ticks(args.symbol, args.count, args.timeout))
    elif action == "collect-candles":
        _emit(deriv_api.collect_candles(args.symbol, args.count, args.granularity, args.timeout))
    elif action == "snapshot":
        symbols = args.symbols.split(",") if args.symbols else []
        out = {}
        for s in symbols:
            r = deriv_api.get_tick(s.strip())
            out[s.strip()] = r.get("tick", r)
        _emit({"symbols": out, "count": len(out)})
    return 0


# ------------------------------------------------------------------- MUSIC #
def cmd_music(args) -> int:
    action = args.music_action
    if action == "melody":
        from eazzu.audio.vinny_extended import generate_ai_melody
        _emit({"melody": generate_ai_melody(args.key, args.scale, args.bars, args.mood, args.complexity)})
    elif action == "chords":
        from eazzu.audio.vinny_extended import generate_chord_progression
        _emit(generate_chord_progression(args.key, args.style, args.bars))
    elif action == "drums":
        from eazzu.audio.vinny_extended import generate_drum_pattern
        _emit({"pattern": generate_drum_pattern(args.genre, args.steps), "genre": args.genre})
    elif action == "bass":
        from eazzu.audio.vinny_extended import generate_bass_line
        _emit({"bass": generate_bass_line(args.key, args.scale, args.genre, args.bars)})
    elif action == "structure":
        from eazzu.audio.vinny_extended import generate_song_structure
        _emit({"structure": generate_song_structure(args.genre), "genre": args.genre})
    elif action == "scales":
        from eazzu.audio.engine import SCALES
        _emit({"scales": {k: list(v) for k, v in SCALES.items()}})
    elif action == "euclidean":
        from eazzu.audio.vinny_extended import generate_euclidean_rhythm
        _emit({"rhythm": generate_euclidean_rhythm(args.steps, args.pulses, args.rotation)})
    elif action == "analyze":
        with open(args.path) as f:
            data = json.load(f)
        from eazzu.tools.music_tools import analyze_audio
        _emit(analyze_audio(data.get("samples", []), data.get("sample_rate", 44100)))
    return 0


# ------------------------------------------------------------------- IMAGE #
def cmd_image(args) -> int:
    action = args.image_action
    if action == "gradient":
        from eazzu.tools.image_tools import generate_gradient
        c1 = tuple(int(x) for x in args.color1.split(","))
        c2 = tuple(int(x) for x in args.color2.split(","))
        _emit(generate_gradient(args.width, args.height, args.direction, c1, c2))
    elif action == "plasma":
        from eazzu.tools.image_tools import generate_plasma
        _emit(generate_plasma(args.width, args.height, args.scale))
    elif action == "mandelbrot":
        from eazzu.tools.image_tools import generate_mandelbrot
        _emit(generate_mandelbrot(args.width, args.height, args.max_iter, args.zoom, args.cx, args.cy))
    elif action == "noise":
        from eazzu.tools.image_tools import generate_noise
        _emit(generate_noise(args.width, args.height, args.scale, args.seed))
    elif action == "checkerboard":
        from eazzu.tools.image_tools import generate_checkerboard
        c1 = tuple(int(x) for x in args.color1.split(","))
        c2 = tuple(int(x) for x in args.color2.split(","))
        _emit(generate_checkerboard(args.width, args.height, args.cells, c1, c2))
    elif action == "pil":
        from eazzu.tools.image_tools import pil_available
        _emit(pil_available())
    return 0


# ---------------------------------------------------------------- WEBTOOLS #
def cmd_webtools(args) -> int:
    from eazzu.tools import web_tools
    action = args.webtools_action
    if action == "get":
        _emit(web_tools.http_get(args.url, args.timeout))
    elif action == "post":
        body = json.loads(args.json_body) if args.json_body else None
        _emit(web_tools.http_post(args.url, data=args.data, json_body=body, timeout=args.timeout))
    elif action == "extract":
        _emit(web_tools.extract_text(args.url, args.timeout))
    elif action == "links":
        _emit(web_tools.extract_links(args.url, args.timeout))
    elif action == "meta":
        _emit(web_tools.extract_meta(args.url, args.timeout))
    elif action == "search":
        _emit(web_tools.web_search(args.query, args.count))
    elif action == "json":
        _emit(web_tools.fetch_json(args.url, args.timeout))
    elif action == "download":
        _emit(web_tools.download_file(args.url, args.path, args.timeout))
    elif action == "url":
        _emit(web_tools.url_info(args.url))
    return 0


# --------------------------------------------------------------------- MCP #
def cmd_mcp(args) -> int:
    from eazzu.mcp import list_default_servers, get_server
    from eazzu.mcp.registry import MCPRegistry
    action = args.mcp_action
    if action == "list":
        servers = list_default_servers()
        rows = [[s["name"], s["transport"], s.get("auth_env") or "—", s["description"][:50]] for s in servers]
        print(table(["Server", "Transport", "Auth Env", "Description"], rows))
    elif action == "status":
        reg = MCPRegistry()
        statuses = reg.server_status()
        rows = [[s["name"], "✓" if s["reachable"] else "✗", s.get("error", "")[:40]] for s in statuses]
        print(table(["Server", "Reachable", "Error"], rows))
    elif action == "connect":
        from eazzu.mcp.client import MCPClient
        spec = get_server(args.server)
        client = MCPClient(endpoint=spec["endpoint"], transport=spec["transport"])
        info = client.initialize()
        tools = client.list_tools()
        client.close()
        _emit({"server": args.server, "info": info, "tools": tools, "count": len(tools)})
    elif action == "call":
        from eazzu.mcp.client import MCPClient
        spec = get_server(args.server)
        client = MCPClient(endpoint=spec["endpoint"], transport=spec["transport"])
        client.initialize()
        arguments = json.loads(args.arguments) if args.arguments else {}
        result = client.call_tool(args.tool, arguments)
        client.close()
        _emit(result)
    elif action == "tools":
        from eazzu.mcp.client import MCPClient
        spec = get_server(args.server)
        client = MCPClient(endpoint=spec["endpoint"], transport=spec["transport"])
        client.initialize()
        tools = client.list_tools()
        client.close()
        rows = [[t.get("name", ""), t.get("description", "")[:60]] for t in tools]
        print(table(["Tool", "Description"], rows))
    return 0


# --------------------------------------------------------------------- CODE #
def cmd_code(args) -> int:
    from eazzu.tools.code_tools import run_python, run_python_interactive, interpret_code, run_script, run_shell
    action = args.code_action
    if action == "python":
        with open(args.file) as f:
            code = f.read()
        _emit(run_python(code, timeout=args.timeout))
    elif action == "eval":
        _emit(run_python(args.code, timeout=args.timeout))
    elif action == "interactive":
        _emit(run_python_interactive(args.code, session_id=args.session))
    elif action == "interpret":
        _emit(interpret_code(args.expression))
    elif action == "script":
        _emit(run_script(args.file, interpreter=args.interpreter, args=args.args, timeout=args.timeout))
    elif action == "shell":
        _emit(run_shell(args.command, timeout=args.timeout))
    elif action == "sessions":
        from eazzu.tools.code_tools import _list_sessions
        _emit(_list_sessions())
    return 0


# ---------------------------------------------------------------- ARTIFACT #
def cmd_artifact(args) -> int:
    from eazzu.tools.artifact_tools import create_artifact, get_artifact, list_artifacts, export_artifact, export_all, create_html, create_markdown, create_json_artifact, create_python_script, create_config
    action = args.artifact_action
    if action == "create":
        with open(args.file) as f:
            content = f.read()
        _emit(create_artifact(args.name, args.type, content))
    elif action == "list":
        _emit(list_artifacts())
    elif action == "get":
        _emit(get_artifact(args.id))
    elif action == "export":
        _emit(export_artifact(args.id, args.output))
    elif action == "export-all":
        _emit(export_all(args.directory))
    elif action == "html":
        _emit(create_html(args.title, args.body))
    elif action == "markdown":
        _emit(create_markdown(args.title, args.body))
    elif action == "json":
        data = json.loads(args.data) if args.data else {}
        _emit(create_json_artifact(args.name, data))
    elif action == "python":
        with open(args.file) as f:
            code = f.read()
        _emit(create_python_script(args.name, code))
    return 0


# ------------------------------------------------------------------- MEMORY #
def cmd_memory(args) -> int:
    from eazzu.agent.memory import WorkingMemory
    mem = WorkingMemory()
    action = args.memory_action
    if action == "snapshot":
        _emit(mem.snapshot())
    elif action == "facts":
        _emit(mem.list_facts())
    elif action == "set":
        _emit(mem.set_fact(args.key, args.value))
    elif action == "get":
        _emit(mem.get_fact(args.key))
    elif action == "delete":
        _emit(mem.delete_fact(args.key))
    elif action == "history":
        _emit(mem.get_history(args.limit))
    elif action == "clear-history":
        _emit(mem.clear_history())
    elif action == "tasks":
        _emit(mem.list_tasks(args.status))
    elif action == "scratchpad":
        _emit(mem.get_scratchpad())
    elif action == "set-scratchpad":
        _emit(mem.set_scratchpad(args.text))
    elif action == "artifacts":
        _emit(mem.list_artifacts())
    elif action == "reset":
        _emit(mem.reset())
    return 0


# ----------------------------------------------------------------- TELEGRAM #
def cmd_telegram(args) -> int:
    from eazzu.bot.telegram import run_bot, get_me
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not token:
        from eazzu.providers import ConfigManager
        token = ConfigManager().get("telegram_bot") or ""
    if not token:
        print(status_line("No Telegram bot token found. Set TELEGRAM_BOT_TOKEN env var or run: eazzu keys set telegram_bot <token>", "error"))
        return 2
    if args.check:
        me = get_me(token)
        _emit(me)
        return 0
    provider, model, strategy = _resolve_agent_args(args)
    allowed = args.allowed_users.split(",") if args.allowed_users else None
    run_bot(token, provider=provider, model=model, allowed_users=allowed,
            router_strategy=strategy or "random")
    return 0


# ------------------------------------------------------------------ ANALYZE #
def cmd_analyze(args) -> int:
    from eazzu.trading.advanced_analysis import full_analysis, vwap, williams_r, mfi, cci, obv, aroon, cmo, trix, keltner_channels, donchian_channels, heikin_ashi, renko, pivot_points, multi_timeframe, correlation
    with open(args.candles) as f:
        data = json.load(f)
    candles = data.get("candles") or data.get("data") or data.get("history") or data
    if not isinstance(candles, list):
        print("invalid candle data format")
        return 2
    if args.indicator == "full":
        _emit(full_analysis(candles))
    elif args.indicator == "vwap":
        _emit({"vwap": vwap(candles)})
    elif args.indicator == "williams":
        _emit({"williams_r": williams_r(candles, args.period)})
    elif args.indicator == "mfi":
        _emit({"mfi": mfi(candles, args.period)})
    elif args.indicator == "cci":
        _emit({"cci": cci(candles, args.period)})
    elif args.indicator == "obv":
        _emit({"obv": obv(candles)})
    elif args.indicator == "aroon":
        _emit(aroon(candles, args.period))
    elif args.indicator == "cmo":
        _emit({"cmo": cmo(candles, args.period)})
    elif args.indicator == "trix":
        _emit({"trix": trix(candles, args.period)})
    elif args.indicator == "keltner":
        _emit(keltner_channels(candles))
    elif args.indicator == "donchian":
        _emit(donchian_channels(candles, args.period))
    elif args.indicator == "heikin":
        _emit({"heikin_ashi": heikin_ashi(candles)})
    elif args.indicator == "renko":
        _emit(renko(candles))
    elif args.indicator == "pivot":
        _emit(pivot_points(candles, args.method))
    elif args.indicator == "mtf":
        _emit(multi_timeframe(candles))
    else:
        _emit(full_analysis(candles))
    return 0


# ------------------------------------------------------------------- DOCTOR #
def cmd_doctor(args) -> int:
    from eazzu.doctor import run_doctor, print_report
    report = run_doctor(fix=getattr(args, "fix", False))
    if getattr(args, "json", False):
        _emit(report)
        return 0 if report["status"] == "ok" else 1
    print_report(report)
    return 0 if report["status"] in ("ok", "warn") else 2


# -------------------------------------------------------------------- TOOLS #
def cmd_tools(args) -> int:
    from eazzu import tools_discovery as td
    action = args.tools_action
    if action == "list":
        return td.cmd_list(query=args.query, group=args.group, as_json=args.json)
    if action == "count":
        return td.cmd_count()
    if action == "info":
        return td.cmd_info(args.name)
    if action == "groups":
        return td.cmd_groups()
    return 1


# ------------------------------------------------------------------- CONFIG #
def cmd_config(args) -> int:
    from eazzu.config import get_config, parse_value, DEFAULTS
    cfg = get_config()
    action = args.config_action
    if action == "show":
        _emit(cfg.all())
        return 0
    if action == "list":
        rows = [
            [k, repr(cfg.get(k)), repr(DEFAULTS[k])] for k in sorted(DEFAULTS)
        ]
        print(table(["Key", "Value", "Default"], rows))
        print(f"\nfile: {cfg.path}")
        return 0
    if action == "path":
        print(cfg.path)
        return 0
    if action == "get":
        print(cfg.get(args.key))
        return 0
    if action == "set":
        try:
            cfg.set(args.key, parse_value(args.value))
        except (KeyError, ValueError) as e:
            print(status_line(str(e), "error"))
            return 2
        cfg.save()
        print(status_line(f"{args.key} = {cfg.get(args.key)!r}", "ok"))
        return 0
    if action == "unset":
        if args.key not in DEFAULTS:
            print(status_line(f"unknown key {args.key!r}", "error"))
            return 2
        cfg.set(args.key, DEFAULTS[args.key])
        cfg.save()
        print(status_line(f"{args.key} reset to {DEFAULTS[args.key]!r}", "ok"))
        return 0
    if action == "reset":
        cfg.reset()
        cfg.save()
        print(status_line(f"config reset to defaults at {cfg.path}", "ok"))
        return 0
    return 1


# --------------------------------------------------------------------- APP #
def cmd_app(args) -> int:
    from eazzu.tools import app_builder_tools as ab
    action = args.app_action
    if action == "create":
        _emit(ab.create_app(args.description, language=args.language,
                            out_dir=args.out_dir, title=args.title))
    elif action == "run":
        _emit(ab.run_app(args.directory, command=args.command, timeout=args.timeout,
                         background=args.background, port=args.port))
    elif action == "fix":
        _emit(ab.fix_app(args.directory, args.error_log))
    elif action == "screenshot":
        _emit(ab.screenshot_app(url=args.url, output=args.output, wait_ms=args.wait_ms))
    elif action == "package":
        _emit(ab.package_app(args.directory, fmt=args.fmt))
    elif action == "build":
        _emit(ab.build_app(args.description, language=args.language))
    else:
        return 1
    return 0


# -------------------------------------------------------------------- SELF #
def cmd_self(args) -> int:
    from eazzu.tools import self_updater_tools as su
    action = args.self_action
    if action == "status":
        _emit(su.status_self())
    elif action == "clone":
        _emit(su.clone_self(dest=args.dest, branch=args.branch))
    elif action == "test":
        _emit(su.test_self(args.directory, args=args.args))
    elif action == "install":
        _emit(su.install_self(args.directory))
    elif action == "commit":
        _emit(su.commit_self(args.directory, args.message))
    elif action == "push":
        _emit(su.push_self(args.directory, branch=args.branch, to_main=args.to_main))
    elif action == "apply":
        _emit(su.apply_to_live(args.directory, restart_cmd=args.restart_cmd))
    else:
        return 1
    return 0


# ------------------------------------------------------------------ COMPUTER #
def cmd_computer(args) -> int:
    from eazzu.tools import computer_tools as ct
    action = args.computer_action
    if action == "screenshot":
        _emit(ct.screenshot(output=args.output or "screenshot.png"))
        return 0
    if action == "desktop":
        _emit(ct.list_desktop())
        return 0
    if action == "ls":
        _emit(ct.list_directory(args.path or "."))
        return 0
    if action == "info":
        _emit(ct.file_info(args.path))
        return 0
    if action == "open":
        _emit(ct.open_file(args.path))
        return 0
    if action == "shell":
        _emit(ct.run_shell_cmd(args.command, shell=args.shell or "auto",
                               timeout=args.timeout, cwd=args.cwd))
        return 0
    if action == "cmd":
        _emit(ct.run_cmd(args.command, timeout=args.timeout, cwd=args.cwd))
        return 0
    if action == "powershell":
        _emit(ct.run_powershell(args.command, timeout=args.timeout, cwd=args.cwd))
        return 0
    if action == "processes":
        _emit(ct.list_processes())
        return 0
    if action == "window":
        _emit(ct.active_window())
        return 0
    if action == "clipboard":
        if args.write:
            _emit(ct.clipboard_write(args.write))
        else:
            _emit(ct.clipboard_read())
        return 0
    if action == "alert":
        _emit(ct.dialog_alert(args.title or "EAZZU", args.message))
        return 0
    return 1


# -------------------------------------------------------------------- UPDATE #
def cmd_update(args) -> int:
    from eazzu.updater import update
    return update(full=args.full, yes=args.yes)


# ------------------------------------------------------------------- ROUTER #
def cmd_router(args) -> int:
    import json as _json
    from eazzu.providers.router import ProviderRouter, mask_key
    from eazzu.cli_ui import table, C
    from eazzu.config import get_config

    # Pick strategy: CLI flag > config > default
    cfg = get_config()
    strategy = getattr(args, "strategy", None) or cfg.get("router_strategy", "random")
    router = ProviderRouter(strategy=strategy)

    if args.router_action == "refresh":
        added = router.refresh()
        print(status_line(f"refreshed endpoints ({added:+d})", "ok"))
        return 0
    if args.router_action == "reset":
        router.reset_health()
        print(status_line("health state reset for all endpoints", "ok"))
        return 0
    if args.router_action == "status":
        st = router.status()
        if args.json:
            _emit(st)
            return 0
        print(f"Router strategy: {colorize(st['strategy'], C.BOLD)}   "
              f"healthy: {colorize(str(st['healthy']), C.GREEN)}/{st['total_endpoints']}")
        rows = []
        for e in st["endpoints"]:
            mark = colorize("✓", C.GREEN) if e["ready"] else colorize(f"⏳{e['cooldown_remaining_s']}s", C.YELLOW)
            rows.append([
                mark,
                e["label"],
                e["key"],
                e["model"] or "",
                f"{e['successes']}/{e['successes']+e['failures']}",
                f"{e['avg_latency_ms']:.0f}ms",
                (e["last_error"][:50] + "…") if e["last_error"] else "",
            ])
        print(table(["", "Endpoint", "Key", "Model", "ok/tot", "lat", "last err"], rows))
        return 0
    if args.router_action == "test":
        # Send a tiny 'ping' to every configured endpoint and report.
        prompt = "Reply with exactly the word PONG and nothing else."
        results = []
        for ep in router.endpoints:
            entry = {"endpoint": ep.name, "provider": ep.provider, "ok": False, "latency_ms": 0, "reply": "", "error": ""}
            t0 = time.time()
            try:
                inst = router.connector.get_provider(ep.provider, api_key=ep.api_key)
                resp = inst.chat([{"role": "user", "content": prompt}], model=ep.model, timeout=30)
                entry["ok"] = "PONG" in resp.content.upper()
                entry["reply"] = resp.content[:60]
            except Exception as e:
                entry["error"] = f"{type(e).__name__}: {str(e)[:120]}"
            entry["latency_ms"] = round((time.time() - t0) * 1000)
            results.append(entry)
        if args.json:
            _emit(results)
            return 0
        rows = []
        for r in results:
            mark = colorize("✓", C.GREEN) if r["ok"] else colorize("✗", C.RED)
            detail = r["reply"] if r["ok"] else r["error"]
            rows.append([mark, r["endpoint"], f"{r['latency_ms']}ms", (detail[:70] + "…") if len(detail) > 70 else detail])
        print(table(["", "Endpoint", "lat", "result"], rows))
        ok = sum(1 for r in results if r["ok"])
        print(f"\n{ok}/{len(results)} endpoints alive")
        return 0 if ok > 0 else 1
    return 1


# ----------------------------------------------------------------- COMMANDS #
def _iter_command_help(parser: argparse.ArgumentParser, prefix: str = "eazzu") -> list[tuple[str, str]]:
    """Walk subparsers to produce (command_path, help) pairs."""
    from argparse import _SubParsersAction
    out: list[tuple[str, str]] = []
    for action in parser._actions:
        if isinstance(action, _SubParsersAction):
            for name, sub in action.choices.items():
                path = f"{prefix} {name}".strip()
                # argparse stores per-choice help in _choices_actions, not on the subparser itself
                first = ""
                for choice_action in action._choices_actions:
                    if choice_action.dest == name or choice_action.metavar == name:
                        first = choice_action.help or ""
                        break
                if not first:
                    first = (sub.description or "").splitlines()[0] if sub.description else ""
                out.append((path, first))
                out.extend(_iter_command_help(sub, path))
    return out


def cmd_commands(args) -> int:
    parser = build_parser()
    cmds = _iter_command_help(parser)
    if getattr(args, "json", False):
        _emit([{"command": c, "description": d} for c, d in cmds])
        return 0
    rows = [[c, d] for c, d in cmds]
    print(table(["Command", "Description"], rows))
    print(f"\n{len(cmds)} commands total.")
    return 0


# --------------------------------------------------------------------- PARSE #
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        "eazzu",
        description="Unified agentic developer + trading + AI + MCP toolkit",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Run `eazzu <command> --help` for details on each command.",
    )
    p.add_argument("--version", "-V", action="store_true", help="print version and exit")
    p.add_argument("--no-color", action="store_true", help="disable ANSI colors (overrides env/config)")
    # Hidden flags used by the shell-completion machinery.
    p.add_argument("--_complete", action="store_true", help=argparse.SUPPRESS)
    p.add_argument("--_completion-script", choices=("bash", "zsh", "fish"), help=argparse.SUPPRESS)
    p.add_argument("--install-completion", nargs="?", const="auto",
                   choices=("bash", "zsh", "fish", "auto"),
                   help="install shell completion (default: detect shell)")
    sub = p.add_subparsers(dest="cmd")

    def _default_provider() -> str:
        # env > config > "auto"
        if os.environ.get("EAZZU_PROVIDER"):
            return os.environ["EAZZU_PROVIDER"]
        try:
            from eazzu.config import get_config
            return get_config().get("default_provider") or "auto"
        except Exception:
            return "auto"

    def _default_model() -> Optional[str]:
        if os.environ.get("EAZZU_MODEL"):
            return os.environ["EAZZU_MODEL"]
        try:
            from eazzu.config import get_config
            return get_config().get("default_model")
        except Exception:
            return None

    for name, fn, help_txt in (("chat", cmd_chat, "interactive agentic chat"), ("ask", cmd_ask, "one-shot agent query")):
        sp = sub.add_parser(name, help=help_txt)
        sp.add_argument("--provider", default=None,
                        help="AI provider (default: auto = rotate across all configured keys)")
        sp.add_argument("--model", default=None)
        sp.add_argument("--router-strategy", choices=("random", "healthiest", "fastest", "cheapest"),
                        default=None, help="routing strategy when provider=auto")
        if name == "ask":
            sp.add_argument("prompt"); sp.add_argument("--json", action="store_true")
        sp.set_defaults(func=fn)

    lp = sub.add_parser("loop", help="autonomous agentic loop — works until task complete")
    lp.add_argument("task")
    lp.add_argument("--provider", default=None,
                    help="AI provider (default: auto = rotate across all configured keys)")
    lp.add_argument("--model", default=None)
    lp.add_argument("--router-strategy", choices=("random", "healthiest", "fastest", "cheapest"), default=None)
    lp.add_argument("--max-iterations", type=int, default=20)
    lp.set_defaults(func=cmd_loop)

    kp = sub.add_parser("keys", help="manage provider API keys (encrypted, multi-key supported)")
    ksub = kp.add_subparsers(dest="action", required=True)
    ks_set = ksub.add_parser("set", help="replace all keys for a provider")
    ks_set.add_argument("provider"); ks_set.add_argument("value")
    ks_add = ksub.add_parser("add", help="append a key to a provider (rotator picks randomly)")
    ks_add.add_argument("provider"); ks_add.add_argument("value")
    ks_get = ksub.add_parser("get", help="print the active (first) key for a provider")
    ks_get.add_argument("provider")
    ks_show = ksub.add_parser("show", help="list masked keys for a provider (safe for logs)")
    ks_show.add_argument("provider")
    ks_rm = ksub.add_parser("remove", help="remove a key by value or 1-based index")
    ks_rm.add_argument("provider"); ks_rm.add_argument("value", nargs="?", help="key substring or 1-based index")
    ks_del = ksub.add_parser("delete", help="delete ALL keys for a provider")
    ks_del.add_argument("provider")
    ksub.add_parser("list", help="list providers with stored keys (with counts)")
    kp.set_defaults(func=cmd_keys)

    pp = sub.add_parser("providers", help="list registered providers")
    pp.add_argument("--category", help="filter: llm | image | audio | search | embedding")
    pp.set_defaults(func=cmd_providers)

    tp = sub.add_parser("trade", help="trading analysis, signal tracking, and legacy toolkit")
    tsub = tp.add_subparsers(dest="trade_action", required=True)
    tsub.add_parser("list"); tsub.add_parser("knowledge")
    bt = tsub.add_parser("backtest"); bt.add_argument("--strategy", default="deriv_scalper"); bt.add_argument("--symbol", default="R_75"); bt.add_argument("--days", type=int, default=30)
    for name, help_text in (("analyze", "run multi-method analysis on local OHLCV JSON"), ("signal", "generate confluence signal from local OHLCV JSON")):
        command = tsub.add_parser(name, help=help_text)
        command.add_argument("--candles", required=True); command.add_argument("--symbol"); command.add_argument("--timeframe")
        if name == "signal":
            command.add_argument("--min-confidence", type=float, default=0.56); command.add_argument("--risk-multiple", type=float, default=1.5)
            command.add_argument("--reward-multiple", type=float, default=2.0); command.add_argument("--expiry-bars", type=int, default=12)
            command.add_argument("--ledger"); command.add_argument("--no-record", action="store_true")
    track = tsub.add_parser("track"); track_sub = track.add_subparsers(dest="track_action", required=True)
    ts = track_sub.add_parser("summary"); ts.add_argument("--ledger"); ts.add_argument("--limit", type=int, default=20)
    tr = track_sub.add_parser("resolve"); tr.add_argument("signal_id"); tr.add_argument("--candles", required=True); tr.add_argument("--ledger")
    lv = tsub.add_parser("live"); lv.add_argument("--i-understand-risk", action="store_true")
    tp.set_defaults(func=cmd_trade)

    dp = sub.add_parser("dev", help="developer toolkit")
    dsub = dp.add_subparsers(dest="dev_action", required=True)
    az = dsub.add_parser("analyze"); az.add_argument("path")
    rn = dsub.add_parser("run"); rn.add_argument("path"); rn.add_argument("args", nargs="*")
    dp.set_defaults(func=cmd_dev)

    rp = sub.add_parser("research", help="deep web research pipeline")
    rp.add_argument("query"); rp.add_argument("--max-sources", type=int, default=5)
    rp.set_defaults(func=cmd_research)

    np_ = sub.add_parser("net", help="network utilities")
    nsub = np_.add_subparsers(dest="net_action", required=True)
    ip_ = nsub.add_parser("ip"); ip_.add_argument("address")
    dn = nsub.add_parser("dns"); dn.add_argument("hostname")
    ht = nsub.add_parser("http"); ht.add_argument("url")
    np_.set_defaults(func=cmd_net)

    wp = sub.add_parser("web", help="serve the bundled chat web UI")
    wp.add_argument("--port", type=int, default=8787)
    wp.set_defaults(func=cmd_web)

    dp2 = sub.add_parser("deriv", help="real-time forex data via Deriv public API")
    dsub = dp2.add_subparsers(dest="deriv_action", required=True)
    dsub.add_parser("ping"); dsub.add_parser("symbols"); dsub.add_parser("status"); dsub.add_parser("time")
    tk = dsub.add_parser("tick"); tk.add_argument("symbol")
    hi = dsub.add_parser("history"); hi.add_argument("symbol"); hi.add_argument("--count", type=int, default=100); hi.add_argument("--style", default="ticks")
    cd = dsub.add_parser("candles"); cd.add_argument("symbol"); cd.add_argument("--count", type=int, default=100); cd.add_argument("--granularity", type=int, default=60)
    rt = dsub.add_parser("rates"); rt.add_argument("--base", default="USD")
    pp_ = dsub.add_parser("proposal"); pp_.add_argument("--contract-type", default="CALL"); pp_.add_argument("--symbol", default="R_100")
    pp_.add_argument("--amount", type=float, default=10); pp_.add_argument("--basis", default="stake"); pp_.add_argument("--currency", default="USD")
    pp_.add_argument("--duration", type=int, default=5); pp_.add_argument("--duration-unit", default="m")
    ct = dsub.add_parser("collect-ticks"); ct.add_argument("symbol"); ct.add_argument("--count", type=int, default=10); ct.add_argument("--timeout", type=float, default=30.0)
    cc = dsub.add_parser("collect-candles"); cc.add_argument("symbol"); cc.add_argument("--count", type=int, default=10); cc.add_argument("--granularity", type=int, default=60); cc.add_argument("--timeout", type=float, default=60.0)
    sn = dsub.add_parser("snapshot"); sn.add_argument("--symbols")
    dp2.set_defaults(func=cmd_deriv)

    mp = sub.add_parser("music", help="AI music composition and analysis")
    msub = mp.add_subparsers(dest="music_action", required=True)
    mel = msub.add_parser("melody"); mel.add_argument("--key", default="C"); mel.add_argument("--scale", default="major"); mel.add_argument("--bars", type=int, default=4); mel.add_argument("--mood", default="happy"); mel.add_argument("--complexity", type=float, default=0.5)
    ch = msub.add_parser("chords"); ch.add_argument("--key", default="C"); ch.add_argument("--style", default="pop"); ch.add_argument("--bars", type=int, default=4)
    dr = msub.add_parser("drums"); dr.add_argument("--genre", default="house"); dr.add_argument("--steps", type=int, default=16)
    bs = msub.add_parser("bass"); bs.add_argument("--key", default="C"); bs.add_argument("--scale", default="major"); bs.add_argument("--genre", default="house"); bs.add_argument("--bars", type=int, default=4)
    st = msub.add_parser("structure"); st.add_argument("--genre", default="pop")
    msub.add_parser("scales")
    eu = msub.add_parser("euclidean"); eu.add_argument("--steps", type=int, default=16); eu.add_argument("--pulses", type=int, default=4); eu.add_argument("--rotation", type=int, default=0)
    an = msub.add_parser("analyze"); an.add_argument("path")
    mp.set_defaults(func=cmd_music)

    ip = sub.add_parser("image", help="image generation and processing")
    isub = ip.add_subparsers(dest="image_action", required=True)
    gr = isub.add_parser("gradient"); gr.add_argument("--width", type=int, default=256); gr.add_argument("--height", type=int, default=256); gr.add_argument("--direction", default="horizontal"); gr.add_argument("--color1", default="0,0,0"); gr.add_argument("--color2", default="255,255,255")
    pl = isub.add_parser("plasma"); pl.add_argument("--width", type=int, default=256); pl.add_argument("--height", type=int, default=256); pl.add_argument("--scale", type=float, default=0.05)
    mb = isub.add_parser("mandelbrot"); mb.add_argument("--width", type=int, default=256); mb.add_argument("--height", type=int, default=256); mb.add_argument("--max-iter", type=int, default=80); mb.add_argument("--zoom", type=float, default=1.0); mb.add_argument("--cx", type=float, default=-0.5); mb.add_argument("--cy", type=float, default=0.0)
    nz = isub.add_parser("noise"); nz.add_argument("--width", type=int, default=256); nz.add_argument("--height", type=int, default=256); nz.add_argument("--scale", type=float, default=1.0); nz.add_argument("--seed", type=int, default=42)
    cb = isub.add_parser("checkerboard"); cb.add_argument("--width", type=int, default=256); cb.add_argument("--height", type=int, default=256); cb.add_argument("--cells", type=int, default=8); cb.add_argument("--color1", default="0,0,0"); cb.add_argument("--color2", default="255,255,255")
    isub.add_parser("pil")
    ip.set_defaults(func=cmd_image)

    wtp = sub.add_parser("webtools", help="web access: fetch, search, scrape, extract")
    wtsub = wtp.add_subparsers(dest="webtools_action", required=True)
    g = wtsub.add_parser("get"); g.add_argument("url"); g.add_argument("--timeout", type=int, default=20)
    p_ = wtsub.add_parser("post"); p_.add_argument("url"); p_.add_argument("--data"); p_.add_argument("--json-body"); p_.add_argument("--timeout", type=int, default=20)
    ex = wtsub.add_parser("extract"); ex.add_argument("url"); ex.add_argument("--timeout", type=int, default=20)
    lk = wtsub.add_parser("links"); lk.add_argument("url"); lk.add_argument("--timeout", type=int, default=20)
    mt = wtsub.add_parser("meta"); mt.add_argument("url"); mt.add_argument("--timeout", type=int, default=20)
    se = wtsub.add_parser("search"); se.add_argument("query"); se.add_argument("--count", type=int, default=10)
    js = wtsub.add_parser("json"); js.add_argument("url"); js.add_argument("--timeout", type=int, default=20)
    dl = wtsub.add_parser("download"); dl.add_argument("url"); dl.add_argument("path"); dl.add_argument("--timeout", type=int, default=60)
    ui = wtsub.add_parser("url"); ui.add_argument("url")
    wtp.set_defaults(func=cmd_webtools)

    mcp_p = sub.add_parser("mcp", help="MCP server management (HuggingFace, TradingView, MT5, etc.)")
    mcp_sub = mcp_p.add_subparsers(dest="mcp_action", required=True)
    mcp_sub.add_parser("list", help="list configured MCP servers")
    mcp_sub.add_parser("status", help="ping all MCP servers")
    mc = mcp_sub.add_parser("connect", help="connect to a server and list its tools"); mc.add_argument("server")
    mcall = mcp_sub.add_parser("call", help="call a tool on an MCP server"); mcall.add_argument("server"); mcall.add_argument("tool"); mcall.add_argument("--arguments", default="{}")
    mt2 = mcp_sub.add_parser("tools", help="list tools on a server"); mt2.add_argument("server")
    mcp_p.set_defaults(func=cmd_mcp)

    code_p = sub.add_parser("code", help="code runner and interpreter")
    code_sub = code_p.add_subparsers(dest="code_action", required=True)
    cp = code_sub.add_parser("python", help="run a Python file"); cp.add_argument("file"); cp.add_argument("--timeout", type=int, default=30)
    ce = code_sub.add_parser("eval", help="evaluate Python code string"); ce.add_argument("code"); ce.add_argument("--timeout", type=int, default=30)
    ci = code_sub.add_parser("interactive", help="run Python in a persistent session"); ci.add_argument("code"); ci.add_argument("--session", default="default")
    cint = code_sub.add_parser("interpret", help="evaluate a Python expression"); cint.add_argument("expression")
    cs = code_sub.add_parser("script", help="run a script with any interpreter"); cs.add_argument("file"); cs.add_argument("--interpreter", default="python"); cs.add_argument("args", nargs="*"); cs.add_argument("--timeout", type=int, default=30)
    csh = code_sub.add_parser("shell", help="run a shell command"); csh.add_argument("command"); csh.add_argument("--timeout", type=int, default=30)
    code_sub.add_parser("sessions", help="list interactive Python sessions")
    code_p.set_defaults(func=cmd_code)

    art_p = sub.add_parser("artifact", help="create and manage project artifacts")
    art_sub = art_p.add_subparsers(dest="artifact_action", required=True)
    ac = art_sub.add_parser("create", help="create artifact from file"); ac.add_argument("name"); ac.add_argument("type"); ac.add_argument("file")
    art_sub.add_parser("list", help="list all artifacts")
    ag = art_sub.add_parser("get", help="get artifact by ID"); ag.add_argument("id")
    ae = art_sub.add_parser("export", help="export artifact to file"); ae.add_argument("id"); ae.add_argument("output")
    aea = art_sub.add_parser("export-all", help="export all artifacts"); aea.add_argument("directory")
    ah = art_sub.add_parser("html", help="create HTML page"); ah.add_argument("title"); ah.add_argument("body")
    am = art_sub.add_parser("markdown", help="create Markdown doc"); am.add_argument("title"); am.add_argument("body")
    aj = art_sub.add_parser("json", help="create JSON artifact"); aj.add_argument("name"); aj.add_argument("data")
    ap = art_sub.add_parser("python", help="create Python script artifact"); ap.add_argument("name"); ap.add_argument("file")
    art_p.set_defaults(func=cmd_artifact)

    mem_p = sub.add_parser("memory", help="persistent working memory management")
    mem_sub = mem_p.add_subparsers(dest="memory_action", required=True)
    mem_sub.add_parser("snapshot")
    mem_sub.add_parser("facts")
    ms = mem_sub.add_parser("set"); ms.add_argument("key"); ms.add_argument("value")
    mg = mem_sub.add_parser("get"); mg.add_argument("key")
    md = mem_sub.add_parser("delete"); md.add_argument("key")
    mh = mem_sub.add_parser("history"); mh.add_argument("--limit", type=int, default=50)
    mem_sub.add_parser("clear-history")
    mt3 = mem_sub.add_parser("tasks"); mt3.add_argument("--status")
    mem_sub.add_parser("scratchpad")
    mss = mem_sub.add_parser("set-scratchpad"); mss.add_argument("text")
    mem_sub.add_parser("artifacts")
    mem_sub.add_parser("reset")
    mem_p.set_defaults(func=cmd_memory)

    tg_p = sub.add_parser("telegram", help="run the EAZZU Telegram bot")
    tg_p.add_argument("--provider", default=None, help="AI provider (default: auto)")
    tg_p.add_argument("--model", default=None)
    tg_p.add_argument("--router-strategy", choices=("random", "healthiest", "fastest", "cheapest"), default=None)
    tg_p.add_argument("--allowed-users", help="comma-separated Telegram user IDs")
    tg_p.add_argument("--check", action="store_true", help="verify bot token and exit")
    tg_p.set_defaults(func=cmd_telegram)

    an_p = sub.add_parser("analyze", help="advanced technical analysis (22+ indicators)")
    an_p.add_argument("candles", help="path to OHLCV JSON file")
    an_p.add_argument("--indicator", default="full", help="indicator: full, vwap, williams, mfi, cci, obv, aroon, cmo, trix, keltner, donchian, heikin, renko, pivot, mtf")
    an_p.add_argument("--period", type=int, default=14)
    an_p.add_argument("--method", default="classic", help="pivot method: classic, camarilla, woodie")
    an_p.set_defaults(func=cmd_analyze)

    # --------------------------------------------------------- NEW: doctor #
    dr_p = sub.add_parser("doctor", help="environment diagnostics (Python, deps, keys, network)")
    dr_p.add_argument("--fix", action="store_true", help="attempt to auto-fix fixable issues (e.g. create config dir)")
    dr_p.add_argument("--json", action="store_true", help="emit JSON report instead of ANSI table")
    dr_p.set_defaults(func=cmd_doctor)

    # --------------------------------------------------------- NEW: tools #
    tl_p = sub.add_parser("tools", help="discover / search tools in the registry")
    tl_sub = tl_p.add_subparsers(dest="tools_action", required=True)
    tl_l = tl_sub.add_parser("list", help="list tools (filter with --query/--group)")
    tl_l.add_argument("--query", "-q", help="substring to match against name/description")
    tl_l.add_argument("--group", "-g", help="glob against group name (e.g. 'trade*')")
    tl_l.add_argument("--json", action="store_true")
    tl_sub.add_parser("count", help="print tool count by group")
    tl_sub.add_parser("groups", help="list tool groups and counts")
    tl_i = tl_sub.add_parser("info", help="show details for one tool"); tl_i.add_argument("name")
    tl_p.set_defaults(func=cmd_tools)

    # --------------------------------------------------------- NEW: config #
    cf_p = sub.add_parser("config", help="view/edit persistent CLI settings (~/.eazzu/config.json)")
    cf_sub = cf_p.add_subparsers(dest="config_action", required=True)
    cf_sub.add_parser("show", help="print current settings as JSON")
    cf_ls = cf_sub.add_parser("list", help="print settings as a key-value table")
    cf_get = cf_sub.add_parser("get", help="print a single setting"); cf_get.add_argument("key")
    cf_set = cf_sub.add_parser("set", help="set a setting"); cf_set.add_argument("key"); cf_set.add_argument("value")
    cf_del = cf_sub.add_parser("unset", help="reset a key to its default"); cf_del.add_argument("key")
    cf_sub.add_parser("reset", help="reset all settings to defaults")
    cf_path = cf_sub.add_parser("path", help="print path to config file")
    cf_p.set_defaults(func=cmd_config)

    # --------------------------------------------------------- NEW: update #
    up_p = sub.add_parser("update", help="pull latest from git and pip reinstall (if installed from a clone)")
    up_p.add_argument("--full", action="store_true", help="reinstall with [full] extras")
    up_p.add_argument("--yes", "-y", action="store_true", help="skip confirmation prompt")
    up_p.set_defaults(func=cmd_update)

    # --------------------------------------------------------- NEW: computer #
    cu_p = sub.add_parser("computer", help="computer-control: screenshot, desktop, files, shell/cmd/powershell, clipboard")
    cu_sub = cu_p.add_subparsers(dest="computer_action", required=True)
    cu_ss = cu_sub.add_parser("screenshot", help="capture the primary screen to PNG")
    cu_ss.add_argument("--output", "-o", default="screenshot.png")
    cu_sub.add_parser("desktop", help="list files on the desktop")
    cu_ls = cu_sub.add_parser("ls", help="list a directory")
    cu_ls.add_argument("path", nargs="?", default=".")
    cu_inf = cu_sub.add_parser("info", help="file/directory metadata")
    cu_inf.add_argument("path")
    cu_op = cu_sub.add_parser("open", help="open a file with OS default handler")
    cu_op.add_argument("path")
    cu_sh = cu_sub.add_parser("shell", help="run a shell command")
    cu_sh.add_argument("command"); cu_sh.add_argument("--shell", default="auto"); cu_sh.add_argument("--timeout", type=int, default=30); cu_sh.add_argument("--cwd")
    cu_cmd = cu_sub.add_parser("cmd", help="run a Windows cmd.exe command")
    cu_cmd.add_argument("command"); cu_cmd.add_argument("--timeout", type=int, default=30); cu_cmd.add_argument("--cwd")
    cu_ps = cu_sub.add_parser("powershell", help="run PowerShell (pwsh on non-Windows)")
    cu_ps.add_argument("command"); cu_ps.add_argument("--timeout", type=int, default=30); cu_ps.add_argument("--cwd")
    cu_sub.add_parser("processes", help="list running processes")
    cu_sub.add_parser("window", help="title of the active/foreground window")
    cu_cb = cu_sub.add_parser("clipboard", help="read (default) or --write text to clipboard")
    cu_cb.add_argument("--write", help="write text to clipboard")
    cu_al = cu_sub.add_parser("alert", help="show a desktop popup dialog")
    cu_al.add_argument("message"); cu_al.add_argument("--title", default="EAZZU")
    cu_p.set_defaults(func=cmd_computer)

    # --------------------------------------------------------- NEW: app builder #
    ap_p = sub.add_parser("app", help="create, run, screenshot, and package production-ready apps")
    ap_sub = ap_p.add_subparsers(dest="app_action", required=True)
    ap_c = ap_sub.add_parser("create", help="scaffold a new app")
    ap_c.add_argument("description"); ap_c.add_argument("--language", default="html", choices=["html", "python", "node"])
    ap_c.add_argument("--out-dir"); ap_c.add_argument("--title")
    ap_r = ap_sub.add_parser("run", help="run the scaffolded app")
    ap_r.add_argument("directory"); ap_r.add_argument("--command"); ap_r.add_argument("--timeout", type=int, default=30)
    ap_r.add_argument("--background", action="store_true"); ap_r.add_argument("--port", type=int, default=0)
    ap_f = ap_sub.add_parser("fix", help="append error log to FIX_LOG.txt for fix iteration")
    ap_f.add_argument("directory"); ap_f.add_argument("error_log")
    ap_s = ap_sub.add_parser("screenshot", help="capture a running app")
    ap_s.add_argument("--url", default="http://localhost:8765"); ap_s.add_argument("--output"); ap_s.add_argument("--wait-ms", type=int, default=1500)
    ap_pk = ap_sub.add_parser("package", help="bundle the app (zip/tar.gz)")
    ap_pk.add_argument("directory"); ap_pk.add_argument("--fmt", default="zip")
    ap_b = ap_sub.add_parser("build", help="create + run + screenshot + package in one step")
    ap_b.add_argument("description"); ap_b.add_argument("--language", default="html")
    ap_p.set_defaults(func=cmd_app)

    # --------------------------------------------------------- NEW: self updater #
    sf_p = sub.add_parser("self", help="self-improvement: clone, test, commit, push, apply changes to running EAZZU")
    sf_sub = sf_p.add_subparsers(dest="self_action", required=True)
    sf_sub.add_parser("status", help="show running install info")
    sf_c = sf_sub.add_parser("clone", help="clone the repo to a sandbox dir")
    sf_c.add_argument("--dest"); sf_c.add_argument("--branch", default="self-improve")
    sf_t = sf_sub.add_parser("test", help="run pytest + compileall + ruff inside a clone")
    sf_t.add_argument("directory"); sf_t.add_argument("--args", default="-q")
    sf_i = sf_sub.add_parser("install", help="pip install -e a clone")
    sf_i.add_argument("directory")
    sf_cm = sf_sub.add_parser("commit", help="commit all changes in a clone")
    sf_cm.add_argument("directory"); sf_cm.add_argument("message")
    sf_pu = sf_sub.add_parser("push", help="push a clone to origin/main")
    sf_pu.add_argument("directory"); sf_pu.add_argument("--branch"); sf_pu.add_argument("--to-main", action="store_true", default=True)
    sf_a = sf_sub.add_parser("apply", help="copy changes back into the live install")
    sf_a.add_argument("directory"); sf_a.add_argument("--restart-cmd")
    sf_p.set_defaults(func=cmd_self)

    # --------------------------------------------------------- NEW: router #
    rt_p = sub.add_parser("router", help="multi-provider rotation status / health / tests")
    rt_sub = rt_p.add_subparsers(dest="router_action", required=True)
    rt_sub.add_parser("status", help="show endpoint health / cooldowns / stats")
    rt_sub.add_parser("refresh", help="re-scan keys/env to discover new endpoints")
    rt_sub.add_parser("reset", help="clear health state / cooldowns for all endpoints")
    rt_test = rt_sub.add_parser("test", help="send a tiny PONG ping to every configured endpoint")
    rt_test.add_argument("--json", action="store_true")
    rt_st = rt_sub.choices["status"]
    rt_st.add_argument("--json", action="store_true")
    rt_st.add_argument("--strategy", choices=("random", "healthiest", "fastest", "cheapest"),
                       help="override routing strategy for this invocation")
    rt_p.set_defaults(func=cmd_router)

    # --------------------------------------------------------- NEW: commands #
    cmd_p = sub.add_parser("commands", help="list every eazzu subcommand with a one-line description")
    cmd_p.add_argument("--json", action="store_true")
    cmd_p.set_defaults(func=cmd_commands)

    # --------------------------------------------------------- NEW: version (alias) #
    ver_p = sub.add_parser("version", help="print installed version")
    ver_p.set_defaults(func=cmd_version)

    return p


def main(argv: Optional[list[str]] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)

    # Early-handle --version/-V anywhere in the argv (works before/after subcommands).
    if any(a in ("--version", "-V") for a in argv):
        return cmd_version(argparse.Namespace())

    parser = build_parser()
    args = parser.parse_args(argv)

    # ---- Internal / global flags that bypass normal dispatch -------------
    if args._complete:
        from eazzu.completion import do_complete
        return do_complete()
    if args._completion_script:
        from eazzu.completion import print_script
        return print_script(args._completion_script)
    if args.install_completion:
        from eazzu.completion import install
        shell = None if args.install_completion == "auto" else args.install_completion
        return install(shell)

    _apply_globals(args)

    if not getattr(args, "cmd", None):
        print(banner())
        parser.print_help()
        return 0
    try:
        return args.func(args)
    except KeyboardInterrupt:
        print()
        return 130
    except Exception as exc:  # pragma: no cover - defensive top-level
        import traceback
        if os.environ.get("EAZZU_DEBUG"):
            traceback.print_exc()
        else:
            print(status_line(f"{type(exc).__name__}: {exc} (set EAZZU_DEBUG=1 for traceback)", "error"))
        return 1


if __name__ == "__main__":
    sys.exit(main())
