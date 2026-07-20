"""``eazzu`` — one CLI to rule them all.

Sub-commands
------------
* ``chat``           interactive agentic chat (BYO API keys)
* ``ask``            one-shot agent query, prints answer & exits
* ``keys``           set / get / list / delete provider keys (encrypted)
* ``providers``      list every registered provider, optionally by category
* ``trade``          knowledge / analysis / signal generation / adaptive tracking / legacy scalpers
* ``dev``            code analysis + run via vendored devtoolkit
* ``research``       run the deep-research pipeline
* ``net``            ip-info · dns · http-get
* ``web``            launch the bundled Neural chat web UI locally
* ``deriv``          real-time forex / synthetic-index data from Deriv public API
* ``music``          AI composition, synthesis, analysis, MIDI, mastering
* ``image``          procedural generation, filters, transforms, codecs
* ``webtools``       fetch, search, scrape, extract web content
* ``version``        print the installed version
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Optional


# ------------------------------------------------------------------ helpers #
BANNER = r"""
 ███████╗ █████╗ ███████╗███████╗██╗   ██╗
 ██╔════╝██╔══██╗╚══███╔╝╚══███╔╝██║   ██║
 █████╗  ███████║  ███╔╝   ███╔╝ ██║   ██║
 ██╔══╝  ██╔══██║ ███╔╝   ███╔╝  ██║   ██║
 ███████╗██║  ██║███████╗███████╗╚██████╔╝
 ╚══════╝╚═╝  ╚═╝╚══════╝╚══════╝ ╚═════╝
   agentic dev · trading · AI toolkit
