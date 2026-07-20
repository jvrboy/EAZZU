"""Risk Agent — position sizing, daily loss caps, Kelly criterion.

Converted from infinite-loop-sound's risk-agent.ts. Pure stateful logic with
no I/O; safe to invoke from the EAZZU agent loop.
"""
from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from eazzu.agents.types import AgentConfig, AgentMessage, AgentResult, RiskAssessment

RISK_AGENT_CONFIG = AgentConfig(
    id="risk-agent",
    name="Risk Agent",
    description=(
        "Real-time risk management with Kelly criterion, daily loss caps, "
        "consecutive loss tracking, and position sizing recommendations."
    ),
    enabled=True,
    priority="critical",
    interval_sec=10,
    instruments=["all"],
    timeframes=["all"],
)


class _RiskState:
    daily_pnl: float = 0.0
    daily_start_balance: float = 10000.0
    consecutive_losses: int = 0
    max_consecutive_losses: int = 0
    total_trades_today: int = 0
    wins_today: int = 0
    losses_today: int = 0
    last_reset_date: str = ""

    def reset(self, carry_balance: float) -> None:
        self.daily_pnl = 0.0
        self.daily_start_balance = carry_balance
        self.consecutive_losses = 0
        self.max_consecutive_losses = 0
        self.total_trades_today = 0
        self.wins_today = 0
        self.losses_today = 0
        self.last_reset_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")


_state = _RiskState()
_state.last_reset_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _reset_if_new_day() -> None:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if _state.last_reset_date != today:
        _state.reset(_state.daily_start_balance + _state.daily_pnl)


def record_trade(pnl: float, won: bool) -> None:
    _reset_if_new_day()
    _state.daily_pnl += pnl
    _state.total_trades_today += 1
    if won:
        _state.wins_today += 1
        _state.consecutive_losses = 0
    else:
        _state.losses_today += 1
        _state.consecutive_losses += 1
        _state.max_consecutive_losses = max(
            _state.max_consecutive_losses, _state.consecutive_losses
        )


def run_risk_agent(
    balance: float,
    daily_loss_cap: float = 50.0,
    max_positions: int = 2,
    max_consecutive_losses: int = 5,
    risk_per_trade_pct: float = 1.0,
    open_positions: int = 0,
    available_margin: Optional[float] = None,
    win_rate: float = 0.6,
    avg_win_loss_ratio: float = 1.5,
) -> AgentResult:
    _reset_if_new_day()
    start = time.time()
    messages: List[AgentMessage] = []

    if available_margin is None:
        available_margin = balance

    b = avg_win_loss_ratio
    p = win_rate
    q = 1.0 - p
    kelly = max(0.0, (b * p - q) / b) if b > 0 else 0.0
    safe_kelly = kelly / 2.0

    risk_amount = balance * (risk_per_trade_pct / 100.0)
    kelly_amount = balance * safe_kelly
    recommended = min(risk_amount, kelly_amount)
    max_position_size = max(0.01, recommended)

    should_halt = (
        _state.daily_pnl <= -daily_loss_cap
        or _state.consecutive_losses >= max_consecutive_losses
    )
    halt_reason: Optional[str] = None
    if _state.daily_pnl <= -daily_loss_cap:
        halt_reason = (
            f"Daily loss cap reached (${_state.daily_pnl:.2f} / -${daily_loss_cap})"
        )
        messages.append(
            AgentMessage(
                id=str(uuid.uuid4()),
                agent_id=RISK_AGENT_CONFIG.id,
                type="error",
                timestamp=time.time() * 1000,
                content=halt_reason,
            )
        )
    if _state.consecutive_losses >= max_consecutive_losses:
        halt_reason = (
            f"{_state.consecutive_losses} consecutive losses — halting to prevent tilt"
        )
        messages.append(
            AgentMessage(
                id=str(uuid.uuid4()),
                agent_id=RISK_AGENT_CONFIG.id,
                type="warning",
                timestamp=time.time() * 1000,
                content=halt_reason,
            )
        )

    assessment = RiskAssessment(
        max_position_size=max_position_size,
        daily_loss_limit=daily_loss_cap,
        current_daily_pnl=_state.daily_pnl,
        risk_per_trade=risk_per_trade_pct,
        kelly_fraction=safe_kelly,
        consecutive_losses=_state.consecutive_losses,
        should_halt=should_halt,
        reason=halt_reason,
        position_count=open_positions,
        max_positions=max_positions,
        available_margin=available_margin,
    )

    insights: List[str] = [
        f"Kelly fraction (half): {safe_kelly * 100:.2f}%",
        f"Recommended position size: ${max_position_size:.2f}",
        (
            f"Today: {_state.total_trades_today} trades, WR: "
            f"{(_state.wins_today / _state.total_trades_today * 100):.1f}%"
            if _state.total_trades_today > 0
            else "Today: 0 trades"
        ),
        f"Daily P&L: ${_state.daily_pnl:.2f} (cap: -${daily_loss_cap})",
    ]
    if _state.consecutive_losses > 0:
        insights.append(
            f"Consecutive losses: {_state.consecutive_losses}/{max_consecutive_losses} max"
        )

    return AgentResult(
        agent_id=RISK_AGENT_CONFIG.id,
        status="error" if should_halt else "completed",
        timestamp=time.time() * 1000,
        output={"assessment": assessment.__dict__, "messages": [m.to_dict() for m in messages]},
        insights=insights,
        duration=(time.time() - start) * 1000,
    )


def get_risk_state() -> Dict[str, Any]:
    _reset_if_new_day()
    return {
        "daily_pnl": _state.daily_pnl,
        "daily_start_balance": _state.daily_start_balance,
        "consecutive_losses": _state.consecutive_losses,
        "max_consecutive_losses": _state.max_consecutive_losses,
        "total_trades_today": _state.total_trades_today,
        "wins_today": _state.wins_today,
        "losses_today": _state.losses_today,
    }


def reset_risk_state() -> None:
    _state.reset(_state.daily_start_balance)
