"""
Risk Calculator
Position sizing and risk management calculations
"""

from typing import Dict, Any, Optional


class RiskCalculator:
    """
    Risk Calculator
    Handles position sizing and risk management calculations
    """

    def __init__(self, balance: float = 1000.0):
        self.balance = balance

    def calculate_position_size(self,
                               risk_percent: float,
                               entry_price: float,
                               stop_loss_price: float,
                               pip_size: float = 0.01) -> float:
        """
        Calculate position size based on risk parameters

        Args:
            risk_percent: Risk percentage of account (e.g., 1 for 1%)
            entry_price: Entry price of trade
            stop_loss_price: Stop loss price
            pip_size: Size of one pip

        Returns:
            Position size in lots
        """
        risk_amount = self.balance * (risk_percent / 100)

        # Calculate stop loss in pips
        sl_pips = abs(entry_price - stop_loss_price) / pip_size

        if sl_pips == 0:
            return 0

        # Calculate position size
        position_size = risk_amount / (sl_pips * pip_size)

        return round(position_size, 2)

    def calculate_stop_loss(self,
                           entry_price: float,
                           direction: str,
                           atr: float = None,
                           atr_multiplier: float = 1.5,
                           fixed_pips: float = None) -> float:
        """
        Calculate stop loss price

        Args:
            entry_price: Entry price
            direction: 'CALL' or 'PUT'
            atr: Average True Range value
            atr_multiplier: ATR multiplier for stop loss
            fixed_pips: Fixed stop loss in pips

        Returns:
            Stop loss price
        """
        if fixed_pips:
            pip_value = fixed_pips * 0.01
        elif atr:
            pip_value = atr * atr_multiplier
        else:
            pip_value = 10 * 0.01  # Default 10 pips

        if direction == 'CALL':
            return entry_price - pip_value
        else:
            return entry_price + pip_value

    def calculate_take_profit(self,
                             entry_price: float,
                             direction: str,
                             risk_reward_ratio: float = 2.0,
                             stop_loss_price: float = None) -> float:
        """
        Calculate take profit price

        Args:
            entry_price: Entry price
            direction: 'CALL' or 'PUT'
            risk_reward_ratio: Ratio of profit to risk
            stop_loss_price: Stop loss price (optional)

        Returns:
            Take profit price
        """
        if stop_loss_price:
            distance = abs(entry_price - stop_loss_price)
            profit_distance = distance * risk_reward_ratio
        else:
            profit_distance = 0.2  # Default 20 pips

        if direction == 'CALL':
            return entry_price + profit_distance
        else:
            return entry_price - profit_distance

    def calculate_risk_reward(self,
                            entry_price: float,
                            stop_loss_price: float,
                            take_profit_price: float,
                            direction: str) -> float:
        """
        Calculate risk-reward ratio

        Args:
            entry_price: Entry price
            stop_loss_price: Stop loss price
            take_profit_price: Take profit price
            direction: 'CALL' or 'PUT'

        Returns:
            Risk-reward ratio
        """
        risk = abs(entry_price - stop_loss_price)

        if direction == 'CALL':
            reward = take_profit_price - entry_price
        else:
            reward = entry_price - take_profit_price

        if risk == 0:
            return 0

        return reward / risk

    def calculate_max_daily_loss(self,
                                daily_loss_limit: float = 100.0) -> bool:
        """
        Check if daily loss limit has been reached

        Args:
            daily_loss_limit: Maximum allowed daily loss

        Returns:
            True if limit reached (should stop trading)
        """
        # This would need to track daily P&L
        # Placeholder implementation
        return False

    def get_risk_level(self, risk_percent: float) -> str:
        """
        Get risk level description

        Args:
            risk_percent: Risk percentage

        Returns:
            Risk level string
        """
        if risk_percent <= 0.5:
            return "Very Low"
        elif risk_percent <= 1.0:
            return "Low"
        elif risk_percent <= 2.0:
            return "Medium"
        elif risk_percent <= 5.0:
            return "High"
        else:
            return "Very High"

    def suggest_position_size(self,
                            risk_percent: float = 1.0,
                            confidence: float = 1.0) -> float:
        """
        Suggest position size based on confidence

        Args:
            risk_percent: Base risk percentage
            confidence: Signal confidence (0.0 to 1.0)

        Returns:
            Suggested position size
        """
        # Reduce position size for lower confidence
        adjusted_risk = risk_percent * confidence

        # Calculate position size with minimum risk
        min_risk = 0.1  # Minimum 0.1% risk
        final_risk = max(adjusted_risk, min_risk)

        return self.balance * (final_risk / 100)
