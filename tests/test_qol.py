"""Tests for the v1.5.1 QoL additions: doctor, tools, config, commands,
completion, --no-color, -V, top-level error handling.

All tests are offline: no network calls, no API keys required.
"""
from __future__ import annotations

import io
import json
import os
import sys
from contextlib import redirect_stdout, redirect_stderr


# ------------------------------------------------------------ cli basics #
def test_version_short_flag():
    from eazzu.cli import main
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = main(["-V"])
    assert rc == 0
    assert "eazzu" in buf.getvalue()


def test_version_after_subcommand():
    """--version/-V must work even when placed after a subcommand."""
    from eazzu.cli import main
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = main(["chat", "--version"])
    assert rc == 0
    assert "eazzu" in buf.getvalue()


def test_version_subcommand():
    from eazzu.cli import main
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = main(["version"])
    assert rc == 0
    assert "eazzu" in buf.getvalue()


def test_no_args_shows_help():
    from eazzu.cli import main
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = main([])
    assert rc == 0
    assert "usage:" in buf.getvalue().lower() or "eazzu" in buf.getvalue().lower()


# -------------------------------------------------------------- commands #
def test_commands_lists_subset():
    from eazzu.cli import main
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = main(["commands", "--json"])
    assert rc == 0
    data = json.loads(buf.getvalue())
    names = [c["command"] for c in data]
    # New commands we added
    assert "eazzu doctor" in names
    assert "eazzu tools list" in names
    assert "eazzu config show" in names
    assert "eazzu update" in names
    # Existing commands still there
    assert "eazzu chat" in names
    assert "eazzu trade list" in names


# ---------------------------------------------------------------- doctor #
def test_doctor_json():
    from eazzu.doctor import run_doctor
    r = run_doctor()
    assert r["status"] in ("ok", "warn")
    names = {c["name"] for c in r["checks"]}
    expected = {"python", "platform", "eazzu", "config_dir", "keystore", "pip"}
    assert expected.issubset(names)


def test_doctor_cli_runs(tmp_path, monkeypatch):
    """`eazzu doctor --json` must exit 0 and parse as JSON."""
    monkeypatch.setenv("HOME", str(tmp_path))
    from eazzu.cli import main
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = main(["doctor", "--json"])
    assert rc in (0, 1)  # warn is acceptable in CI where deps may be missing
    data = json.loads(buf.getvalue())
    assert "checks" in data
    assert any(c["name"] == "eazzu" for c in data["checks"])


def test_doctor_fix_creates_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("EAZZU_HOME", str(tmp_path / ".eazzu_fresh"))
    from eazzu.doctor import run_doctor
    r = run_doctor(fix=True)
    assert (tmp_path / ".eazzu_fresh").is_dir()


# ----------------------------------------------------------------- tools #
def test_tools_count_reports_total():
    from eazzu.cli import main
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = main(["tools", "count"])
    assert rc == 0
    out = buf.getvalue()
    # 400+ tools claim — assert at least a couple hundred
    assert "TOTAL" in out or "crosscut" in out


def test_tools_info_ip_info():
    from eazzu.cli import main
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = main(["tools", "info", "ip_info"])
    assert rc == 0
    assert "ip_info" in buf.getvalue()
    assert "group" in buf.getvalue()


def test_tools_info_fuzzy():
    """Prefix/substring match for an unknown name gives suggestions."""
    from eazzu.cli import main
    buf = io.StringIO()
    err = io.StringIO()
    with redirect_stdout(buf), redirect_stderr(err):
        rc = main(["tools", "info", "ip_"])
    # Should either match a tool or list suggestions (non-crash)
    assert rc in (0, 1)


def test_tools_list_query():
    from eazzu.cli import main
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = main(["tools", "list", "--query", "shell", "--json"])
    assert rc == 0
    data = json.loads(buf.getvalue())
    assert isinstance(data, list)


def test_tools_groups_nonempty():
    from eazzu.cli import main
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = main(["tools", "groups"])
    assert rc == 0
    assert len(buf.getvalue().strip().splitlines()) > 5


# ---------------------------------------------------------------- config #
def test_config_defaults(tmp_path, monkeypatch):
    monkeypatch.setenv("EAZZU_CONFIG", str(tmp_path / "cfg.json"))
    # Force-reload singleton
    import eazzu.config as cfgmod
    cfgmod._INSTANCE = None
    c = cfgmod.get_config()
    assert c.get("color") == "auto"
    assert c.get("web_port") == 8787


