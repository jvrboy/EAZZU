"""Smoke tests — verify wiring, imports, CLI plumbing, tool safety.

These tests DO NOT call any external API — they only exercise imports,
the CLI parser, and the local tools (shell allow-list, path escapes,
tool-call regex, registry shape)."""
from __future__ import annotations

import io
import os
import sys
from contextlib import redirect_stdout


# --------------------------------------------------------------- packages #
def test_package_imports():
    import eazzu
    assert eazzu.__version__


def test_get_connector():
    from eazzu import get_connector
    c = get_connector()
    provs = c.providers()
    # ai_connector ships dozens of providers; we just assert *some* are there.
    assert len(provs) > 5


def test_agent_import_lazy():
    import eazzu
    Agent = eazzu.Agent  # triggers lazy __getattr__
    assert Agent.__name__ == "Agent"


# ------------------------------------------------------------------ tools #
def test_tool_registry_shape():
    from eazzu.tools import REGISTRY
    assert isinstance(REGISTRY, list) and REGISTRY, "registry must be non-empty"
    for t in REGISTRY:
        assert set(t) >= {"name", "description", "run"}, t
        assert callable(t["run"])
        assert isinstance(t["name"], str) and t["name"]


def test_shell_allow_list_blocks_dangerous():
    from eazzu.tools.shell import run_shell
    result = run_shell("rm -rf /")
    assert result.get("error") == "command_not_allowed"


def test_shell_allowlist_allows_echo():
    from eazzu.tools.shell import run_shell
    r = run_shell("echo hello-eazzu")
    assert r["exit_code"] == 0
    assert "hello-eazzu" in r["stdout"]


def test_file_tool_refuses_escape(tmp_path, monkeypatch):
    from eazzu.tools.files import read_file
    monkeypatch.setenv("EAZZU_FS_ROOT", str(tmp_path))
    # A path that traverses outside the root should error.
    r = read_file("../../../etc/passwd")
    assert "error" in r


def test_file_write_and_read(tmp_path, monkeypatch):
    from eazzu.tools.files import read_file, write_file
    monkeypatch.setenv("EAZZU_FS_ROOT", str(tmp_path))
    w = write_file("hello.txt", "hi eazzu")
    assert w["written"] == len("hi eazzu")
    r = read_file("hello.txt")
    assert r["content"] == "hi eazzu"


def test_ip_info():
    from eazzu.tools.net_tools import ip_info
    r = ip_info("127.0.0.1")
    assert r["is_loopback"] is True
    assert r["version"] == 4


def test_trading_list():
    from eazzu.tools.trade_tools import list_strategies, backtest_strategy
    r = list_strategies()
    assert "scalpers" in r
    b = backtest_strategy()
    assert "command" in b


# ------------------------------------------------------------------ agent #
def test_agent_tool_regex_extracts_json():
    from eazzu.agent.core import Agent
    text = """Sure — let me look.
```tool
{"name": "ip_info", "args": {"address": "8.8.8.8"}}
```
"""
    call = Agent._extract_tool_call(text)
    assert call == {"name": "ip_info", "args": {"address": "8.8.8.8"}}


def test_agent_tool_regex_none_when_absent():
    from eazzu.agent.core import Agent
    assert Agent._extract_tool_call("just a plain answer.") is None


def test_agent_run_tool_dispatches():
    from eazzu.agent.core import Agent
    # Use a dummy tool list so we can construct Agent without a connector call
    dummy = [{"name": "echo", "description": "d", "params": {}, "run": lambda x: {"got": x}}]
    a = Agent(tools=dummy)
    assert a._run_tool("echo", {"x": 42}) == {"got": 42}
    assert "error" in a._run_tool("nope", {})


# -------------------------------------------------------------------- CLI #
def test_cli_version():
    from eazzu.cli import main
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = main(["--version"])
    assert rc == 0
    assert "eazzu" in buf.getvalue()


def test_cli_help_no_args():
    from eazzu.cli import main
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = main([])
    assert rc == 0
    assert "eazzu" in buf.getvalue().lower()


def test_cli_providers():
    from eazzu.cli import main
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = main(["providers", "--category", "llm"])
    assert rc == 0
    # Output is JSON, must contain at least one provider name
    assert len(buf.getvalue()) > 5


def test_cli_net_ip():
    from eazzu.cli import main
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = main(["net", "ip", "10.0.0.1"])
    assert rc == 0
    assert "is_private" in buf.getvalue()


def test_cli_trade_list():
    from eazzu.cli import main
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = main(["trade", "list"])
    assert rc == 0
    assert "scalpers" in buf.getvalue()