"""


def _emit(obj) -> None:
    if isinstance(obj, (dict, list)):
        print(json.dumps(obj, indent=2, default=str))
    else:
        print(obj)


# ---------------------------------------------------------------- CHAT / ASK #
def cmd_chat(args) -> int:
    from eazzu.agent import Agent
    agent = Agent(provider=args.provider, model=args.model)
    print(BANNER)
    print(f"Provider: {args.provider}  ·  Model: {args.model or '(default)'}")
    print("Type '/exit' to quit · '/reset' to clear history · '/tools' to list tools\n")
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
            print("(history cleared)")
            continue
        if user == "/tools":
            for t in agent.tools:
                print(f"  · {t['name']:16s} {t['description']}")
            continue
        print("bot › ", end="", flush=True)
        turn = agent.ask(user, on_token=lambda c: (sys.stdout.write(c), sys.stdout.flush()))
        if not turn.reply and not turn.tool_calls:
            print("(no response)")
        elif turn.tool_calls and turn.reply:
            print()
        else:
            print()
        for tc in turn.tool_calls:
            print(f"  ⤷ tool `{tc['name']}` args={tc['args']}")


def cmd_ask(args) -> int:
    from eazzu.agent import Agent
    agent = Agent(provider=args.provider, model=args.model)
    turn = agent.ask(args.prompt)
    _emit(turn.reply if not args.json else {
        "reply": turn.reply,
        "tool_calls": turn.tool_calls,
        "latency_ms": turn.latency_ms,
        "cost_usd": turn.cost_usd,
    })
    return 0


# ---------------------------------------------------------------------- KEYS #
def cmd_keys(args) -> int:
    from eazzu.providers import ConfigManager
    cm = ConfigManager()
    action = args.action
    if action == "set":
        cm.set(args.provider, args.value)
        print(f"✓ key stored for '{args.provider}' (encrypted at ~/.eazzu/)")
    elif action == "get":
        print(cm.get(args.provider) or "(not set)")
    elif action == "delete":
        cm.delete(args.provider)
        print(f"✓ deleted '{args.provider}'")
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
                result = SignalGenerator(tracker=tracker).generate(
                    candles, symbol=symbol, timeframe=timeframe,
                    min_confidence=args.min_confidence, risk_multiple=args.risk_multiple,
                    reward_multiple=args.reward_multiple, expiry_bars=args.expiry_bars,
                )
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
            print("⚠️  refusing to start live trading without --i-understand-risk")
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
    from eazzu.tools.research_tools import web_search
    _emit(web_search(args.query, args.limit))
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
    import http.server
    import socketserver
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
        _emit(_deriv_snapshot(symbols))
    return 0


def _deriv_snapshot(symbols):
    from eazzu.trading.deriv_api import get_tick
    out = {}
    for s in symbols:
        r = get_tick(s.strip())
        out[s.strip()] = r.get("tick", r)
    return {"symbols": out, "count": len(out)}


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
        import json as _json
        with open(args.path) as f:
            data = _json.load(f)
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
        import json as _json
        body = _json.loads(args.json_body) if args.json_body else None
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


# --------------------------------------------------------------------- PARSE #
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser("eazzu", description="Unified agentic developer + trading + AI toolkit")
    p.add_argument("--version", action="store_true", help="print version and exit")
    sub = p.add_subparsers(dest="cmd")

    # chat / ask
    for name, fn, help_txt in (("chat", cmd_chat, "interactive agentic chat"), ("ask", cmd_ask, "one-shot agent query")):
        sp = sub.add_parser(name, help=help_txt)
        sp.add_argument("--provider", default=os.environ.get("EAZZU_PROVIDER", "openai"))
        sp.add_argument("--model", default=os.environ.get("EAZZU_MODEL"))
        if name == "ask":
            sp.add_argument("prompt")
            sp.add_argument("--json", action="store_true")
        sp.set_defaults(func=fn)

    # keys
    kp = sub.add_parser("keys", help="manage provider API keys (encrypted)")
    ksub = kp.add_subparsers(dest="action", required=True)
    for act, extra in (("set", ["provider", "value"]), ("get", ["provider"]), ("delete", ["provider"]), ("list", [])):
        s = ksub.add_parser(act)
        for a in extra:
            s.add_argument(a)
    kp.set_defaults(func=cmd_keys)

    # providers
    pp = sub.add_parser("providers", help="list registered providers")
    pp.add_argument("--category", help="filter: llm | image | audio | search | embedding")
    pp.set_defaults(func=cmd_providers)

    # trade
    tp = sub.add_parser("trade", help="trading analysis, signal tracking, and legacy toolkit")
    tsub = tp.add_subparsers(dest="trade_action", required=True)
    tsub.add_parser("list", help="list bundled trading capabilities")
    tsub.add_parser("knowledge", help="list and validate packaged reference JSON")
    bt = tsub.add_parser("backtest", help="prepare a legacy strategy backtest")
    bt.add_argument("--strategy", default="deriv_scalper"); bt.add_argument("--symbol", default="R_75"); bt.add_argument("--days", type=int, default=30)
    for name, help_text in (("analyze", "run multi-method analysis on a local OHLCV JSON file"), ("signal", "generate an analysis-only confluence signal from local OHLCV JSON")):
        command = tsub.add_parser(name, help=help_text)
        command.add_argument("--candles", required=True)
        command.add_argument("--symbol"); command.add_argument("--timeframe")
        if name == "signal":
            command.add_argument("--min-confidence", type=float, default=0.56)
            command.add_argument("--risk-multiple", type=float, default=1.5)
            command.add_argument("--reward-multiple", type=float, default=2.0)
            command.add_argument("--expiry-bars", type=int, default=12)
            command.add_argument("--ledger")
            command.add_argument("--no-record", action="store_true")
    track = tsub.add_parser("track", help="inspect or resolve locally recorded analysis-only signals")
    track_sub = track.add_subparsers(dest="track_action", required=True)
    track_summary = track_sub.add_parser("summary", help="show outcome and adaptive-evidence statistics")
    track_summary.add_argument("--ledger"); track_summary.add_argument("--limit", type=int, default=20)
    track_resolve = track_sub.add_parser("resolve", help="resolve one signal against later OHLCV candles")
    track_resolve.add_argument("signal_id"); track_resolve.add_argument("--candles", required=True); track_resolve.add_argument("--ledger")
    lv = tsub.add_parser("live"); lv.add_argument("--i-understand-risk", action="store_true")
    tp.set_defaults(func=cmd_trade)

    # dev
    dp = sub.add_parser("dev", help="developer toolkit")
    dsub = dp.add_subparsers(dest="dev_action", required=True)
    az = dsub.add_parser("analyze"); az.add_argument("path")
    rn = dsub.add_parser("run"); rn.add_argument("path"); rn.add_argument("args", nargs="*")
    dp.set_defaults(func=cmd_dev)

    # research
    rp = sub.add_parser("research", help="quick web/deep research")
    rp.add_argument("query"); rp.add_argument("--limit", type=int, default=5)
    rp.set_defaults(func=cmd_research)

    # net
    np_ = sub.add_parser("net", help="network utilities")
    nsub = np_.add_subparsers(dest="net_action", required=True)
    ip_ = nsub.add_parser("ip"); ip_.add_argument("address")
    dn = nsub.add_parser("dns"); dn.add_argument("hostname")
    ht = nsub.add_parser("http"); ht.add_argument("url")
    np_.set_defaults(func=cmd_net)

    # web
    wp = sub.add_parser("web", help="serve the bundled chat web UI")
    wp.add_argument("--port", type=int, default=8787)
    wp.set_defaults(func=cmd_web)

    # deriv
    dp2 = sub.add_parser("deriv", help="real-time forex data via Deriv public API")
    dsub = dp2.add_subparsers(dest="deriv_action", required=True)
    dsub.add_parser("ping"); dsub.add_parser("symbols"); dsub.add_parser("status"); dsub.add_parser("time")
    tk = dsub.add_parser("tick"); tk.add_argument("symbol")
    hi = dsub.add_parser("history"); hi.add_argument("symbol"); hi.add_argument("--count", type=int, default=100); hi.add_argument("--style", default="ticks")
    cd = dsub.add_parser("candles"); cd.add_argument("symbol"); cd.add_argument("--count", type=int, default=100); cd.add_argument("--granularity", type=int, default=60)
    rt = dsub.add_parser("rates"); rt.add_argument("--base", default="USD")
    pp_ = dsub.add_parser("proposal"); pp_.add_argument("--contract-type", default="CALL"); pp_.add_argument("--symbol", default="R_100"); pp_.add_argument("--amount", type=float, default=10); pp_.add_argument("--basis", default="stake"); pp_.add_argument("--currency", default="USD"); pp_.add_argument("--duration", type=int, default=5); pp_.add_argument("--duration-unit", default="m")
    ct = dsub.add_parser("collect-ticks"); ct.add_argument("symbol"); ct.add_argument("--count", type=int, default=10); ct.add_argument("--timeout", type=float, default=30.0)
    cc = dsub.add_parser("collect-candles"); cc.add_argument("symbol"); cc.add_argument("--count", type=int, default=10); cc.add_argument("--granularity", type=int, default=60); cc.add_argument("--timeout", type=float, default=60.0)
    sn = dsub.add_parser("snapshot"); sn.add_argument("--symbols")
    dp2.set_defaults(func=cmd_deriv)

    # music
    mp = sub.add_parser("music", help="AI music composition and analysis")
    msub = mp.add_subparsers(dest="music_action", required=True)
    mel = msub.add_parser("melody"); mel.add_argument("--key", default="C"); mel.add_argument("--scale", default="major"); mel.add_argument("--bars", type=int, default=4); mel.add_argument("--mood", default="happy"); mel.add_argument("--complexity", type=float, default=0.5)
    ch = msub.add_parser("chords"); ch.add_argument("--key", default="C"); ch.add_argument("--style", default="pop"); ch.add_argument("--bars", type=int, default=4)
    dr = msub.add_parser("drums"); dr.add_argument("--genre", default="house"); dr.add_argument("--steps", type=int, default=16)
    bs = msub.add_parser("bass"); bs.add_argument("--key", default="C"); bs.add_argument("--scale", default="major"); bs.add_argument("--genre", default="house"); bs.add_argument("--bars", type=int, default=4)
    st = msub.add_parser("structure"); st.add_argument("--genre", default="pop")
    msub.add_parser("scales")
    eu = msub.add_parser("euclidean"); eu.add_argument("--steps", type=int, default=16); eu.add_argument("--pulses", type=int, default=4); eu.add_argument("--rotation", type=int, default=0)
    an = msub.add_parser("analyze"); an.add_argument("path", help="JSON with samples + sample_rate")
    mp.set_defaults(func=cmd_music)

    # image
    ip = sub.add_parser("image", help="image generation and processing")
    isub = ip.add_subparsers(dest="image_action", required=True)
    gr = isub.add_parser("gradient"); gr.add_argument("--width", type=int, default=256); gr.add_argument("--height", type=int, default=256); gr.add_argument("--direction", default="horizontal"); gr.add_argument("--color1", default="0,0,0"); gr.add_argument("--color2", default="255,255,255")
    pl = isub.add_parser("plasma"); pl.add_argument("--width", type=int, default=256); pl.add_argument("--height", type=int, default=256); pl.add_argument("--scale", type=float, default=0.05)
    mb = isub.add_parser("mandelbrot"); mb.add_argument("--width", type=int, default=256); mb.add_argument("--height", type=int, default=256); mb.add_argument("--max-iter", type=int, default=80); mb.add_argument("--zoom", type=float, default=1.0); mb.add_argument("--cx", type=float, default=-0.5); mb.add_argument("--cy", type=float, default=0.0)
    nz = isub.add_parser("noise"); nz.add_argument("--width", type=int, default=256); nz.add_argument("--height", type=int, default=256); nz.add_argument("--scale", type=float, default=1.0); nz.add_argument("--seed", type=int, default=42)
    cb = isub.add_parser("checkerboard"); cb.add_argument("--width", type=int, default=256); cb.add_argument("--height", type=int, default=256); cb.add_argument("--cells", type=int, default=8); cb.add_argument("--color1", default="0,0,0"); cb.add_argument("--color2", default="255,255,255")
    isub.add_parser("pil")
    ip.set_defaults(func=cmd_image)

    # webtools
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

    return p


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.version:
        from eazzu import __version__
        print(f"eazzu {__version__}")
        return 0
    if not getattr(args, "cmd", None):
        print(BANNER)
        parser.print_help()
        return 0
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
