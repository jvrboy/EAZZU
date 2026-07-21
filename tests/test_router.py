"""Tests for the multi-provider router (auto mode).

All tests are fully offline — they register fake providers that return
canned responses / raise simulated errors.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

import pytest


# --------------------- helpers: fake provider, temp config -------------- #
class FakeResponse:
    def __init__(self, content, provider="fake", model="fake-model", fail=False, status=None, latency=0.0):
        self.content = content
        self.provider = provider
        self.model = model
        self.fail = fail
        self.status = status
        self.latency = latency
        self.prompt_tokens = 5
        self.completion_tokens = 5
        self.total_tokens = 10
        self.cost_usd = 0.0
        self.latency_ms = 0.0
        self.raw = {}

    def to_dict(self):
        return {
            "content": self.content, "provider": self.provider, "model": self.model,
            "prompt_tokens": self.prompt_tokens, "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens, "cost_usd": self.cost_usd,
        }


class FakeProvider:
    """A provider whose `chat` is driven by a list of (response_or_exception)."""
    name = "fake"
    default_model = "fake-model"
    default_base_url = ""
    price_in_per_1k = 0.0
    price_out_per_1k = 0.0
    category = "llm"

    def __init__(self, api_key=None, base_url=None, timeout=120, extra_headers=None, **kwargs):
        self.api_key = api_key
        self.calls = 0
        self._queue = []
        # Route-specific queues via api_key
        self._key_queues = {}

    def load_queue(self, key, responses):
        self._key_queues[key] = list(responses)

    def chat(self, messages, model=None, **kwargs):
        self.calls += 1
        q = self._key_queues.get(self.api_key, self._queue)
        if not q:
            raise AssertionError(f"FakeProvider[{self.api_key}]: chat called with empty queue (test bug)")
        item = q.pop(0)
        if isinstance(item, Exception):
            raise item
        if isinstance(item, FakeResponse):
            return item
        return FakeResponse(str(item), provider=self.name)

    def stream(self, messages, model=None, **kwargs):
        resp = self.chat(messages, model=model, **kwargs)
        yield resp.content


class ExplodingProvider(FakeProvider):
    name = "broken"
    default_model = "broken-model"


# ---------------------------------------------------------------- tests #
def _register_fakes(monkeypatch):
    """Register fake providers into the PROVIDER_REGISTRY and reset connector cache."""
    import eazzu.providers.core.registry as reg
    import eazzu.providers.router as router
    # Clean slate registration (note: dict, order matters but tests use explicit names)
    monkeypatch.setitem(reg.PROVIDER_REGISTRY, "fake", FakeProvider)
    monkeypatch.setitem(reg.PROVIDER_REGISTRY, "broken", ExplodingProvider)
    # Add to ENV_VAR_MAP so env detection works.
    monkeypatch.setitem(router.ENV_VAR_MAP, "fake", "FAKE_API_KEY")
    monkeypatch.setitem(router.ENV_VAR_MAP, "broken", "BROKEN_API_KEY")


def _make_cm(tmp_path, keys_by_provider):
    """Create a ConfigManager pointing at a temp keys.enc file."""
    from eazzu.providers.core.config import ConfigManager
    cm = ConfigManager(
        config_file=tmp_path / "keys.enc",
        key_file=tmp_path / "master.key",
    )
    for prov, ks in keys_by_provider.items():
        if isinstance(ks, (list, tuple)):
            cm.set(prov, ",".join(ks))
        else:
            cm.set(prov, ks)
    return cm


def test_split_keys_parses_formats():
    from eazzu.providers.router import _split_keys
    assert _split_keys("") == []
    assert _split_keys("single") == ["single"]
    assert _split_keys("a,b,c") == ["a", "b", "c"]
    assert _split_keys("a\nb\nc") == ["a", "b", "c"]
    assert _split_keys('["x","y"]') == ["x", "y"]
    # dedupe + strip
    assert _split_keys("a, a, b") == ["a", "b"]
    assert _split_keys(' "k1" , "k2" ') == ["k1", "k2"]


def test_mask_key():
    from eazzu.providers.router import mask_key
    assert mask_key("") == "(no-key)"
    assert mask_key("abc") == "***"
    assert "…" in mask_key("sk-1234567890abcdef")
    assert mask_key("sk-1234567890abcdef").startswith("sk-1")
    assert mask_key("sk-1234567890abcdef").endswith("cdef")


def test_config_manager_multi_key(tmp_path):
    cm = _make_cm(tmp_path, {"fake": "k1"})
    assert cm.list_keys("fake") == ["k1"]
    cm.add_key("fake", "k2")
    cm.add_key("fake", "k3")
    assert cm.list_keys("fake") == ["k1", "k2", "k3"]
    # dedupe
    cm.add_key("fake", "k2")
    assert cm.list_keys("fake") == ["k1", "k2", "k3"]
    # remove by index
    cm.remove_key("fake", 2)
    assert cm.list_keys("fake") == ["k1", "k3"]
    # remove by value
    cm.remove_key("fake", "k1")
    assert cm.list_keys("fake") == ["k3"]


def test_router_discovers_multi_key_endpoints(tmp_path, monkeypatch):
    _register_fakes(monkeypatch)
    cm = _make_cm(tmp_path, {"fake": ["k1", "k2", "k3"]})
    from eazzu.providers.router import ProviderRouter
    from eazzu.providers import Connector
    conn = Connector(config_manager=cm)
    r = ProviderRouter(connector=conn, config=cm, persist_path=tmp_path / "stats.json")
    # Three endpoints for 'fake', each with their own key
    assert len(r.endpoints) == 3
    keys = sorted(ep.api_key for ep in r.endpoints)
    assert keys == ["k1", "k2", "k3"]
    # Status reports healthy
    st = r.status()
    assert st["total_endpoints"] == 3
    assert st["healthy"] == 3


def test_router_picks_first_healthy_endpoint(tmp_path, monkeypatch):
    _register_fakes(monkeypatch)
    cm = _make_cm(tmp_path, {"fake": ["k1", "k2"]})
    from eazzu.providers.router import ProviderRouter
    from eazzu.providers import Connector
    conn = Connector(config_manager=cm)
    r = ProviderRouter(connector=conn, config=cm, strategy="random",
                       persist_path=tmp_path / "stats.json")
    # Pre-seed queues so first candidate succeeds (we'll fix order)
    # Force deterministic ordering: set strategy to healthiest with no stats => stable? just try all.
    r.strategy = "random"
    # Prime both endpoints to respond PONG
    for ep in r.endpoints:
        FakeProvider.name = "fake"  # ensure name consistent
        # Inject response by patching connector.get_provider's instance
    # Patch get_provider to return a per-key FakeProvider with queues.
    inst_by_key = {}
    for ep in r.endpoints:
        fp = FakeProvider(api_key=ep.api_key)
        fp.load_queue(ep.api_key, [FakeResponse(f"hi-from-{ep.api_key}")])
        inst_by_key[ep.api_key] = fp
    def fake_get_provider(name, api_key=None, base_url=None, **kw):
        return inst_by_key[api_key]
    monkeypatch.setattr(conn, "get_provider", fake_get_provider)
    res = r.chat([{"role": "user", "content": "hello"}])
    assert res.response is not None
    assert res.response.content.startswith("hi-from-")
    assert res.attempts == 1
    assert res.provider == "fake"


def test_router_fails_over_on_error(tmp_path, monkeypatch):
    """If k1 raises, k2 should be used seamlessly."""
    _register_fakes(monkeypatch)
    cm = _make_cm(tmp_path, {"fake": ["k1", "k2"]})
    from eazzu.providers.router import ProviderRouter
    from eazzu.providers import Connector
    conn = Connector(config_manager=cm)
    r = ProviderRouter(connector=conn, config=cm, strategy="random",
                       persist_path=tmp_path / "stats.json", max_attempts=4)
    k1, k2 = r.endpoints[0].api_key, r.endpoints[1].api_key
    fp1 = FakeProvider(api_key=k1)
    # k1 always fails
    fp1.load_queue(k1, [RuntimeError("HTTP 429: rate limited")] * 10)
    fp2 = FakeProvider(api_key=k2)
    fp2.load_queue(k2, [FakeResponse("via-k2")])
    inst_by_key = {k1: fp1, k2: fp2}
    # Force k1 to be tried first among READY candidates; simulate random rotation.
    _orig = r._ordered_candidates
    def fixed_order():
        # Fall back to real ordering but re-sort to put k1 before k2 when both ready
        ready = [e for e in r.endpoints if e.is_ready()]
        ready.sort(key=lambda e: 0 if e.api_key == k1 else 1)
        return ready or _orig()
    monkeypatch.setattr(r, "_ordered_candidates", fixed_order)
    monkeypatch.setattr(conn, "get_provider", lambda name, api_key=None, **kw: inst_by_key[api_key])
    failovers = []
    res = r.chat([{"role": "user", "content": "hello"}], on_failover=lambda e: failovers.append(e))
    assert res.response.content == "via-k2"
    assert res.attempts >= 2
    assert len(failovers) >= 1
    # Endpoint labels use "fake #1"/"fake #2" when there are multiple keys.
    assert any("fake" in f["endpoint"] for f in failovers)
    # k2 was the successful one
    assert fp2.calls >= 1
    # k1 had at least one failure
    assert fp1.calls >= 1
    ep_k1 = next(e for e in r.endpoints if e.api_key == k1)
    assert ep_k1.strikes >= 1


def test_router_raises_when_all_exhausted(tmp_path, monkeypatch):
    _register_fakes(monkeypatch)
    cm = _make_cm(tmp_path, {"fake": ["k1"]})
    from eazzu.providers.router import ProviderRouter
    from eazzu.providers import Connector
    conn = Connector(config_manager=cm)
    r = ProviderRouter(connector=conn, config=cm, max_attempts=3,
                       persist_path=tmp_path / "stats.json")
    fp = FakeProvider(api_key="k1")
    # Queue always-fails responses for many attempts
    fp.load_queue("k1", [RuntimeError("HTTP 402: quota exceeded")] * 20)
    monkeypatch.setattr(conn, "get_provider", lambda *a, **kw: fp)
    with pytest.raises(RuntimeError) as ei:
        r.chat([{"role": "user", "content": "hi"}])
    assert "exhausted" in str(ei.value) or "router" in str(ei.value).lower() or "router" in str(ei.value)


def test_router_honors_non_retryable(tmp_path, monkeypatch):
    """A 400 / bad-request must NOT trigger failover (it's not the key's fault).

    We force k1 to be tried first; k1 raises HTTP 400 which is non-retryable,
    so the call must raise without ever touching k2.
    """
    _register_fakes(monkeypatch)
    cm = _make_cm(tmp_path, {"fake": ["k1", "k2"]})
    from eazzu.providers.router import ProviderRouter
    from eazzu.providers import Connector
    conn = Connector(config_manager=cm)
    r = ProviderRouter(connector=conn, config=cm, max_attempts=5,
                       persist_path=tmp_path / "stats.json")
    k1, k2 = r.endpoints[0].api_key, r.endpoints[1].api_key
    fp1 = FakeProvider(api_key=k1)
    fp1.load_queue(k1, [RuntimeError("HTTP 400: bad request")] * 20)
    fp2 = FakeProvider(api_key=k2)
    fp2.load_queue(k2, [FakeResponse("never-reached")])
    inst_by_key = {k1: fp1, k2: fp2}
    # Pin ordering: k1 first among READY candidates.
    def fixed_order():
        ready = [e for e in r.endpoints if e.is_ready()]
        ready.sort(key=lambda e: 0 if e.api_key == k1 else 1)
        return ready
    monkeypatch.setattr(r, "_ordered_candidates", fixed_order)
    monkeypatch.setattr(conn, "get_provider", lambda name, api_key=None, **kw: inst_by_key[api_key])
    with pytest.raises(RuntimeError):
        r.chat([{"role": "user", "content": "hi"}])
    # k2 was never called
    assert fp2.calls == 0


def test_router_strategies(tmp_path, monkeypatch):
    _register_fakes(monkeypatch)
    cm = _make_cm(tmp_path, {"fake": ["k1", "k2", "k3"]})
    from eazzu.providers.router import ProviderRouter
    from eazzu.providers import Connector
    conn = Connector(config_manager=cm)
    for strat in ("random", "healthiest", "fastest", "cheapest"):
        r = ProviderRouter(connector=conn, config=cm, strategy=strat,
                           persist_path=tmp_path / f"stats-{strat}.json")
        order = r._ordered_candidates()
        assert len(order) == 3


def test_router_reset_health(tmp_path, monkeypatch):
    _register_fakes(monkeypatch)
    cm = _make_cm(tmp_path, {"fake": "k1"})
    from eazzu.providers.router import ProviderRouter
    from eazzu.providers import Connector
    conn = Connector(config_manager=cm)
    r = ProviderRouter(connector=conn, config=cm, persist_path=tmp_path / "stats.json")
    r.endpoints[0].strikes = 5
    r.endpoints[0].cooldown_until = time.time() + 999
    r.endpoints[0].fail_count = 10
    r.reset_health()
    assert r.endpoints[0].strikes == 0
    assert r.endpoints[0].cooldown_until <= time.time()
    assert r.endpoints[0].fail_count == 0


def test_router_persists_stats(tmp_path, monkeypatch):
    _register_fakes(monkeypatch)
    cm = _make_cm(tmp_path, {"fake": "k1"})
    from eazzu.providers.router import ProviderRouter
    from eazzu.providers import Connector
    conn = Connector(config_manager=cm)
    sp = tmp_path / "stats.json"
    r = ProviderRouter(connector=conn, config=cm, persist_path=sp)
    # Mark one success
    r._mark_success(r.endpoints[0], 123.0)
    r._save_state()
    assert sp.exists()
    data = json.loads(sp.read_text())
    assert data["endpoints"][0]["success_count"] == 1


# ----------------------------------------------------------- agent auto #
def test_agent_defaults_to_auto_and_uses_router(monkeypatch, tmp_path):
    """When provider is 'auto' (default), Agent.router is populated."""
    # Clear any env keys & set up tmp home
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("FAKE_API_KEY", raising=False)
    _register_fakes(monkeypatch)
    cm = _make_cm(tmp_path, {"fake": "fk1"})
    # Replace Connector config with ours
    import eazzu.agent.core as agent_mod
    from eazzu.providers import Connector as Conn
    # Build agent with provider=auto explicitly
    a = agent_mod.Agent(provider="auto", connector=Conn(config_manager=cm))
    assert a.router is not None
    assert a.provider == "auto"


def test_agent_single_provider_disables_router(monkeypatch):
    _register_fakes(monkeypatch)
    import eazzu.agent.core as agent_mod
    a = agent_mod.Agent(provider="fake", tools=[{"name": "echo", "description": "d",
                                                 "params": {}, "run": lambda: "ok"}])
    assert a.router is None
    assert a.provider == "fake"
