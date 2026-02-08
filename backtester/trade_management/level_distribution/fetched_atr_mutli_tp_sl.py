import os
import sys
import pandas as pd

parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)
from backtester.trade_management.tp_sl.atr_tm import ATR_RR_TradeManagement
from backtester.risk_management.rpt import RiskPerTrade
from backtester.helpers.indicators import calculate_atr

class ATRMultipTpSl:
    def __init__(self, strategy, atr_period=14, base_multiplier=1.0, steps=3, step_size=0.5):
        self.strategy = strategy
        self.atr_period = atr_period
        self.base_multiplier = base_multiplier
        self.steps = steps  # Number of TP/SL levels to generate
        self.step_size = step_size  # Increment step size for ATR multiplier
        self.risk_per_trade = RiskPerTrade(strategy)
        
        # Base ATR trade management
        self.atr_tm = ATR_RR_TradeManagement(strategy, atr_period=atr_period, atr_multiplier=3)
    
    
    def init(self): 
        """
        Optional initialization method for EfficiencyRatio.
        """
        pass
        

    def calculate_tp_sl(self, direction):
        # Fetch single TP/SL from base ATR_TM
        stop_loss, take_profit = self.atr_tm.calculate_tp_sl(direction)
        entry_price = self.strategy.data.df['Close'].iloc[-1]
        
        # Compute multiple ATR-based TP/SL levels
        sl_levels = [{stop_loss: 0.0}]
        tp_levels = [{take_profit: 1.0}]
        
        for step in range(1, self.steps + 1):
            multiplier = self.base_multiplier + (step * self.step_size)
            atr_value = calculate_atr(self.strategy.data.df, self.atr_period)
            risk = atr_value * multiplier
            
            if direction.lower() == 'buy':
                sl_level = entry_price - risk
                tp_level = entry_price + (risk * self.atr_tm.risk_reward_ratio)
            elif direction.lower() == 'sell':
                sl_level = entry_price + risk
                tp_level = entry_price - (risk * self.atr_tm.risk_reward_ratio)
            else:
                raise ValueError("Invalid direction. Must be 'buy' or 'sell'.")
            
            sl_levels.append({round(sl_level, 5): step / self.steps})
            tp_levels.append({round(tp_level, 5): 1 - (step / self.steps)})
        
        return sl_levels, tp_levels
    
    def get_risk_per_trade(self):
        return self.risk_per_trade.get_risk_per_trade()
