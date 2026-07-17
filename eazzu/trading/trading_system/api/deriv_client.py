"""
Deriv API Client
================
WebSocket client for Deriv API - handles all market data and trading operations.
"""

import asyncio
import json
import websockets
import requests
from typing import Optional, Dict, List, Callable, Any, Coroutine
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import numpy as np
import threading
import queue
import time
import uuid

from config.settings import APIConfig, get_config
from core.logger import api_logger, system_logger
from core.types import OHLCV, MarketData


class DerivWebSocketClient:
    """
    Deriv WebSocket API Client.
    Handles real-time data streaming and API communication.
    """
    
    def __init__(self, app_id: int = None):
        self.config: APIConfig = get_config("api")
        self.app_id = app_id or self.config.APP_ID
        self.endpoint = f"{self.config.ENDPOINT}?app_id={self.app_id}"
        
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.connected = False
        self.subscriptions: Dict[str, Any] = {}
        self.callbacks: Dict[str, List[Callable]] = {}
        self.req_id = 1
        self.responses: Dict[int, asyncio.Future] = {}
        
        self._receive_task: Optional[asyncio.Task] = None
        self._ping_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()
        self._reconnect_count = 0
        
        api_logger.info(f"Deriv client initialized | App ID: {self.app_id}")
    
    async def connect(self) -> bool:
        """Establish WebSocket connection."""
        try:
            self.ws = await websockets.connect(
                self.endpoint,
                ping_interval=self.config.PING_INTERVAL,
                ping_timeout=10,
                close_timeout=5
            )
            self.connected = True
            self._reconnect_count = 0
            
            # Start background tasks
            self._receive_task = asyncio.create_task(self._receive_loop())
            self._ping_task = asyncio.create_task(self._ping_loop())
            
            api_logger.info("WebSocket connected successfully")
            return True
            
        except Exception as e:
            api_logger.error(f"Connection failed: {e}")
            return False
    
    async def disconnect(self):
        """Close WebSocket connection."""
        self.connected = False
        
        if self._ping_task:
            self._ping_task.cancel()
        if self._receive_task:
            self._receive_task.cancel()
        
        if self.ws:
            await self.ws.close()
            
        api_logger.info("WebSocket disconnected")
    
    async def _receive_loop(self):
        """Background task to receive and process messages."""
        while self.connected:
            try:
                if self.ws:
                    message = await asyncio.wait_for(self.ws.recv(), timeout=60)
                    data = json.loads(message)
                    await self._handle_message(data)
            except asyncio.TimeoutError:
                continue
            except websockets.exceptions.ConnectionClosed:
                api_logger.warning("Connection closed, attempting reconnect")
                await self._reconnect()
            except Exception as e:
                api_logger.error(f"Receive error: {e}")
                await asyncio.sleep(1)
    
    async def _ping_loop(self):
        """Keep connection alive with periodic pings."""
        while self.connected:
            try:
                await self.send({"ping": 1})
                await asyncio.sleep(self.config.PING_INTERVAL)
            except Exception as e:
                api_logger.debug(f"Ping error: {e}")
                await asyncio.sleep(5)
    
    async def _reconnect(self):
        """Attempt to reconnect."""
        if self._reconnect_count >= self.config.RECONNECT_ATTEMPTS:
            api_logger.error("Max reconnection attempts reached")
            self.connected = False
            return
        
        self._reconnect_count += 1
        delay = self.config.RECONNECT_DELAY * self._reconnect_count
        api_logger.info(f"Reconnecting in {delay}s (attempt {self._reconnect_count})")
        
        await asyncio.sleep(delay)
        await self.connect()
        
        # Resubscribe to active subscriptions
        for sub_id, sub_data in self.subscriptions.items():
            await self.send(sub_data["request"])
    
    async def send(self, request: Dict) -> Dict:
        """Send a request and wait for response."""
        if not self.connected or not self.ws:
            raise ConnectionError("Not connected to Deriv API")
        
        async with self._lock:
            req_id = self.req_id
            self.req_id += 1
            request["req_id"] = req_id
        
        future = asyncio.get_event_loop().create_future()
        self.responses[req_id] = future
        
        try:
            await self.ws.send(json.dumps(request))
            return await asyncio.wait_for(future, timeout=self.config.TIMEOUT)
        except asyncio.TimeoutError:
            api_logger.error(f"Request {req_id} timed out")
            raise
        finally:
            self.responses.pop(req_id, None)
    
    async def _handle_message(self, data: Dict):
        """Handle incoming WebSocket messages."""
        req_id = data.get("req_id")
        
        # Resolve pending requests
        if req_id and req_id in self.responses:
            if not self.responses[req_id].done():
                self.responses[req_id].set_result(data)
        
        # Handle subscriptions (ticks, candles)
        if "tick" in data:
            await self._handle_tick(data["tick"])
        elif "candles" in data:
            await self._handle_candles(data)
        elif "ohlc" in data:
            await self._handle_ohlc(data["ohlc"])
        
        # Trigger callbacks
        msg_type = self._get_message_type(data)
        if msg_type in self.callbacks:
            for callback in self.callbacks[msg_type]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        asyncio.create_task(callback(data))
                    else:
                        callback(data)
                except Exception as e:
                    api_logger.error(f"Callback error: {e}")
    
    def _get_message_type(self, data: Dict) -> str:
        """Determine message type from data."""
        for key in ["tick", "candles", "ohlc", "history", "proposal", "buy", "sell"]:
            if key in data:
                return key
        return "unknown"
    
    async def _handle_tick(self, tick_data: Dict):
        """Process tick data."""
        symbol = tick_data.get("symbol")
        price = tick_data.get("quote", 0)
        epoch = tick_data.get("epoch", int(time.time()))
        
        # Store latest tick
        self.subscriptions[symbol] = {
            "type": "tick",
            "last_price": price,
            "timestamp": datetime.fromtimestamp(epoch),
            "data": tick_data
        }
    
    async def _handle_candles(self, data: Dict):
        """Process candle data."""
        pass  # Handled in specific methods
    
    async def _handle_ohlc(self, ohlc_data: Dict):
        """Process OHLC stream data."""
        symbol = ohlc_data.get("symbol", "")
        if symbol not in self.callbacks:
            return
    
    def register_callback(self, event_type: str, callback: Callable):
        """Register a callback for event type."""
        if event_type not in self.callbacks:
            self.callbacks[event_type] = []
        self.callbacks[event_type].append(callback)
    
    # === API Methods ===
    
    async def ping(self) -> bool:
        """Test connection."""
        try:
            response = await self.send({"ping": 1})
            return "pong" in response
        except Exception as e:
            api_logger.error(f"Ping failed: {e}")
            return False
    
    async def get_active_symbols(self, symbol_type: str = "forex") -> List[Dict]:
        """Get list of active trading symbols."""
        response = await self.send({
            "active_symbols": symbol_type,
            "product_type": "basic"
        })
        return response.get("active_symbols", [])
    
    async def get_tick_history(
        self,
        symbol: str,
        count: int = 5000,
        end: str = "latest",
        style: str = "candles",
        granularity: int = 60
    ) -> List[OHLCV]:
        """
        Get historical tick/candle data.
        
        Args:
            symbol: Asset symbol (e.g., 'frxEURUSD', 'cryBTCUSD', 'R_100')
            count: Number of data points
            end: End time or 'latest'
            style: 'ticks' or 'candles'
            granularity: Candle granularity in seconds
        """
        request = {
            "ticks_history": symbol,
            "adjust_start_time": 1,
            "count": min(count, 5000),
            "end": end,
            "style": style,
        }
        
        if style == "candles":
            request["granularity"] = granularity
        
        if end == "latest":
            request["end"] = "latest"
            request["subscribe"] = 0
        
        api_logger.debug(f"Fetching {count} candles for {symbol} ({granularity}s)")
        
        try:
            response = await self.send(request)
            
            if "error" in response:
                api_logger.error(f"API error: {response['error']}")
                return []
            
            candles = []
            if style == "candles" and "candles" in response:
                for c in response["candles"]:
                    candles.append(OHLCV(
                        timestamp=datetime.fromtimestamp(c["epoch"]),
                        open=float(c["open"]),
                        high=float(c["high"]),
                        low=float(c["low"]),
                        close=float(c["close"]),
                        volume=float(c.get("volume", 0))
                    ))
            elif style == "ticks" and "history" in response:
                prices = response["history"]["prices"]
                times = response["history"]["times"]
                for i in range(len(prices)):
                    candles.append(OHLCV(
                        timestamp=datetime.fromtimestamp(times[i]),
                        open=float(prices[i]),
                        high=float(prices[i]),
                        low=float(prices[i]),
                        close=float(prices[i]),
                        volume=0
                    ))
            
            api_logger.info(f"Retrieved {len(candles)} candles for {symbol}")
            return candles
            
        except Exception as e:
            api_logger.error(f"Failed to get tick history: {e}")
            return []
    
    async def subscribe_ticks(self, symbol: str) -> str:
        """Subscribe to real-time tick stream."""
        request = {
            "ticks": symbol,
            "subscribe": 1
        }
        
        response = await self.send(request)
        
        if "error" in response:
            api_logger.error(f"Subscribe error: {response['error']}")
            return ""
        
        sub_id = response.get("subscription", {}).get("id", str(uuid.uuid4()))
        self.subscriptions[sub_id] = {
            "type": "ticks",
            "symbol": symbol,
            "request": request
        }
        
        api_logger.info(f"Subscribed to ticks: {symbol}")
        return sub_id
    
    async def subscribe_candles(self, symbol: str, granularity: int = 60) -> str:
        """Subscribe to real-time candle stream."""
        request = {
            "ticks_history": symbol,
            "end": "latest",
            "granularity": granularity,
            "style": "candles",
            "subscribe": 1,
            "count": 1
        }
        
        response = await self.send(request)
        
        if "error" in response:
            api_logger.error(f"Candle subscribe error: {response['error']}")
            return ""
        
        sub_id = response.get("subscription", {}).get("id", str(uuid.uuid4()))
        self.subscriptions[sub_id] = {
            "type": "candles",
            "symbol": symbol,
            "granularity": granularity,
            "request": request
        }
        
        api_logger.info(f"Subscribed to candles: {symbol} ({granularity}s)")
        return sub_id
    
    async def forget_subscription(self, subscription_id: str) -> bool:
        """Unsubscribe from a stream."""
        response = await self.send({
            "forget": subscription_id
        })
        
        success = "error" not in response
        if success:
            self.subscriptions.pop(subscription_id, None)
            api_logger.info(f"Unsubscribed: {subscription_id}")
        
        return success
    
    async def forget_all(self, stream_type: str = "ticks") -> bool:
        """Unsubscribe from all streams of a type."""
        response = await self.send({
            "forget_all": stream_type
        })
        
        success = "error" not in response
        if success:
            # Clean up subscriptions
            to_remove = [
                k for k, v in self.subscriptions.items()
                if v.get("type") == stream_type
            ]
            for k in to_remove:
                self.subscriptions.pop(k, None)
            
            api_logger.info(f"Unsubscribed all {stream_type}")
        
        return success
    
    async def get_trading_times(self, date: str = None) -> Dict:
        """Get trading times for all assets."""
        request = {"trading_times": date or "today"}
        response = await self.send(request)
        return response.get("trading_times", {})
    
    async def get_asset_index(self) -> List:
        """Get asset index with contract details."""
        response = await self.send({"asset_index": 1})
        return response.get("asset_index", [])
    
    async def get_exchange_rates(self, base: str = "USD") -> Dict:
        """Get exchange rates."""
        response = await self.send({
            "exchange_rates": 1,
            "base_currency": base
        })
        return response.get("exchange_rates", {})


