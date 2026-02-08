import numpy as np
import os
import sys
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

class VolatilityATR:
    def __init__(self, strategy, initial_risk_per_trade=0.01, profit_risk_percentage=0.1, atr=1.5, lot_size=10_00000, tick_size=0.01, exchange_rate=1.0):
        """
        Initialize the VolatilityATR class.

        :param strategy: The trading strategy object.
        :param initial_risk_per_trade: Initial risk percentage per trade (default: 2%).
        :param profit_risk_percentage: Percentage of profits to add to risk (default: 10%).
        :param atr: Average True Range (ATR) value (default: 1.5).
        :param lot_size: Trade size (e.g., 100,000 for a standard lot in forex).
        :param tick_size: Smallest price movement (e.g., 0.0001 for forex).
        :param exchange_rate: Exchange rate of the quote currency to the account currency.
        """
        self.initial_equity = strategy._broker._cash
        self.initial_risk_per_trade = initial_risk_per_trade
        self.profit_risk_percentage = profit_risk_percentage
        self.closed_trade_profit = 0
        self.atr = atr
        self.lot_size = lot_size
        self.tick_size = tick_size
        self.exchange_rate = exchange_rate

    def get_risk_per_trade(self):
        """
        Calculate the risk per trade based on ATR and dynamically computed point_value.

        :return: Risk per trade as a percentage of equity.
        """
        point_value = self.lot_size * self.tick_size * self.exchange_rate
        point_value_percentage = point_value / self.initial_equity * 100

        base_risk = self.initial_equity * self.initial_risk_per_trade
        profit_risk = self.closed_trade_profit * self.profit_risk_percentage
        total_risk = base_risk + profit_risk

        risk_per_trade = total_risk / (self.atr * point_value_percentage)
        return risk_per_trade

    def update_after_win(self):
        """
        Update logic after a winning trade.
        """
        self.initial_risk_per_trade *= 1.1 

    def update_after_loss(self):
        """
        Update logic after a losing trade.
        """
        self.initial_risk_per_trade *= 0.9
