import os
import sys
import math
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)
from backtester.trade_management.tp_sl.fixed_tm import FixedTP_SL_TradeManagement

class TradeLevelsCalculator:
    def __init__(self, strategy, n_tp_levels, n_sl_levels, sl_pct, tp_pct):
        """
        Initialize the TradeLevelsCalculator with separate TP and SL level counts
        and fixed TP/SL percentages.
        Parameters:
            strategy: The trading strategy instance.
            n_tp_levels (int): Number of take profit levels to generate.
            n_sl_levels (int): Number of stop loss levels to generate.
            sl_pct (float): Fixed stop loss percentage (e.g. 0.01 for 1%).
            tp_pct (float): Fixed take profit percentage (e.g. 0.02 for 2%).
        """
        self.strategy = strategy
        self.n_tp_levels = n_tp_levels
        self.n_sl_levels = n_sl_levels
        self.sl_pct = sl_pct
        self.tp_pct = tp_pct
        
    def init(self):
        """Optional initialization method for TradeLevelsCalculator."""
        pass
        
    def calculate_levels(self, tp_levels, sl_levels, direction):
        """
        Calculate stop loss (SL) and take profit (TP) levels based on the given direction and strategy,
        using fixed TP and SL percentages.
        
        Parameters:
            direction (str): The trade direction ('buy' or 'sell').
        
        Returns:
            tuple: A tuple containing lists of SL levels and TP levels.
        """
        # Use FixedTP_SL_TradeManagement instead of ATR_RR_TradeManagement
        fixed_tm = FixedTP_SL_TradeManagement(self.strategy, sl=self.sl_pct, tp=self.tp_pct)
        final_sl, final_tp = fixed_tm.calculate_tp_sl(direction)
        
        entry_price = self.strategy.data.df['Close'].iloc[-1]
        
        if direction.lower() == 'buy':
            tp_distance = final_tp - entry_price
            sl_distance = entry_price - final_sl
            tp_levels = [
                round(entry_price + (i * (tp_distance / self.n_tp_levels)), 5)
                for i in range(1, self.n_tp_levels + 1)
            ]
            sl_levels = [
                round(entry_price - (i * (sl_distance / self.n_sl_levels)), 5)
                for i in range(1, self.n_sl_levels + 1)
            ]
        elif direction.lower() == 'sell':
            tp_distance = entry_price - final_tp
            sl_distance = final_sl - entry_price
            tp_levels = [
                round(entry_price - (i * (tp_distance / self.n_tp_levels)), 5)
                for i in range(1, self.n_tp_levels + 1)
            ]
            sl_levels = [
                round(entry_price + (i * (sl_distance / self.n_sl_levels)), 5)
                for i in range(1, self.n_sl_levels + 1)
            ]
        else:
            raise ValueError(f"Invalid direction: {direction}. Must be 'buy' or 'sell'.")
        
        return sl_levels, tp_levels