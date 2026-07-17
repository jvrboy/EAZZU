"""FastAPI web UI + REST API for the connector."""
from __future__ import annotations

import json
from typing import Optional

from ai_connector import Connector
from eazzu.providers.core.failover import FailoverPolicy
from eazzu.providers.providers import *  # noqa: F401,F403


INDEX_HTML = """
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>AI API Connector</title>
<style>
 body{font-family:system-ui,Segoe UI,Arial;margin:0;padding:20px;background:#0f172a;color:#e2e8f0;}
 h1{margin:0 0 6px;font-weight:600;letter-spacing:.5px}
 .sub{color:#94a3b8;margin-bottom:20px;font-size:14px}
 .wrap{max-width:1100px;margin:0 auto}
 .row{display:flex;gap:12px;flex-wrap:wrap;margin-bottom:10px}
 label{font-size:12px;color:#94a3b8;display:block;margin-bottom:4px}
 select,input,textarea,button{background:#1e293b;border:1px solid #334155;color:#e2e8f0;
    border-radius:8px;padding:10px 12px;font-size:14px;font-family:inherit}
 textarea{width:100%;box-sizing:border-box;min-height:110px;resize:vertical}
 button{cursor:pointer;background:#2563eb;border:none;font-weight:600}
 button:hover{background:#1d4ed8}
 button.ghost{background:transparent;border:1px solid #334155}
 .col{flex:1;min-width:180px}
 pre{background:#0b1220;padding:14px;border-radius:10px;overflow:auto;
    border:1px solid #1e293b;min-height:200px;white-space:pre-wrap}
 .stats{color:#94a3b8;font-size:12px;margin-top:6px}
 .chk{display:inline-flex;gap:6px;align-items:center;font-size:13px}
 .tab{display:flex;gap:8px;margin-bottom:12px}
 .tab button{background:#1e293b;color:#cbd5e1}
 .tab button.active{background:#2563eb;color:white}
 .hidden{display:none}
 table{width:100%;border-collapse:collapse;font-size:13px}
 td,th{padding:6px 10px;border-bottom:1px solid #1e293b;text-align:left}
</style>
</head>
<body>
<div class="wrap">
  <h1>🔌 AI API Connector</h1>
  <div class="sub">Unified access to 80+ AI providers · LLM · Image · Audio · Search · Embedding · MCP</div>

  <div class="tab">
    <button id="tab-chat" class="active" onclick="showTab('chat')">Chat</button>
    <button id="tab-keys" onclick="showTab('keys')">Keys</button>
    <button id="tab-usage" onclick="showTab('usage')">Usage</button>
    <button id="tab-failover" onclick="showTab('failover')">Failover</button>
    <button id="tab-mcp" onclick="showTab('mcp')">MCP</button>
  </div>

  <div id="pane-chat">
    <div class="row">
      <div class="col"><label>Provider</label>
        <select id="provider" onchange="onProv()"></select></div>
      <div class="col"><label>Model</label>
        <input id="model" placeholder="default"></div>
      <div class="col"><label>Base URL (optional)</label>
        <input id="base_url" placeholder="use provider default"></div>
    </div>
    <div class="row">
      <label class="chk"><input type="checkbox" id="stream" checked> Stream</label>
      <label class="chk"><input type="checkbox" id="cache"> Cache</label>
    </div>
    <label>Prompt</label>
    <textarea id="prompt">Hello! Introduce yourself in one sentence.</textarea>
    <div class="row" style="margin-top:8px">
      <button onclick="send()">Send</button>
      <button class="ghost" onclick="document.getElementById('out').textContent=''">Clear</button>
    </div>
    <label style="margin-top:14px">Response</label>
    <pre id="out"></pre>
    <div class="stats" id="stats"></div>
  </div>

  <div id="pane-keys" class="hidden">
    <p>Store API keys encrypted on disk (Fernet). Values are never sent back to the browser.</p>
    <div class="row">
      <div class="col"><label>Provider</label>
        <select id="k_prov"></select></div>
      <div class="col"><label>API Key</label>
        <input id="k_val" type="password" placeholder="paste key"></div>
    </div>
    <div class="row">
      <button onclick="setKey()">Save</button>
      <button class="ghost" onclick="listKeys()">Refresh List</button>
    </div>
    <pre id="k_list"></pre>
  </div>

  <div id="pane-usage" class="hidden">
    <div class="row"><button onclick="loadUsage()">Reload</button></div>
    <pre id="u_out"></pre>
  </div>

  <div id="pane-failover" class="hidden">
    <label>Providers (comma-separated priority order)</label>
    <input id="fo_provs" style="width:100%" value="openai,anthropic,groq">
    <label style="margin-top:8px">Prompt</label>
    <textarea id="fo_prompt">Explain LLM failover in one paragraph.</textarea>
    <div class="row" style="margin-top:8px"><button onclick="foSend()">Send with Failover</button></div>
    <pre id="fo_out"></pre>
  </div>

  <div id="pane-mcp" class="hidden">
    <p>Speak to any MCP-compliant server via JSON-RPC. Uses the built-in <code>custom_mcp</code> provider.</p>
    <label>MCP Server URL</label>
    <input id="mcp_url" style="width:100%" placeholder="https://your-mcp-server/rpc">
    <div class="row" style="margin-top:8px">
      <div class="col"><label>Tool Name</label><input id="mcp_tool" placeholder="auto-detect"></div>
      <div class="col"><label>Tool Args (JSON)</label><input id="mcp_args" value='{"query":"hello"}'></div>
    </div>
    <div class="row"><button onclick="mcpList()">List Tools</button>
      <button onclick="mcpCall()">Call Tool</button></div>
    <pre id="mcp_out"></pre>
  </div>
</div>

<script>
let PROVIDERS = [];
async function loadProviders(){
  const r = await fetch('/api/providers'); PROVIDERS = await r.json();
  const sel = document.getElementById('provider'), sel2 = document.getElementById('k_prov');
  sel.innerHTML = sel2.innerHTML = '';
  for (const p of PROVIDERS){
    for (const s of [sel, sel2]){
      const o = document.createElement('option'); o.value = p.name; o.textContent = `${p.name} (${p.category})`;
      s.appendChild(o);
    }
  }
  onProv();
}
function onProv(){
  const p = PROVIDERS.find(x => x.name === document.getElementById('provider').value);
  if (!p) return;
  document.getElementById('model').placeholder = p.default_model || 'default';
  document.getElementById('base_url').placeholder = p.default_base_url || '';
}
function showTab(t){
  for (const x of ['chat','keys','usage','failover','mcp']){
    document.getElementById('pane-'+x).classList.toggle('hidden', x !== t);
    document.getElementById('tab-'+x).classList.toggle('active', x === t);
  }
}
async function send(){
  const body = {
    provider: document.getElementById('provider').value,
    prompt: document.getElementById('prompt').value,
    model: document.getElementById('model').value || null,
    base_url: document.getElementById('base_url').value || null,
    cache: document.getElementById('cache').checked,
  };
  document.getElementById('out').textContent = ''; document.getElementById('stats').textContent = 'Sending…';
  if (document.getElementById('stream').checked){
    const resp = await fetch('/api/stream', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body)});
    const reader = resp.body.getReader(); const dec = new TextDecoder();
    while(true){ const {done, value} = await reader.read(); if (done) break;
      document.getElementById('out').textContent += dec.decode(value); }
    document.getElementById('stats').textContent = 'Done (stream)';
  } else {
    const r = await fetch('/api/chat', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body)});
    const j = await r.json();
    if (j.error){ document.getElementById('out').textContent = 'ERROR: '+j.error; return; }
    document.getElementById('out').textContent = j.content;
    document.getElementById('stats').textContent = `${j.total_tokens} tok · $${j.cost_usd.toFixed(6)} · ${Math.round(j.latency_ms)} ms`;
  }
}
async function setKey(){
  const r = await fetch('/api/keys', {method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({provider: document.getElementById('k_prov').value, value: document.getElementById('k_val').value})});
  document.getElementById('k_val').value = '';
  listKeys();
}
async function listKeys(){
  const r = await fetch('/api/keys'); const j = await r.json();
  document.getElementById('k_list').textContent = 'Stored: ' + (j.stored.join(', ') || '(none)');
}
async function loadUsage(){
  const r = await fetch('/api/usage'); const j = await r.json();
  document.getElementById('u_out').textContent = JSON.stringify(j, null, 2);
}
async function foSend(){
  document.getElementById('fo_out').textContent = 'Calling…';
  const r = await fetch('/api/failover', {method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({providers: document.getElementById('fo_provs').value.split(',').map(x=>x.trim()),
                           prompt: document.getElementById('fo_prompt').value})});
  const j = await r.json();
  document.getElementById('fo_out').textContent = j.error ? 'ERROR '+j.error : `[used ${j.provider}]\\n\\n${j.content}`;
}
async function mcpList(){
  const r = await fetch('/api/mcp/tools?url='+encodeURIComponent(document.getElementById('mcp_url').value));
  document.getElementById('mcp_out').textContent = JSON.stringify(await r.json(), null, 2);
}
async function mcpCall(){
  const r = await fetch('/api/mcp/call', {method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({url: document.getElementById('mcp_url').value,
                          tool: document.getElementById('mcp_tool').value,
                          args: JSON.parse(document.getElementById('mcp_args').value || '{}')})});
  document.getElementById('mcp_out').textContent = JSON.stringify(await r.json(), null, 2);
}
loadProviders();
</script>
</body></html>
"""


