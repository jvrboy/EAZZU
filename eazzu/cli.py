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
        # If we streamed, tokens already printed; otherwise print reply.
        if not turn.reply and not turn.tool_calls:
            print("(no response)")
        elif turn.tool_calls and turn.reply:
            print()  # newline after streamed content
        else:
            print()
        for tc in turn.tool_calls:
            print(f"  ⤷ tool `{tc['name']}` args={tc['args']}")
    # unreachable


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
                    candles,
                    symbol=symbol,
                    timeframe=timeframe,
                    min_confidence=args.min_confidence,
                    risk_multiple=args.risk_multiple,
                    reward_multiple=args.reward_multiple,
                    expiry_bars=args.expiry_bars,
                )
                if result.get("signal") and not args.no_record:
                    result["tracking"] = tracker.record_signal(result["signal"])
                else:
                    result["tracking"] = {
                        "recorded": False,
                        "reason": "no_signal" if not result.get("signal") else "record_disabled",
                    }
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
        print("Live trading harness is intentionally stubbed here — configure your API "
              "credentials and use the dedicated runners under `eazzu.trading.*`.")
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
    """Serve the bundled Neural chat web app from a local HTTP server."""
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


# --------------------------------------------------------------------- PARSE #
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        "eazzu",
        description="Unified agentic developer + trading + AI toolkit",
    )
    p.add_argument("--version", action="store_true", help="print version and exit")
    sub = p.add_subparsers(dest="cmd")

    # chat / ask
    for name, fn, help_txt in (("chat", cmd_chat, "interactive agentic chat"),
                                ("ask", cmd_ask, "one-shot agent query")):
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
    for act, extra in (("set", ["provider", "value"]),
                        ("get", ["provider"]),
                        ("delete", ["provider"]),
                        ("list", [])):
        s = ksub.add_parser(act)
        for a in extra:
            s.add_argument(a)
    kp.set_defaults(func=cmd_keys)

    # providers
    pp = sub.add_parser("providers", help="list registered providers")
    pp.add_argument("--category", help="filter: llm | image | audio | search | embedding")
    pp.set_defaults(func=cmd_providers)

    # trade — all intelligence commands are analysis-only and never submit orders.
    tp = sub.add_parser("trade", help="trading analysis, signal tracking, and legacy toolkit")
    tsub = tp.add_subparsers(dest="trade_action", required=True)
    tsub.add_parser("list", help="list bundled trading capabilities")
    tsub.add_parser("knowledge", help="list and validate packaged reference JSON")
    bt = tsub.add_parser("backtest", help="prepare a legacy strategy backtest")
    bt.add_argument("--strategy", default="deriv_scalper")
    bt.add_argument("--symbol", default="R_75")
    bt.add_argument("--days", type=int, default=30)

    for name, help_text in (
        ("analyze", "run multi-method analysis on a local OHLCV JSON file"),
        ("signal", "generate an analysis-only confluence signal from local OHLCV JSON"),
    ):
        command = tsub.add_parser(name, help=help_text)
        command.add_argument("--candles", required=True, help="path to JSON OHLCV candles")
        command.add_argument("--symbol", help="instrument symbol; defaults to the JSON metadata")
        command.add_argument("--timeframe", help="candle timeframe; defaults to the JSON metadata")
        if name == "signal":
            command.add_argument("--min-confidence", type=float, default=0.56)
            command.add_argument("--risk-multiple", type=float, default=1.5)
            command.add_argument("--reward-multiple", type=float, default=2.0)
            command.add_argument("--expiry-bars", type=int, default=12)
            command.add_argument("--ledger", help="path for the local signal-performance ledger")
            command.add_argument("--no-record", action="store_true", help="do not record the generated signal")

    track = tsub.add_parser("track", help="inspect or resolve locally recorded analysis-only signals")
    track_sub = track.add_subparsers(dest="track_action", required=True)
    track_summary = track_sub.add_parser("summary", help="show outcome and adaptive-evidence statistics")
    track_summary.add_argument("--ledger", help="path for the local signal-performance ledger")
    track_summary.add_argument("--limit", type=int, default=20, help="number of recent signal records to show")
    track_resolve = track_sub.add_parser("resolve", help="resolve one signal against later OHLCV candles")
    track_resolve.add_argument("signal_id")
    track_resolve.add_argument("--candles", required=True, help="path to subsequent JSON OHLCV candles")
    track_resolve.add_argument("--ledger", help="path for the local signal-performance ledger")

    lv = tsub.add_parser("live")
    lv.add_argument("--i-understand-risk", action="store_true")
    tp.set_defaults(func=cmd_trade)

    # dev
    dp = sub.add_parser("dev", help="developer toolkit")
    dsub = dp.add_subparsers(dest="dev_action", required=True)
    az = dsub.add_parser("analyze"); az.add_argument("path")
    rn = dsub.add_parser("run");     rn.add_argument("path"); rn.add_argument("args", nargs="*")
    dp.set_defaults(func=cmd_dev)

    # research
    rp = sub.add_parser("research", help="quick web/deep research")
    rp.add_argument("query")
    rp.add_argument("--limit", type=int, default=5)
    rp.set_defaults(func=cmd_research)

    # net
    np_ = sub.add_parser("net", help="network utilities")
    nsub = np_.add_subparsers(dest="net_action", required=True)
    ip_ = nsub.add_parser("ip");   ip_.add_argument("address")
    dn = nsub.add_parser("dns");   dn.add_argument("hostname")
    ht = nsub.add_parser("http");  ht.add_argument("url")
    np_.set_defaults(func=cmd_net)

    # web
    wp = sub.add_parser("web", help="serve the bundled chat web UI")
    wp.add_argument("--port", type=int, default=8787)
    wp.set_defaults(func=cmd_web)

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