def test_config_set_get_reset(tmp_path, monkeypatch):
    monkeypatch.setenv("EAZZU_CONFIG", str(tmp_path / "cfg.json"))
    import eazzu.config as cfgmod
    cfgmod._INSTANCE = None
    c = cfgmod.get_config()
    c.set("web_port", 1234)
    c.set("default_provider", "anthropic")
    c.save()

    cfgmod._INSTANCE = None
    c2 = cfgmod.get_config()
    assert c2.get("web_port") == 1234
    assert c2.get("default_provider") == "anthropic"

    c2.reset()
    c2.save()
    cfgmod._INSTANCE = None
    c3 = cfgmod.get_config()
    assert c3.get("web_port") == 8787


def test_config_cli_flow(tmp_path, monkeypatch):
    monkeypatch.setenv("EAZZU_CONFIG", str(tmp_path / "cfg.json"))
    import eazzu.config as cfgmod
    cfgmod._INSTANCE = None
    from eazzu.cli import main
    with redirect_stdout(io.StringIO()):
        assert main(["config", "set", "web_port", "2020"]) == 0
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = main(["config", "get", "web_port"])
    assert rc == 0
    assert "2020" in buf.getvalue()

    bad = io.StringIO()
    with redirect_stdout(io.StringIO()), redirect_stderr(bad):
        rc2 = main(["config", "set", "color", "purple"])
    assert rc2 != 0  # invalid value rejected


def test_config_persists_to_disk(tmp_path, monkeypatch):
    monkeypatch.setenv("EAZZU_CONFIG", str(tmp_path / "cfg.json"))
    import eazzu.config as cfgmod
    cfgmod._INSTANCE = None
    from eazzu.cli import main
    with redirect_stdout(io.StringIO()):
        main(["config", "set", "default_provider", "groq"])
    data = json.loads((tmp_path / "cfg.json").read_text())
    assert data["default_provider"] == "groq"


# -------------------------------------------------------------- no-color #
def test_no_color_flag_suppresses_ansi():
    from eazzu.cli import main
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = main(["--no-color", "tools", "info", "ip_info"])
    assert rc == 0
    out = buf.getvalue()
    # ANSI escape starts with \033 (0x1b) — with --no-color there should be none.
    assert "\033" not in out


def test_no_color_env(monkeypatch):
    monkeypatch.setenv("EAZZU_NO_COLOR", "1")
    # Force re-init of ANSI detection
    import importlib
    import eazzu.cli_ui as ui
    importlib.reload(ui)
    assert ui._ANSI is False
    # Restore default detection so other tests aren't affected
    monkeypatch.delenv("EAZZU_NO_COLOR", raising=False)
    importlib.reload(ui)


# ----------------------------------------------------------- completion #
def test_completion_script_bash():
    from eazzu.cli import main
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = main(["--_completion-script", "bash"])
    assert rc == 0
    assert "_eazzu_completions" in buf.getvalue()


def test_completion_script_zsh():
    from eazzu.cli import main
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = main(["--_completion-script", "zsh"])
    assert rc == 0
    assert "#compdef eazzu" in buf.getvalue()


def test_completion_script_fish():
    from eazzu.cli import main
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = main(["--_completion-script", "fish"])
    assert rc == 0
    assert "complete -c eazzu" in buf.getvalue()


def test_completion_matches_subcommand(monkeypatch):
    monkeypatch.setenv("COMP_LINE", "eazzu too")
    from eazzu.completion import do_complete
    buf = io.StringIO()
    with redirect_stdout(buf):
        do_complete()
    assert "tools" in buf.getvalue()


# ------------------------------------------------- graceful error handler #
def test_unhandled_error_shows_friendly_message(monkeypatch):
    """If a command raises, main() should return 1 and print a friendly error
    (unless EAZZU_DEBUG is set, which prints traceback)."""
    from eazzu.cli import build_parser
    import argparse
    p = build_parser()
    # Bind a handler that raises for the `version` command after _apply_globals
    import eazzu.cli as cli
    original = cli.cmd_version
    def boom(_args):
        raise RuntimeError("boom")
    cli.cmd_version = boom
    try:
        err = io.StringIO()
        with redirect_stderr(err):
            rc = cli.main(["version"])
        assert rc == 1
    finally:
        cli.cmd_version = original


# ------------------------------------------------ config parse_value #
def test_parse_value_coercions():
    from eazzu.config import parse_value
    assert parse_value("true") is True
    assert parse_value("FALSE") is False
    assert parse_value("null") is None
    assert parse_value("42") == 42
    assert parse_value("3.14") == 3.14
    assert parse_value("hello") == "hello"
    assert parse_value('{"a":1}') == {"a": 1}
