"""Deriv public API client — real-time forex / synthetic indices data.

Uses Deriv's default public application (app_id 1089) over the WebSocket API
at wss://ws.derivws.com/ws and the REST endpoint at https://api.derivws.com.
No API token is required for market-data calls (ticks, candles, symbols,
proposal, active symbols). Account / trading calls require a token the user
supplies out-of-band; this client never places orders.

Pure-stdlib: uses `urllib` for REST and an optional `websocket-client` for
streaming. When `websocket-client` is not installed, streaming falls back to
a short-lived REST poll loop so the client still works on iSH/Alpine.
"""
from __future__ import annotations

import json
import threading
import time
from typing import Any, Callable, Dict, List, Optional
from urllib.parse import urlencode
from urllib.request import Request, urlopen

DERIV_APP_ID = 1089
DERIV_REST = f"https://api.derivws.com/websockets/v3?app_id={DERIV_APP_ID}"
DERIV_WS = f"wss://ws.derivws.com/websockets/v3?app_id={DERIV_APP_ID}"
DERIV_REST_ALT = f"https://api.derivws.com?app_id={DERIV_APP_ID}"

UA = "eazzu/1.1 (+https://github.com/jvrboy/EAZZU)"


def _error(code: str, exc: Exception) -> Dict[str, Any]:
    return {"error": code, "message": str(exc)}


def _rest_request(payload: Dict[str, Any], timeout: int = 20) -> Dict[str, Any]:
    url = DERIV_REST_ALT + "&" + urlencode({"req": json.dumps(payload)})
    req = Request(url, headers={"User-Agent": UA})
    with urlopen(req, timeout=timeout) as r:
        body = r.read(500_000).decode("utf-8", errors="replace")
    return json.loads(body)


def ping() -> Dict[str, Any]:
    return _rest_request({"ping": 1})


def get_active_symbols() -> Dict[str, Any]:
    return _rest_request({"active_symbols": "brief", "product_type": "basic"})


def get_tick(symbol: str) -> Dict[str, Any]:
    return _rest_request({"ticks": symbol})


def get_ticks_history(symbol: str, count: int = 100, style: str = "ticks",
                      end: str = "latest") -> Dict[str, Any]:
    return _rest_request({"ticks_history": symbol, "end": end, "count": count, "style": style})


def get_candles(symbol: str, count: int = 100, granularity: int = 60,
                end: str = "latest") -> Dict[str, Any]:
    return _rest_request({"ticks_history": symbol, "end": end, "count": count,
                          "style": "candles", "granularity": granularity})


def get_candles_by_time(symbol: str, start: int, end: int, granularity: int = 60) -> Dict[str, Any]:
    return _rest_request({"ticks_history": symbol, "start": start, "end": end,
                          "style": "candles", "granularity": granularity})


def get_proposal(contract_type: str = "CALL", symbol: str = "R_100",
                 amount: float = 10, basis: str = "stake", currency: str = "USD",
                 duration: int = 5, duration_unit: str = "m") -> Dict[str, Any]:
    return _rest_request({"proposal": 1, "amount": amount, "basis": basis,
                          "contract_type": contract_type, "currency": currency,
                          "duration": duration, "duration_unit": duration_unit, "symbol": symbol})


def get_website_status() -> Dict[str, Any]:
    return _rest_request({"website_status": 1})


def get_time() -> Dict[str, Any]:
    return _rest_request({"time": 1})


def get_exchange_rates(base: str = "USD") -> Dict[str, Any]:
    return _rest_request({"exchange_rates": 1, "base_currency": base})


def get_residence_list() -> Dict[str, Any]:
    return _rest_request({"residence_list": 1})


def get_payout_currencies() -> Dict[str, Any]:
    return _rest_request({"payout_currencies": 1})


def get_countries() -> Dict[str, Any]:
    return _rest_request({"country_listing": 1})


def get_landing_company_details(residence: str = "id") -> Dict[str, Any]:
    return _rest_request({"landing_company_details": residence})


