import os
import sys
import math
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)
from backtester.helpers.indicators import calculate_atr
from backtester.trade_management.tp_sl.atr_tm import ATR_RR_TradeManagement

class TradeLevelsCalculator:
    def __init__(self, strategy, n_tp_levels, n_sl_levels, atr_multiplier=2, atr_period=14, risk_reward_ratio=2):
        """
        Initialize the TradeLevelsCalculator with separate TP and SL level counts.

        Parameters:
            strategy: The trading strategy instance.
            n_tp_levels (int): Number of take profit levels to generate.
            n_sl_levels (int): Number of stop loss levels to generate.
        """
        self.strategy = strategy
        self.n_tp_levels = n_tp_levels
        self.n_sl_levels = n_sl_levels
        self.atr_multiplier = atr_multiplier
        self.atr_period = atr_period
        self.risk_reward_ratio = risk_reward_ratio
        
    def init(self): 
        """Optional initialization method for TradeLevelsCalculator."""
        pass

    def calculate_levels(self, n_tp_levels, n_sl_levels, direction):
        """
        Calculate stop loss (SL) and take profit (TP) levels based on the given direction and strategy.

        Parameters:
            n_tp_levels (int): Number of take profit levels to generate.
            n_sl_levels (int): Number of stop loss levels to generate.
            direction (str): The trade direction ('buy' or 'sell').

        Returns:
            tuple: A tuple containing lists of SL levels and TP levels.
        """
        atr_tm = ATR_RR_TradeManagement(self.strategy,self.risk_reward_ratio, self.atr_multiplier, self.atr_period)
        final_sl, final_tp = atr_tm.calculate_tp_sl(direction)

        entry_price = self.strategy.data.df['Close'].iloc[-1]

        if direction.lower() == 'buy':
            # Calculate distances for TP and SL levels
            tp_distance = final_tp - entry_price
            sl_distance = entry_price - final_sl

            # Generate TP levels
            tp_levels = [
                round(entry_price + (i * (tp_distance / n_tp_levels)), 5)
                for i in range(1, n_tp_levels + 1)
            ]

            # Generate SL levels
            sl_levels = [
                round(entry_price - (i * (sl_distance / n_sl_levels)), 5)
                for i in range(1, n_sl_levels + 1)
            ]

        elif direction.lower() == 'sell':
            # Calculate distances for TP and SL levels
            tp_distance = entry_price - final_tp
            sl_distance = final_sl - entry_price

            # Generate TP levels
            tp_levels = [
                round(entry_price - (i * (tp_distance / n_tp_levels)), 5)
                for i in range(1, n_tp_levels + 1)
            ]

            # Generate SL levels
            sl_levels = [
                round(entry_price + (i * (sl_distance / n_sl_levels)), 5)
                for i in range(1, n_sl_levels + 1)
            ]

        else:
            raise ValueError(f"Invalid direction: {direction}. Must be 'buy' or 'sell'.")

        return sl_levels, tp_levels