class DataManager:
    """
    Manages market data across multiple symbols and timeframes.
    Provides caching, batch retrieval, and data synchronization.
    """
    
    def __init__(self, client: DerivWebSocketClient):
        self.client = client
        self.cache: Dict[str, MarketData] = {}
        self._lock = asyncio.Lock()
        self._update_callbacks: List[Callable] = []
        
        api_logger.info("DataManager initialized")
    
    def _get_cache_key(self, symbol: str, timeframe: str) -> str:
        """Generate cache key."""
        return f"{symbol}_{timeframe}"
    
    async def fetch_historical_data(
        self,
        symbol: str,
        timeframe: str,
        count: int = 5000
    ) -> Optional[MarketData]:
        """
        Fetch historical OHLCV data for a symbol and timeframe.
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe string (1m, 5m, 15m, 30m, 1h, 4h, 1d)
            count: Number of candles to fetch
        """
        granularity_map = {
            "1m": 60, "5m": 300, "15m": 900, "30m": 1800,
            "1h": 3600, "4h": 14400, "1d": 86400
        }
        
        granularity = granularity_map.get(timeframe, 60)
        
        # Check cache first
        cache_key = self._get_cache_key(symbol, timeframe)
        
        async with self._lock:
            if cache_key in self.cache:
                cached = self.cache[cache_key]
                if len(cached.candles) >= count:
                    api_logger.debug(f"Using cached data for {symbol} {timeframe}")
                    return cached
        
        # Fetch from API (may need multiple requests for large counts)
        all_candles = []
        remaining = count
        last_epoch = "latest"
        
        while remaining > 0:
            batch_size = min(remaining, 5000)
            
            candles = await self.client.get_tick_history(
                symbol=symbol,
                count=batch_size,
                end=last_epoch,
                style="candles",
                granularity=granularity
            )
            
            if not candles:
                break
            
            all_candles.extend(candles)
            remaining -= len(candles)
            
            if len(candles) < batch_size:
                break
            
            # Get epoch of oldest candle for next batch
            last_epoch = int(candles[0].timestamp.timestamp())
        
        if not all_candles:
            api_logger.warning(f"No data retrieved for {symbol} {timeframe}")
            return None
        
        # Sort by timestamp
        all_candles.sort(key=lambda x: x.timestamp)
        
        # Create MarketData object
        asset_class = self._detect_asset_class(symbol)
        
        market_data = MarketData(
            symbol=symbol,
            asset_class=asset_class,
            timeframe=timeframe,
            candles=all_candles,
            current_price=all_candles[-1].close if all_candles else 0.0,
            timestamp=datetime.now()
        )
        
        # Cache the data
        async with self._lock:
            self.cache[cache_key] = market_data
        
        api_logger.info(
            f"Fetched {len(all_candles)} candles for {symbol} ({timeframe})"
        )
        
        return market_data
    
    async def fetch_multi_timeframe(
        self,
        symbol: str,
        timeframes: List[str]
    ) -> Dict[str, MarketData]:
        """Fetch data for multiple timeframes simultaneously."""
        tasks = [
            self.fetch_historical_data(symbol, tf)
            for tf in timeframes
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        data = {}
        for tf, result in zip(timeframes, results):
            if isinstance(result, MarketData):
                data[tf] = result
            else:
                api_logger.warning(f"Failed to fetch {symbol} {tf}: {result}")
        
        return data
    
    async def fetch_multi_asset(
        self,
        symbols: List[str],
        timeframe: str
    ) -> Dict[str, MarketData]:
        """Fetch data for multiple assets simultaneously."""
        tasks = [
            self.fetch_historical_data(sym, timeframe)
            for sym in symbols
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        data = {}
        for sym, result in zip(symbols, results):
            if isinstance(result, MarketData):
                data[sym] = result
        
        return data
    
    def _detect_asset_class(self, symbol: str) -> str:
        """Detect asset class from symbol prefix."""
        if symbol.startswith("frx"):
            return "forex"
        elif symbol.startswith("cry"):
            return "crypto"
        elif symbol.startswith(("R_", "1HZ", "JD", "RDB", "WLD", "BOOM", "CRASH", "STEP")):
            return "synthetic"
        elif symbol.startswith("OTC_"):
            if symbol in ["OTC_AUUSD", "OTC_AGUSD", "OTC_WTI", "OTC_BRENT", "OTC_COPPER", "OTC_NGUSD"]:
                return "commodity"
            else:
                return "index"
        return "unknown"
    
    def get_cached_data(self, symbol: str, timeframe: str) -> Optional[MarketData]:
        """Get cached market data."""
        cache_key = self._get_cache_key(symbol, timeframe)
        return self.cache.get(cache_key)
    
    def clear_cache(self):
        """Clear all cached data."""
        self.cache.clear()
        api_logger.info("Cache cleared")
    
    def register_update_callback(self, callback: Callable):
        """Register callback for data updates."""
        self._update_callbacks.append(callback)


class AsyncDerivExecutor:
    """Helper to run async Deriv operations from sync code."""
    
    def __init__(self, app_id: int = None):
        self.client = DerivWebSocketClient(app_id)
        self.data_manager = DataManager(self.client)
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
    
    def start(self):
        """Start the async event loop in a background thread."""
        def run_loop():
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            self._loop.run_forever()
        
        self._thread = threading.Thread(target=run_loop, daemon=True)
        self._thread.start()
        
        # Connect to API
        future = asyncio.run_coroutine_threadsafe(
            self.client.connect(), self._loop
        )
        return future.result(timeout=30)
    
    def stop(self):
        """Stop the event loop."""
        if self._loop:
            future = asyncio.run_coroutine_threadsafe(
                self.client.disconnect(), self._loop
            )
            future.result(timeout=10)
            self._loop.call_soon_threadsafe(self._loop.stop)
    
    def fetch_data(
        self,
        symbol: str,
        timeframe: str,
        count: int = 5000
    ) -> Optional[MarketData]:
        """Fetch market data (sync wrapper)."""
        if not self._loop:
            raise RuntimeError("Executor not started")
        
        future = asyncio.run_coroutine_threadsafe(
            self.data_manager.fetch_historical_data(symbol, timeframe, count),
            self._loop
        )
        return future.result(timeout=120)
    
    def fetch_multi_timeframe(
        self,
        symbol: str,
        timeframes: List[str]
    ) -> Dict[str, MarketData]:
        """Fetch multi-timeframe data (sync wrapper)."""
        if not self._loop:
            raise RuntimeError("Executor not started")
        
        future = asyncio.run_coroutine_threadsafe(
            self.data_manager.fetch_multi_timeframe(symbol, timeframes),
            self._loop
        )
        return future.result(timeout=300)