def create_app():
    from fastapi import FastAPI, HTTPException, Request
    from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
    from pydantic import BaseModel
    from eazzu.providers.core.registry import PROVIDER_REGISTRY

    app = FastAPI(title="AI API Connector")
    conn = Connector(enable_cache=True)

    class ChatIn(BaseModel):
        provider: str
        prompt: str
        model: Optional[str] = None
        base_url: Optional[str] = None
        cache: bool = False

    class FailoverIn(BaseModel):
        providers: list[str]
        prompt: str
        model: Optional[str] = None

    class KeyIn(BaseModel):
        provider: str
        value: str

    class MCPIn(BaseModel):
        url: str
        tool: Optional[str] = None
        args: dict = {}

    @app.get("/", response_class=HTMLResponse)
    def index():
        return INDEX_HTML

    @app.get("/api/providers")
    def providers():
        out = []
        for name, cls in PROVIDER_REGISTRY.items():
            out.append({
                "name": name,
                "category": getattr(cls, "category", "llm"),
                "default_model": getattr(cls, "default_model", ""),
                "default_base_url": getattr(cls, "default_base_url", ""),
            })
        return sorted(out, key=lambda x: (x["category"], x["name"]))

    @app.post("/api/chat")
    def chat(body: ChatIn):
        try:
            r = conn.chat(
                body.provider, body.prompt, model=body.model,
                base_url=body.base_url, use_cache=body.cache,
            )
            return r.to_dict()
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=500)

    @app.post("/api/stream")
    def stream(body: ChatIn):
        def gen():
            try:
                for chunk in conn.stream(
                    body.provider, body.prompt, model=body.model, base_url=body.base_url
                ):
                    yield chunk
            except Exception as e:
                yield f"\n[ERROR] {e}"
        return StreamingResponse(gen(), media_type="text/plain")

    @app.post("/api/failover")
    def failover(body: FailoverIn):
        try:
            policy = FailoverPolicy(providers=body.providers)
            r = conn.chat_with_failover(policy, body.prompt, model=body.model)
            return r.to_dict()
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=500)

    @app.get("/api/keys")
    def list_keys():
        return {"stored": conn.config.list_stored()}

    @app.post("/api/keys")
    def set_key(body: KeyIn):
        conn.config.set(body.provider, body.value)
        return {"ok": True}

    @app.get("/api/usage")
    def usage():
        return {"summary": conn.tracker.summary(), "recent": conn.tracker.recent(20)}

    @app.get("/api/mcp/tools")
    def mcp_tools(url: str):
        p = conn.get_provider("custom_mcp", base_url=url)
        return {"tools": p.list_tools()}

    @app.post("/api/mcp/call")
    def mcp_call(body: MCPIn):
        p = conn.get_provider("custom_mcp", base_url=body.url)
        if not body.tool:
            tools = p.list_tools()
            body.tool = tools[0]["name"] if tools else None
        if not body.tool:
            raise HTTPException(400, "No tool available")
        return {"result": p.call_tool(body.tool, body.args)}

    return app


def run(host="127.0.0.1", port=8000):
    import uvicorn
    uvicorn.run(create_app(), host=host, port=port)


if __name__ == "__main__":
    run()
