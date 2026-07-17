"""
Custom API + Custom MCP providers.

`custom` — Bring-Your-Own OpenAI-compatible endpoint (base_url + api_key).
`custom_mcp` — Model Context Protocol client (JSON-RPC over HTTP/SSE).
"""
from __future__ import annotations

import json
from typing import Iterator, Optional
import uuid

import requests

from eazzu.providers.core.base_provider import BaseProvider, ChatMessage, ChatResponse
from eazzu.providers.core.http import post_json, stream_sse
from eazzu.providers.core.registry import register_provider
from eazzu.providers.providers.openai_compatible import OpenAICompatibleProvider


@register_provider
class Custom(OpenAICompatibleProvider):
    """
    Custom OpenAI-compatible endpoint.

    Usage:
        c.chat("custom", "Hello", base_url="https://my.llm/v1",
               api_key="…", model="my-model")
    """
    name = "custom"
    default_base_url = "http://localhost:8000/v1"
    default_model = "custom-model"
    category = "llm"


@register_provider
class CustomMCP(BaseProvider):
    """
    Custom MCP (Model Context Protocol) server client.

    Speaks JSON-RPC 2.0 to a user-provided MCP server URL. Supports:
      • tools/list — enumerate server tools
      • tools/call — invoke a tool (default action)
      • prompts/list, resources/list

    Usage:
        c.chat("custom_mcp",
               "search for weather",
               base_url="https://my-mcp.example.com/rpc",
               tool_name="search",           # tool to call
               tool_args={"query": "weather"} # extra args
        )
    """
    name = "custom_mcp"
    default_base_url = "http://localhost:8765/rpc"
    default_model = "mcp"
    category = "mcp"

    def _rpc(self, method: str, params: Optional[dict] = None) -> dict:
        payload = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": method,
            "params": params or {},
        }
        return post_json(self.base_url, self._headers(), payload, self.timeout)

    # -------- Public MCP helpers -------- #
    def list_tools(self) -> list[dict]:
        resp = self._rpc("tools/list")
        return resp.get("result", {}).get("tools", [])

    def list_prompts(self) -> list[dict]:
        resp = self._rpc("prompts/list")
        return resp.get("result", {}).get("prompts", [])

    def list_resources(self) -> list[dict]:
        resp = self._rpc("resources/list")
        return resp.get("result", {}).get("resources", [])

    def call_tool(self, tool_name: str, arguments: dict) -> dict:
        resp = self._rpc("tools/call", {"name": tool_name, "arguments": arguments})
        return resp.get("result", {})

    # -------- BaseProvider hooks -------- #
    def _chat_impl(self, messages, model, **kwargs) -> ChatResponse:
        query = "\n".join(m.content for m in messages if m.role != "system")
        tool_name = kwargs.pop("tool_name", None)
        tool_args = kwargs.pop("tool_args", {}) or {}
        if not tool_name:
            # Fallback: introspect and pick the first tool
            tools = self.list_tools()
            if not tools:
                raise RuntimeError("MCP server exposes no tools.")
            tool_name = tools[0]["name"]
            tool_args = tool_args or {"query": query}
        else:
            tool_args = {**tool_args, "query": query} if "query" not in tool_args else tool_args

        result = self.call_tool(tool_name, tool_args)
        # MCP tool call result: {"content": [{"type":"text","text":"..."}], "isError": bool}
        content = ""
        for block in result.get("content", []):
            if block.get("type") == "text":
                content += block.get("text", "")
        if not content:
            content = json.dumps(result, ensure_ascii=False)[:5000]
        return ChatResponse(
            provider=self.name, model=f"mcp:{tool_name}", content=content, raw=result,
        )
