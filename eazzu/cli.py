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
from typing import Optional

from eazzu.cli_ui import banner, panel, table, kv, status_line, rule, C, colorize


def _emit(obj) -> None:
    if isinstance(obj, (dict, list)):
        print(json.dumps(obj, indent=2, default=str))
    else:
        print(obj)


# ---------------------------------------------------------------- CHAT / ASK #
def cmd_chat(args) -> int:
    from eazzu.agent import Agent
    agent = Agent(provider=args.provider, model=args.model)
    print(banner())
    print(f"Provider: {args.provider}  ·  Model: {args.model or '(default)'}")
    print(f"Tools: {len(agent.tools)} registered")
    print("Type '/exit' to quit · '/reset' to clear · '/tools' to list tools · '/memory' for memory\n")
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
        print("bot › ", end="", flush=True)
        turn = agent.ask(user, on_token=lambda c: (sys.stdout.write(c), sys.stdout.flush()))
        if not turn.reply and not turn.tool_calls:
            print("(no response)")
        else:
            print()
        for tc in turn.tool_calls:
            print(f"  {colorize('⤷', C.DIM)} tool `{colorize(tc['name'], C.CYAN)}` args={tc['args']}")


def cmd_ask(args) -> int:
    from eazzu.agent import Agent
    agent = Agent(provider=args.provider, model=args.model)
    turn = agent.ask(args.prompt)
    _emit(turn.reply if not args.json else {"reply": turn.reply, "tool_calls": turn.tool_calls, "latency_ms": turn.latency_ms, "cost_usd": turn.cost_usd})
    return 0


# --------------------------------------------------------------------- LOOP #
def cmd_loop(args) -> int:
    from eazzu.agent.loop import run_loop
    print(banner())
    print(f"Starting autonomous loop (max {args.max_iterations} iterations)\n")
    def on_step(step):
        it = step['iteration']
        print(f"\n{rule(f'Iteration {it}')}")
        print(f"  {colorize('Reply:', C.CYAN)} {step['reply'][:200]}...")
        if step['tool_calls']:
            for tc in step['tool_calls']:
                print(f"  {colorize('Tool:', C.YELLOW)} {tc['name']}")
        print(f"  {colorize('Elapsed:', C.DIM)} {step['elapsed_s']}s")
    result = run_loop(args.task, provider=args.provider, model=args.model, max_iterations=args.max_iterations, on_step=on_step)
    print(f"\n{rule('Result')}")
    _emit(result)
    return 0 if result["status"] == "complete" else 1


# ---------------------------------------------------------------------- KEYS #
def cmd_keys(args) -> int:
    from eazzu.providers import ConfigManager
    cm = ConfigManager()
    action = args.action
    if action == "set":
        cm.set(args.provider, args.value)
        print(status_line(f"key stored for '{args.provider}' (encrypted at ~/.eazzu/)", "ok"))
    elif action == "get":
        print(cm.get(args.provider) or "(not set)")
    elif action == "delete":
        cm.delete(args.provider)
        print(status_line(f"deleted '{args.provider}'", "ok"))
    elif action == "list":
        keys = cm.list_stored()
        print("\n".join(keys) if keys else "(no keys stored)")
    return 0


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
    allowed = args.allowed_users.split(",") if args.allowed_users else None
    run_bot(token, provider=args.provider, model=args.model, allowed_users=allowed)
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


# --------------------------------------------------------------------- PARSE #
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser("eazzu", description="Unified agentic developer + trading + AI + MCP toolkit")
    p.add_argument("--version", action="store_true", help="print version and exit")
    sub = p.add_subparsers(dest="cmd")

    for name, fn, help_txt in (("chat", cmd_chat, "interactive agentic chat"), ("ask", cmd_ask, "one-shot agent query")):
        sp = sub.add_parser(name, help=help_txt)
        sp.add_argument("--provider", default=os.environ.get("EAZZU_PROVIDER", "openai"))
        sp.add_argument("--model", default=os.environ.get("EAZZU_MODEL"))
        if name == "ask":
            sp.add_argument("prompt"); sp.add_argument("--json", action="store_true")
        sp.set_defaults(func=fn)

    lp = sub.add_parser("loop", help="autonomous agentic loop — works until task complete")
    lp.add_argument("task"); lp.add_argument("--provider", default="openai"); lp.add_argument("--model")
    lp.add_argument("--max-iterations", type=int, default=20)
    lp.set_defaults(func=cmd_loop)

    kp = sub.add_parser("keys", help="manage provider API keys (encrypted)")
    ksub = kp.add_subparsers(dest="action", required=True)
    for act, extra in (("set", ["provider", "value"]), ("get", ["provider"]), ("delete", ["provider"]), ("list", [])):
        s = ksub.add_parser(act)
        for a in extra: s.add_argument(a)
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
    tg_p.add_argument("--provider", default="openai"); tg_p.add_argument("--model")
    tg_p.add_argument("--allowed-users", help="comma-separated Telegram user IDs")
    tg_p.add_argument("--check", action="store_true", help="verify bot token and exit")
    tg_p.set_defaults(func=cmd_telegram)

    an_p = sub.add_parser("analyze", help="advanced technical analysis (22+ indicators)")
    an_p.add_argument("candles", help="path to OHLCV JSON file")
    an_p.add_argument("--indicator", default="full", help="indicator: full, vwap, williams, mfi, cci, obv, aroon, cmo, trix, keltner, donchian, heikin, renko, pivot, mtf")
    an_p.add_argument("--period", type=int, default=14)
    an_p.add_argument("--method", default="classic", help="pivot method: classic, camarilla, woodie")
    an_p.set_defaults(func=cmd_analyze)

    return p


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.version:
        from eazzu import __version__
        print(f"eazzu {__version__}")
        return 0
    if not getattr(args, "cmd", None):
        print(banner())
        parser.print_help()
        return 0
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
