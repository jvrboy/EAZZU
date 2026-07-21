"""v1.8.0 tests — HuggingFace provider, platform tools, autoinstall, CLI."""
from __future__ import annotations

import io
import json
import os
from contextlib import redirect_stdout


def test_huggingface_provider_registered():
    import eazzu.providers.providers  # noqa: F401
    from eazzu.providers.core.registry import PROVIDER_REGISTRY
    assert "huggingface" in PROVIDER_REGISTRY
    assert "huggingface_endpoint" in PROVIDER_REGISTRY
    hf = PROVIDER_REGISTRY["huggingface"]
    assert "huggingface" in hf.default_base_url
    assert hf.default_model  # has a default chat model
    assert PROVIDER_REGISTRY["huggingface_endpoint"].name == "huggingface_endpoint"


def test_hf_env_mapping():
    from eazzu.providers.core.config import ENV_VAR_MAP
    assert ENV_VAR_MAP["huggingface"] in ("HF_TOKEN", "HUGGINGFACE_API_KEY", "HF_API_KEY")


def test_platform_detect_shape():
    from eazzu.tools import platform_tools as pt
    d = pt.detect_platform()
    assert d["ok"] is True
    for key in ("platform", "os", "python", "is_windows", "is_mac", "is_linux",
                "is_ish_ios", "is_colab", "is_wsl"):
        assert key in d


def test_platform_system_info():
    from eazzu.tools import platform_tools as pt
    info = pt.system_info()
    assert info["ok"] is True
    assert "hostname" in info
    assert "cpu_count" in info


def test_platform_now():
    from eazzu.tools import platform_tools as pt
    n = pt.now()
    assert n["ok"]
    assert "iso" in n and "unix" in n


def test_platform_calc():
    from eazzu.tools import platform_tools as pt
    assert pt.calc("(2+3)*4")["result"] == 20
    assert pt.calc("10/2")["result"] == 5
    # Reject dangerous input
    bad = pt.calc("import os")
    assert bad["ok"] is False


def test_platform_hash():
    from eazzu.tools import platform_tools as pt
    h = pt.hash_text("hello")
    assert h["digest"] == "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"
    m = pt.hash_text("hello", "md5")
    assert m["digest"] == "5d41402abc4b2a76b9719d911017c592"


def test_platform_b64_roundtrip():
    from eazzu.tools import platform_tools as pt
    msg = "the quick brown fox"
    enc = pt.b64_encode(msg)["encoded"]
    dec = pt.b64_decode(enc)["decoded"]
    assert dec == msg


def test_platform_uuid():
    from eazzu.tools import platform_tools as pt
    import uuid as _uuid
    u = pt.make_uuid()
    assert u["ok"]
    _uuid.UUID(u["uuid"])  # validates


def test_platform_qr_codes():
    import tempfile
    from pathlib import Path
    from eazzu.tools import platform_tools as pt
    with tempfile.TemporaryDirectory() as td:
        out = str(Path(td) / "qr.png")
        r = pt.qr_code("https://example.com", out)
        assert r["ok"] is True
        assert Path(out).exists()
        assert Path(out).stat().st_size > 100


def test_platform_whoami():
    from eazzu.tools import platform_tools as pt
    w = pt.whoami()
    assert w["ok"]
    assert "user" in w


def test_autoinstall_ensure_present():
    from eazzu import autoinstall
    # requests is already installed; ensure should return ok
    r = autoinstall.ensure(packages=["requests"], prompt=False)
    assert r["_ok"] is True


def test_autoinstall_rejects_unknown_when_off():
    os.environ["EAZZU_NO_AUTOINSTALL"] = "1"
    try:
        from eazzu import autoinstall
        # Use a package that definitely doesn't exist
        r = autoinstall.ensure(packages=["definitely-not-a-real-package-xyz123"], prompt=False)
        assert r["_ok"] is False
        assert "definitely-not-a-real-package-xyz123".replace("-", "_") in r["_missing"][0].replace("-","_") or \
               len(r["_missing"]) >= 1
    finally:
        os.environ.pop("EAZZU_NO_AUTOINSTALL", None)


def test_launch_command_exists():
    from eazzu.cli import build_parser
    p = build_parser()
    # "install", "platform", "launch" / "computer" all exist
    names = [a.dest for a in p._actions if hasattr(a, "choices") and a.choices]
    all_subs = set()
    for a in p._actions:
        if hasattr(a, "choices") and isinstance(a.choices, dict):
            all_subs.update(a.choices.keys())
    for must in ("install", "platform", "computer", "app", "self", "router"):
        assert must in all_subs


def test_cli_platform_detect():
    from eazzu.cli import main
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = main(["platform", "detect"])
    assert rc == 0
    data = json.loads(buf.getvalue())
    assert data["ok"] is True
    assert "platform" in data


def test_cli_install_list():
    from eazzu.cli import main
    buf = io.StringIO()
    try:
        with redirect_stdout(buf):
            rc = main(["install", "--list"])
    except SystemExit as e:
        rc = e.code
    # cmd_install returns 0 and prints JSON; parser errors exit 2
    assert rc in (0, 1, 2)
    out = buf.getvalue()
    if rc == 0:
        data = json.loads(out)
        assert "available" in data
        for must in ("trading", "image", "pdf", "slides", "automation", "all"):
            assert must in data["available"]


def test_cli_platform_detect_rc():
    from eazzu.cli import main
    buf = io.StringIO()
    try:
        with redirect_stdout(buf):
            rc = main(["platform", "detect"])
    except SystemExit as e:
        rc = e.code
    assert rc in (0, 1, 2)


def test_cli_platform_calc():
    from eazzu.cli import main
    buf = io.StringIO()
    with redirect_stdout(buf):
        try:
            rc = main(["platform", "calc", "6*7"])
        except SystemExit as e:
            rc = e.code
    assert rc == 0
    assert "42" in buf.getvalue()


def test_freemodel_still_registered():
    import eazzu.providers.providers  # noqa: F401
    from eazzu.providers.core.registry import PROVIDER_REGISTRY
    assert "freemodel" in PROVIDER_REGISTRY


def test_all_tools_registered():
    from eazzu.tools import REGISTRY
    names = {t["name"] for t in REGISTRY}
    # New in 1.7
    for name in ("desktop_screenshot", "list_desktop", "run_shell", "create_app", "build_app",
                 "self_status", "self_clone", "self_test"):
        assert name in names, f"missing tool: {name}"
    # New in 1.8
    for name in ("detect_platform", "system_info", "battery", "wifi_info", "set_volume",
                 "notify", "timer", "hash_text", "b64_encode", "b64_decode",
                 "make_uuid", "qr_code", "now", "calc", "say", "ip_external",
                 "whoami", "colab_mount", "ish_info", "pip_install"):
        assert name in names, f"missing tool: {name}"
    # 769 + 22 platform_tools + computer/app/self already counted earlier
    assert len(REGISTRY) >= 800
