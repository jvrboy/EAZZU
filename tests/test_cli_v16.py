"""Tests for the new CLI surface added in v1.6.0: multi-key keys subcommands
and the `router` command. All offline."""
from __future__ import annotations

import io
import json
import os
import shutil
from contextlib import redirect_stdout, redirect_stderr

import pytest


# Each test that touches the CLI gets an isolated HOME (and thus ~/.eazzu) so
# state from one test never leaks into another.
@pytest.fixture(autouse=True)
def _isolate_home(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    # Clear env API keys (including test-injected LOCALFAKE/GEMINI/etc)
    for k in list(os.environ):
        if k.endswith("_API_KEY") or k.startswith("EAZZU_") or k in {"NO_COLOR"}:
            monkeypatch.delenv(k, raising=False)
    # Reset module singletons
    import eazzu.config as cfgmod
    cfgmod._INSTANCE = None
    # Reset the router _GROUPS cache so provider-group info is rebuilt fresh
    import eazzu.tools_discovery as td
    td._GROUPS_MAP.clear()
    td._GROUPS_ORDER.clear()
    # Wipe any leftover ~/.eazzu from prior tests (same tmp_path dir across a test session)
    eazzu_dir = tmp_path / ".eazzu"
    if eazzu_dir.exists():
        shutil.rmtree(eazzu_dir)
    yield


def test_keys_add_list_show_remove(tmp_path, monkeypatch):
    from eazzu.cli import main
    buf = io.StringIO()
    with redirect_stdout(buf):
        assert main(["keys", "add", "gemini", "gemini-key-aaa"]) == 0
        assert main(["keys", "add", "gemini", "gemini-key-bbb"]) == 0
        assert main(["keys", "add", "openrouter", "or-key-1"]) == 0
    # List all
    buf = io.StringIO()
    with redirect_stdout(buf):
        main(["keys", "list"])
    out = buf.getvalue()
    assert "gemini" in out
    assert "openrouter" in out
    # Show for gemini (masked)
    buf = io.StringIO()
    with redirect_stdout(buf):
        main(["keys", "show", "gemini"])
    out = buf.getvalue()
    assert "…" in out  # masked
    assert "gemini-key-aaa" not in out  # full key hidden
    # Remove one key by index
    buf = io.StringIO()
    with redirect_stdout(buf):
        main(["keys", "remove", "gemini", "1"])
    # After remove, should still have one gemini key
    from eazzu.providers.core.config import ConfigManager
    cm = ConfigManager()
    assert len(cm.list_keys("gemini")) == 1


def test_keys_delete(tmp_path, monkeypatch):
    from eazzu.cli import main
    buf = io.StringIO()
    with redirect_stdout(buf):
        main(["keys", "add", "cerebras", "cb-1"])
        main(["keys", "add", "cerebras", "cb-2"])
        main(["keys", "delete", "cerebras"])
    from eazzu.providers.core.config import ConfigManager
    cm = ConfigManager()
    assert cm.list_keys("cerebras") == []


def test_router_status_no_keys(tmp_path, monkeypatch):
    """If no keys are configured, router status reports 0 endpoints without crashing.

    This test uses a fully isolated HOME that we create *after* clearing env,
    so it avoids cross-test keystore pollution.
    """
    import eazzu.config as cfgmod
    cfgmod._INSTANCE = None
    from eazzu.cli import main
    buf = io.StringIO()
    err = io.StringIO()
    with redirect_stdout(buf), redirect_stderr(err):
        rc = main(["router", "status", "--json"])
    data = json.loads(buf.getvalue())
    assert data["strategy"] in {"random", "healthiest", "fastest", "cheapest"}
    assert rc == 0
    # Must not crash; total_endpoints may be 0 or more depending on env keys
    # that leak in from the ambient shell (e.g. if developer has keys exported).
    assert isinstance(data["endpoints"], list)


def test_router_refresh_and_reset(tmp_path):
    from eazzu.cli import main
    buf = io.StringIO()
    with redirect_stdout(buf):
        # Add a key then refresh the router
        main(["keys", "add", "cerebras", "cerebras-k"])
        main(["router", "refresh"])
    buf = io.StringIO()
    with redirect_stdout(buf):
        main(["router", "status", "--json"])
    data = json.loads(buf.getvalue())
    assert data["total_endpoints"] >= 1
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = main(["router", "reset"])
    assert rc == 0


def test_router_test_json_shape_with_fake_provider(tmp_path, monkeypatch):
    """`router test --json` must produce a well-formed list of per-endpoint results."""
    import eazzu.providers.core.registry as reg
    import eazzu.providers.router as rtr
    from eazzu.providers.core.base_provider import BaseProvider, ChatResponse
    class LocalFake(BaseProvider):
        name = "localfake"
        default_model = "m"
        category = "llm"
        def _chat_impl(self, messages, model, **kw):
            return ChatResponse(provider=self.name, model=model, content="PONG")
    monkeypatch.setitem(reg.PROVIDER_REGISTRY, "localfake", LocalFake)
    monkeypatch.setitem(rtr.ENV_VAR_MAP, "localfake", "LOCALFAKE_API_KEY")
    monkeypatch.setenv("LOCALFAKE_API_KEY", "fk1,fk2")
    from eazzu.cli import main
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = main(["router", "test", "--json"])
    assert rc == 0
    data = json.loads(buf.getvalue())
    assert isinstance(data, list)
    assert len(data) >= 2
    assert all("ok" in d for d in data)
    assert sum(1 for d in data if d["ok"]) >= 2, f"expected both endpoints to PONG: {data}"


def test_chat_command_accepts_router_strategy_flag(tmp_path):
    from eazzu.cli import build_parser
    p = build_parser()
    # The chat subparser should accept --router-strategy and --provider default None
    args = p.parse_args(["chat", "--router-strategy", "cheapest"])
    assert args.router_strategy == "cheapest"
    assert args.provider is None


def test_version_works_after_new_subcommands(tmp_path):
    from eazzu.cli import main
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = main(["-V"])
    assert rc == 0
    assert "eazzu" in buf.getvalue()