class DerivStream:
    """Lightweight Deriv tick/candle stream."""

    def __init__(self, symbol: str, style: str = "ticks", granularity: int = 60):
        self.symbol = symbol
        self.style = style
        self.granularity = granularity
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._ws = None
        self.messages: List[Dict[str, Any]] = []
        self.callback: Optional[Callable[[Dict[str, Any]], None]] = None

    def subscribe(self, callback: Optional[Callable[[Dict[str, Any]], None]] = None) -> Dict[str, Any]:
        self.callback = callback
        try:
            import websocket  # type: ignore
            self._thread = threading.Thread(target=self._ws_loop, daemon=True)
            self._thread.start()
            return {"streaming": True, "transport": "websocket", "symbol": self.symbol}
        except ImportError:
            self._thread = threading.Thread(target=self._poll_loop, daemon=True)
            self._thread.start()
            return {"streaming": True, "transport": "rest-poll", "symbol": self.symbol}

    def _ws_loop(self):
        try:
            import websocket  # type: ignore
            self._ws = websocket.create_connection(DERIV_WS, timeout=10)
            req = {"ticks": self.symbol} if self.style == "ticks" else {
                "ticks_history": self.symbol, "end": "latest", "count": 1,
                "style": "candles", "granularity": self.granularity, "subscribe": 1}
            self._ws.send(json.dumps(req))
            while not self._stop.is_set():
                try:
                    msg = self._ws.recv()
                    if not msg:
                        continue
                    data = json.loads(msg)
                    self.messages.append(data)
                    if self.callback:
                        self.callback(data)
                except Exception:
                    break
        except Exception:
            self._poll_loop()

    def _poll_loop(self):
        last_epoch = 0
        while not self._stop.is_set():
            try:
                if self.style == "ticks":
                    r = get_tick(self.symbol)
                    if "tick" in r:
                        data = r["tick"]
                        if data.get("epoch", 0) != last_epoch:
                            last_epoch = data.get("epoch", 0)
                            self.messages.append({"tick": data})
                            if self.callback:
                                self.callback({"tick": data})
                else:
                    r = get_candles(self.symbol, count=1, granularity=self.granularity)
                    if "candles" in r and r["candles"]:
                        c = r["candles"][-1]
                        if c.get("epoch", 0) != last_epoch:
                            last_epoch = c.get("epoch", 0)
                            self.messages.append({"candle": c})
                            if self.callback:
                                self.callback({"candle": c})
            except Exception:
                pass
            for _ in range(10):
                if self._stop.is_set():
                    return
                time.sleep(0.5)

    def stop(self) -> Dict[str, Any]:
        self._stop.set()
        if self._ws:
            try:
                self._ws.close()
            except Exception:
                pass
        if self._thread:
            self._thread.join(timeout=2)
        return {"stopped": True, "messages": len(self.messages)}

    def latest(self) -> Optional[Dict[str, Any]]:
        return self.messages[-1] if self.messages else None


def collect_ticks(symbol: str, count: int = 10, timeout: float = 30.0) -> Dict[str, Any]:
    collected: List[Dict[str, Any]] = []
    done = threading.Event()

    def on_msg(msg):
        if "tick" in msg:
            collected.append(msg["tick"])
            if len(collected) >= count:
                done.set()

    stream = DerivStream(symbol, style="ticks")
    stream.subscribe(on_msg)
    done.wait(timeout=timeout)
    stream.stop()
    return {"symbol": symbol, "count": len(collected), "ticks": collected}


def collect_candles(symbol: str, count: int = 10, granularity: int = 60,
                    timeout: float = 60.0) -> Dict[str, Any]:
    collected: List[Dict[str, Any]] = []
    done = threading.Event()

    def on_msg(msg):
        if "candle" in msg:
            collected.append(msg["candle"])
            if len(collected) >= count:
                done.set()

    stream = DerivStream(symbol, style="candles", granularity=granularity)
    stream.subscribe(on_msg)
    done.wait(timeout=timeout)
    stream.stop()
    return {"symbol": symbol, "granularity": granularity, "count": len(collected), "candles": collected}
