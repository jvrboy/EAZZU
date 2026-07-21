"""Smoke tests for v1.7.0: computer tools, app builder, self-updater, Telegram bot,
and the new freemodel.dev provider."""
from __future__ import annotations

import json
import os
import io
from contextlib import redirect_stdout


def test_computer_tools_import_and_shapes():
    from eazzu.tools.computer_tools import TOOLS
    names = {t["name"] for t in TOOLS}
    expected = {
        "screenshot", "list_desktop", "list_directory", "open_file", "run_shell",
        "run_cmd", "run_powershell", "file_info", "clipboard_read", "clipboard_write",
        "list_processes", "active_window", "dialog_alert",
        "keyboard_type", "mouse_click", "mouse_move",
    }
    assert expected.issubset(names)
    for t in TOOLS:
        assert callable(t["run"])
        assert "description" in t


def test_computer_list_directory(tmp_path):
    from eazzu.tools import computer_tools as ct
    (tmp_path / "a.txt").write_text("x")
    (tmp_path / "d").mkdir()
    monkeypatch = __import__("pytest").MonkeyPatch()
    monkeypatch.setenv("EAZZU_FS_ROOT", str(tmp_path))
    r = ct.list_directory(".")
    assert r["ok"] is True
    names = [e["name"] for e in r["entries"]]
    assert "a.txt" in names and "d" in names
    monkeypatch.undo()


def test_computer_run_shell_echo():
    from eazzu.tools import computer_tools as ct
    r = ct.run_shell_cmd("echo hello-eazzu")
    assert r["ok"] is True
    assert "hello-eazzu" in r["stdout"]


def test_computer_file_info(tmp_path):
    from eazzu.tools import computer_tools as ct
    f = tmp_path / "foo.txt"
    f.write_text("hello")
    monkeypatch = __import__("pytest").MonkeyPatch()
    monkeypatch.setenv("EAZZU_FS_ROOT", str(tmp_path))
    info = ct.file_info("foo.txt")
    assert info["ok"] is True
    assert info["name"] == "foo.txt"
    assert info["size"] == 5
    monkeypatch.undo()


def test_computer_platform_utils_run():
    # Active window / processes should not crash even in sandbox.
    from eazzu.tools import computer_tools as ct
    aw = ct.active_window()
    assert "ok" in aw
    lp = ct.list_processes()
    assert lp.get("ok") in (True, False)  # may fail in sandbox


def test_app_builder_create_html(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("EAZZU_FS_ROOT", str(tmp_path))
    # Reset singleton
    import eazzu.config as cfg
    cfg._INSTANCE = None
    from eazzu.tools.app_builder_tools import create_app, build_app, package_app
    r = create_app("test app", language="html")
    assert r["ok"] is True
    assert os.path.exists(r["dir"])
    assert "index.html" in os.listdir(r["dir"])
    pkg = package_app(r["dir"])
    assert pkg["ok"] is True and pkg["bytes"] > 0


def test_app_builder_python_run(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("EAZZU_FS_ROOT", str(tmp_path))
    import eazzu.config as cfg
    cfg._INSTANCE = None
    from eazzu.tools.app_builder_tools import create_app, run_app
    r = create_app("hi", language="python")
    assert r["ok"]
    run = run_app(r["dir"], timeout=10)
    assert run["ok"] is True
    assert "Hello" in run["stdout"]


def test_self_updater_status():
    from eazzu.tools import self_updater_tools as su
    s = su.status_self()
    assert s["ok"] is True
    assert s["is_git_clone"] is True
    assert s["version"]
    assert s["git_root"].endswith("EAZZU")


def test_freemodel_provider_registered():
    import eazzu.providers.providers  # noqa: F401
    from eazzu.providers.core.registry import PROVIDER_REGISTRY
    assert "freemodel" in PROVIDER_REGISTRY
    assert "freemodel_codex" in PROVIDER_REGISTRY
    fm = PROVIDER_REGISTRY["freemodel"]
    assert fm.default_base_url.startswith("https://api.freemodel.dev")
    assert fm.default_model == "gpt-5.5"


def test_freemodel_env_mapping():
    from eazzu.providers.core.config import ENV_VAR_MAP
    assert "freemodel" in ENV_VAR_MAP
    assert ENV_VAR_MAP["freemodel"] == "FREEMODEL_API_KEY"


def test_telegram_runbot_signature():
    from eazzu.bot import telegram
    import inspect
    sig = inspect.signature(telegram.run_bot)
    params = sig.parameters
    assert "token" in params
    assert "provider" in params
    assert "router_strategy" in params
    # Telegram helpers
    assert hasattr(telegram, "send_message")
    assert hasattr(telegram, "_menu_kb")
    assert hasattr(telegram, "_files_kb")


def test_cli_computer_subcommand_help():
    from eazzu.cli import main
    buf = io.StringIO()
    with redirect_stdout(buf):
        try:
            main(["computer", "--help"])
        except SystemExit as e:
            assert e.code == 0
    assert "screenshot" in buf.getvalue()


def test_cli_app_build_help():
    from eazzu.cli import main
    buf = io.StringIO()
    with redirect_stdout(buf):
        try:
            main(["app", "--help"])
        except SystemExit as e:
            assert e.code == 0
    assert "build" in buf.getvalue()


def test_cli_self_status():
    from eazzu.cli import main
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = main(["self", "status"])
    assert rc == 0
    data = json.loads(buf.getvalue())
    assert data["is_git_clone"] in (True, False)
    assert "version" in data
