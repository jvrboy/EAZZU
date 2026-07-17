"""Command-line interface for the AI Connector."""
from __future__ import annotations

import argparse
import json
import sys

from eazzu.providers import Connector, ConfigManager
from eazzu.providers.core.failover import FailoverPolicy
from eazzu.providers.providers import *  # noqa: F401,F403 — registers all


def cmd_list(args, c: Connector):
    if args.category:
        provs = c.providers(args.category)
    else:
        cats = c.categories()
        for cat, provs in cats.items():
            print(f"\n== {cat.upper()} ({len(provs)}) ==")
            print(", ".join(provs))
        return
    print("\n".join(provs))


def cmd_chat(args, c: Connector):
    messages = [{"role": "user", "content": args.prompt}]
    if args.system:
        messages.insert(0, {"role": "system", "content": args.system})
    if args.stream:
        for chunk in c.stream(
            args.provider, messages, model=args.model, base_url=args.base_url
        ):
            sys.stdout.write(chunk)
            sys.stdout.flush()
        print()
    else:
        resp = c.chat(
            args.provider, messages, model=args.model,
            base_url=args.base_url, use_cache=args.cache,
        )
        if args.json:
            print(json.dumps(resp.to_dict(), indent=2, default=str))
        else:
            print(resp.content)
            print(f"\n[tokens: p={resp.prompt_tokens} c={resp.completion_tokens}"
                  f" | ${resp.cost_usd:.6f} | {resp.latency_ms:.0f}ms]")


def cmd_failover(args, c: Connector):
    policy = FailoverPolicy(providers=args.providers.split(","), max_retries=args.retries)
    resp = c.chat_with_failover(policy, args.prompt, model=args.model)
    print(resp.content)
    print(f"[used: {resp.provider}/{resp.model}]")


def cmd_key(args, c: Connector):
    if args.action == "set":
        c.config.set(args.provider, args.value)
        print(f"Key stored for '{args.provider}' (encrypted).")
    elif args.action == "get":
        v = c.config.get(args.provider)
        print(v or "(not set)")
    elif args.action == "delete":
        c.config.delete(args.provider)
        print(f"Deleted '{args.provider}'.")
    elif args.action == "list":
        print("\n".join(c.config.list_stored()) or "(no keys stored)")


def cmd_usage(args, c: Connector):
    if args.recent:
        for row in c.tracker.recent(args.recent):
            print(row)
    else:
        s = c.tracker.summary(args.provider)
        print(json.dumps(s, indent=2))


def cmd_cache(args, c: Connector):
    if args.clear:
        if c.cache is None:
            print("Cache is disabled. Enable with --enable-cache on chat commands.")
            return
        c.cache.clear()
        print("Cache cleared.")


def build_parser():
    p = argparse.ArgumentParser("ai-connector", description="Unified AI provider CLI")
    p.add_argument("--enable-cache", action="store_true")
    sub = p.add_subparsers(dest="cmd", required=True)

    ls = sub.add_parser("list", help="List providers")
    ls.add_argument("--category", help="llm|image|audio|search|embedding|mcp")
    ls.set_defaults(func=cmd_list)

    ch = sub.add_parser("chat", help="Send a chat request")
    ch.add_argument("provider")
    ch.add_argument("prompt")
    ch.add_argument("--model")
    ch.add_argument("--system")
    ch.add_argument("--base-url")
    ch.add_argument("--stream", action="store_true")
    ch.add_argument("--json", action="store_true")
    ch.add_argument("--cache", action="store_true")
    ch.set_defaults(func=cmd_chat)

    fo = sub.add_parser("failover", help="Chat with automatic failover across providers")
    fo.add_argument("providers", help="Comma-separated list, e.g. 'openai,anthropic,groq'")
    fo.add_argument("prompt")
    fo.add_argument("--model")
    fo.add_argument("--retries", type=int, default=1)
    fo.set_defaults(func=cmd_failover)

    kk = sub.add_parser("key", help="Manage encrypted API keys")
    kk.add_argument("action", choices=["set", "get", "delete", "list"])
    kk.add_argument("provider", nargs="?")
    kk.add_argument("value", nargs="?")
    kk.set_defaults(func=cmd_key)

    us = sub.add_parser("usage", help="Show usage / cost stats")
    us.add_argument("--provider")
    us.add_argument("--recent", type=int)
    us.set_defaults(func=cmd_usage)

    ca = sub.add_parser("cache", help="Cache admin")
    ca.add_argument("--clear", action="store_true")
    ca.set_defaults(func=cmd_cache)

    gui = sub.add_parser("gui", help="Launch Tkinter GUI")
    gui.set_defaults(func=lambda a, c: _launch_gui())

    web = sub.add_parser("web", help="Launch FastAPI web UI")
    web.add_argument("--host", default="127.0.0.1")
    web.add_argument("--port", type=int, default=8000)
    web.set_defaults(func=lambda a, c: _launch_web(a.host, a.port))

    return p


def _launch_gui():
    from eazzu.providers.interfaces.gui import main as gmain
    gmain()


def _launch_web(host, port):
    from eazzu.providers.interfaces.web import run
    run(host=host, port=port)


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    c = Connector(enable_cache=getattr(args, "enable_cache", False))
    args.func(args, c)


if __name__ == "__main__":
    main()
