"""
Deriv API Client
Handles WebSocket communication with Deriv API
"""

import asyncio
import json
import logging
from enum import Enum
from typing import Optional, Dict, Any, Callable, List
from dataclasses import dataclass
from datetime import datetime
import traceback

import websockets
from websockets.exceptions import ConnectionClosed, InvalidStatusCode

from ..config import TradingConfig


class ConnectionState(Enum):
    """WebSocket connection states"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    AUTHENTICATED = "authenticated"
    ERROR = "error"


@dataclass
class TickData:
    """Tick data from market"""
    symbol: str
    bid: float
    ask: float
    last: float
    timestamp: datetime
    epoch: int

    @property
    def spread(self) -> float:
        """Calculate spread"""
        return self.ask - self.bid

    @property
    def mid_price(self) -> float:
        """Calculate mid price"""
        return (self.bid + self.ask) / 2


class DerivClient:
    """
    Deriv WebSocket API Client
    Handles all communication with Deriv trading platform
    """

    def __init__(self, config: Optional[TradingConfig] = None):
        self.config = config or TradingConfig()
        self.api_config = self.config.api

        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.state = ConnectionState.DISCONNECTED

        self.logger = logging.getLogger(__name__)

        # Callbacks
        self.tick_callbacks: List[Callable[[TickData], None]] = []
        self.candle_callbacks: List[Callable[[Dict], None]] = []
        self.balance_callbacks: List[Callable[[float], None]] = []
        self.proposal_callbacks: List[Callable[[Dict], None]] = []

        # Data storage
        self.ticks: Dict[str, List[TickData]] = {}
        self.candles: Dict[str, List[Dict]] = {}
        self.balance: Optional[float] = None
        self.proposals: Dict[str, Dict] = {}

        # Subscription tracking
        self.subscriptions: Dict[str, int] = {}

        # Task management
        self._tasks: List[asyncio.Task] = []
        self._running = False
        self._retry_count = 0

    async def connect(self) -> bool:
        """
        Establish WebSocket connection to Deriv API
        Returns True if connection successful
        """
        if self.state in (ConnectionState.CONNECTING, ConnectionState.CONNECTED, ConnectionState.AUTHENTICATED):
            return True

        self.state = ConnectionState.CONNECTING
        self.logger.info(f"Connecting to {self.api_config.api_endpoint}...")

        try:
            # Build connection URL with app_id
            url = f"{self.api_config.api_endpoint}?app_id={self.api_config.app_id}"

            self.ws = await websockets.connect(
                url,
                ping_interval=self.api_config.ping_interval,
                ping_timeout=self.api_config.timeout
            )

            self.state = ConnectionState.CONNECTED
            self._retry_count = 0
            self.logger.info("Connected to Deriv API")

            # Start message handler
            self._task_loop = asyncio.create_task(self._message_loop())

            # Authorize if token provided
            if self.config.token:
                await self.authorize(self.config.token)
            else:
                self.logger.info("Using public API (read-only access)")

            return True

        except Exception as e:
            self.logger.error(f"Connection failed: {e}")
            self.state = ConnectionState.ERROR
            return False

    async def disconnect(self) -> None:
        """Close WebSocket connection"""
        self._running = False
        self.state = ConnectionState.DISCONNECTED

        # Cancel all tasks
        for task in self._tasks:
            task.cancel()

        if self.ws:
            await self.ws.close()
            self.ws = None

        self.logger.info("Disconnected from Deriv API")

    async def _message_loop(self) -> None:
        """Main message handling loop"""
        self._running = True

        while self._running and self.ws:
            try:
                async for message in self.ws:
                    await self._handle_message(message)

            except ConnectionClosed as e:
                self.logger.warning(f"Connection closed: {e.code} - {e.reason}")
                self.state = ConnectionState.DISCONNECTED
                await self._reconnect()

            except Exception as e:
                self.logger.error(f"Message loop error: {e}")
                self.logger.debug(traceback.format_exc())
                break

    async def _handle_message(self, message: str) -> None:
        """Process incoming WebSocket message"""
        try:
            data = json.loads(message)

            # Handle different message types
            msg_type = data.get('msg_type')

            if msg_type == 'tick':
                await self._handle_tick(data)
            elif msg_type == 'ohlc':
                await self._handle_ohlc(data)
            elif msg_type == 'balance':
                self._handle_balance(data)
            elif msg_type == 'proposal':
                self._handle_proposal(data)
            elif msg_type == 'buy':
                self._handle_buy_response(data)
            elif msg_type == 'error':
                self._handle_error(data)
            elif msg_type == 'authorize':
                self._handle_authorize(data)
            elif msg_type == 'ping':
                await self._send({'ping': data.get('ping')})

        except json.JSONDecodeError:
            self.logger.warning(f"Invalid JSON message: {message[:100]}...")
        except Exception as e:
            self.logger.error(f"Error handling message: {e}")

    async def _handle_tick(self, data: Dict) -> None:
        """Handle tick data"""
        if 'tick' not in data:
            return

        tick_data = data['tick']
        symbol = tick_data.get('symbol', 'unknown')

        tick = TickData(
            symbol=symbol,
            bid=tick_data.get('bid', 0),
            ask=tick_data.get('ask', 0),
            last=tick_data.get('last', 0),
            timestamp=datetime.fromtimestamp(tick_data.get('epoch', 0)),
            epoch=tick_data.get('epoch', 0)
        )

        # Store tick
        if symbol not in self.ticks:
            self.ticks[symbol] = []
        self.ticks[symbol].append(tick)

        # Keep last 1000 ticks
        if len(self.ticks[symbol]) > 1000:
            self.ticks[symbol] = self.ticks[symbol][-1000:]

        # Notify callbacks
        for callback in self.tick_callbacks:
            try:
                callback(tick)
            except Exception as e:
                self.logger.error(f"Tick callback error: {e}")

    async def _handle_ohlc(self, data: Dict) -> None:
        """Handle OHLC candle data"""
        if 'ohlc' not in data:
            return

        ohlc_data = data['ohlc']
        symbol = data.get('subscription', {}).get('symbol', 'unknown')

        # Store candle
        if symbol not in self.candles:
            self.candles[symbol] = []
        self.candles[symbol].append(ohlc_data)

        # Keep last 500 candles
        if len(self.candles[symbol]) > 500:
            self.candles[symbol] = self.candles[symbol][-500:]

        # Notify callbacks
        for callback in self.candle_callbacks:
            try:
                callback(ohlc_data)
            except Exception as e:
                self.logger.error(f"Candle callback error: {e}")

    def _handle_balance(self, data: Dict) -> None:
        """Handle balance update"""
        if 'balance' in data:
            self.balance = float(data['balance'].get('balance', 0))

            for callback in self.balance_callbacks:
                try:
                    callback(self.balance)
                except Exception as e:
                    self.logger.error(f"Balance callback error: {e}")

    def _handle_proposal(self, data: Dict) -> None:
        """Handle proposal response"""
        if 'proposal' in data:
            proposal = data['proposal']
            self.proposals[proposal.get('id', '')] = proposal

            for callback in self.proposal_callbacks:
                try:
                    callback(proposal)
                except Exception as e:
                    self.logger.error(f"Proposal callback error: {e}")

    def _handle_buy_response(self, data: Dict) -> None:
        """Handle buy response"""
        self.logger.info(f"Buy response: {data}")

    def _handle_error(self, data: Dict) -> None:
        """Handle error message"""
        error = data.get('error', {})
        code = error.get('code', 'unknown')
        message = error.get('message', 'Unknown error')
        self.logger.error(f"API Error [{code}]: {message}")

    def _handle_authorize(self, data: Dict) -> None:
        """Handle authorization response"""
        if 'authorize' in data:
            self.state = ConnectionState.AUTHENTICATED
            self.logger.info(f"Authenticated as: {data['authorize'].get('loginid', 'unknown')}")
        elif 'error' in data:
            self.logger.warning("Authorization failed - using public API")

    async def _send(self, data: Dict) -> None:
        """Send message to WebSocket"""
        if not self.ws:
            raise ConnectionError("Not connected")

        try:
            await self.ws.send(json.dumps(data))
        except Exception as e:
            self.logger.error(f"Send error: {e}")
            raise

    async def _reconnect(self) -> None:
        """Attempt to reconnect with exponential backoff"""
        if self._retry_count >= self.api_config.max_retries:
            self.logger.error("Max reconnection attempts reached")
            self.state = ConnectionState.ERROR
            return

        self._retry_count += 1
        delay = self.api_config.retry_delay * (2 ** (self._retry_count - 1))

        self.logger.info(f"Reconnecting in {delay}s (attempt {self._retry_count})...")
        await asyncio.sleep(delay)

        if self._running:
            await self.connect()

    async def authorize(self, token: str) -> bool:
        """Authorize with API token"""
        await self._send({'authorize': token})
        self.logger.info("Authorization request sent")
        return True

    async def subscribe_ticks(self, symbol: str) -> int:
        """
        Subscribe to tick updates for a symbol
        Returns subscription ID
        """
        req_id = int(datetime.now().timestamp() * 1000)

        await self._send({
            'tick': symbol,
            'subscribe': 1
        })

        self.subscriptions[symbol] = req_id
        self.logger.debug(f"Subscribed to {symbol} ticks")
        return req_id

    async def subscribe_candles(self, symbol: str, interval: int = 60) -> int:
        """
        Subscribe to candle/OHLC updates
        interval: seconds (1, 5, 15, 30, 60, 120, etc.)
        """
        req_id = int(datetime.now().timestamp() * 1000)

        await self._send({
            'ohlc': {
                'symbol': symbol,
                'interval': interval
            },
            'subscribe': 1
        })

        self.subscriptions[f"{symbol}_{interval}"] = req_id
        self.logger.debug(f"Subscribed to {symbol} {interval}s candles")
        return req_id

    async def get_ticks(self, symbol: str, count: int = 100) -> List[TickData]:
        """Get historical ticks for a symbol"""
        await self._send({
            'ticks_history': symbol,
            'end': 'latest',
            'count': count,
            'style': 'ticks'
        })

        # Wait for response
        await asyncio.sleep(0.5)

        return self.ticks.get(symbol, [])

    async def get_candles(self, symbol: str, interval: int = 60, count: int = 100) -> List[Dict]:
        """Get historical candle data"""
        await self._send({
            ' candles': symbol,
            'interval': interval,
            'count': count
        })

        # Wait for response
        await asyncio.sleep(0.5)

        return self.candles.get(symbol, [])

    async def get_balance(self) -> Optional[float]:
        """Get current account balance"""
        await self._send({'balance': 1})
        await asyncio.sleep(0.2)
        return self.balance

    async def proposal(self, symbol: str, contract_type: str, duration: int,
                      duration_type: str = 's', amount: float = 0.35) -> Optional[Dict]:
        """
        Request a trade proposal
        contract_type: 'CALL' or 'PUT'
        duration: in duration_type units
        duration_type: 's' for seconds, 'm' for minutes, 'h' for hours
        """
        await self._send({
            'proposal': 1,
            'amount': amount,
            'basis': 'stake',
            'contract_type': contract_type,
            'currency': 'USD',
            'duration': duration,
            'duration_unit': duration_type,
            'product_type': 'basic',
            'symbol': symbol
        })

        # Wait for proposal
        await asyncio.sleep(0.3)

        # Return latest proposal
        for pid, proposal in list(self.proposals.items()):
            if proposal.get('symbol') == symbol:
                return proposal

        return None

    async def buy(self, proposal_id: str, price: float = 0.35) -> Optional[Dict]:
        """
        Execute a trade
        Returns buy response with contract details
        """
        await self._send({
            'buy': proposal_id,
            'price': price
        })

        # Wait for response
        for _ in range(10):
            await asyncio.sleep(0.2)

        return None  # Response handled via callback

    async def sell(self, contract_id: str) -> bool:
        """Request to sell a contract"""
        await self._send({
            'sell': contract_id
        })
        return True

    async def get_contracts_for_symbol(self, symbol: str) -> List[Dict]:
        """Get open contracts for a symbol"""
        await self._send({
            'proposal_open_contract': {
                'symbol': symbol,
                'limit': 10
            },
            'subscribe': 1
        })

        await asyncio.sleep(0.3)
        return []

    def get_latest_price(self, symbol: str) -> Optional[float]:
        """Get latest price for a symbol"""
        ticks = self.ticks.get(symbol, [])
        if ticks:
            return ticks[-1].last
        return None

    def get_latest_candle(self, symbol: str, interval: int = 60) -> Optional[Dict]:
        """Get latest candle for a symbol"""
        candles = self.candles.get(f"{symbol}_{interval}", [])
        if candles:
            return candles[-1]
        return None

    def add_tick_callback(self, callback: Callable[[TickData], None]) -> None:
        """Add tick data callback"""
        self.tick_callbacks.append(callback)

    def add_candle_callback(self, callback: Callable[[Dict], None]) -> None:
        """Add candle data callback"""
        self.candle_callbacks.append(callback)

    def add_balance_callback(self, callback: Callable[[float], None]) -> None:
        """Add balance callback"""
        self.balance_callbacks.append(callback)

    @property
    def is_connected(self) -> bool:
        """Check if connected to API"""
        return self.state in (ConnectionState.CONNECTED, ConnectionState.AUTHENTICATED)

    @property
    def is_authenticated(self) -> bool:
        """Check if authenticated"""
        return self.state == ConnectionState.AUTHENTICATED
