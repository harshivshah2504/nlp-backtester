import numpy as np
import os
import sys
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

class MarketRegimeADX:
    def __init__(self, strategy, initial_risk_per_trade=0.01, profit_risk_percentage=0.1, adx_threshold=20):
        """
        Initialize the RiskPerTrade class.

        :param strategy: The trading strategy object (must have an `adx` attribute or method).
        :param initial_risk_per_trade: Initial risk percentage per trade (default: 3%).
        :param profit_risk_percentage: Percentage of profits to add to risk (default: 10%).
        :param adx_threshold: ADX threshold for determining trending markets (default: 25).
        """
        self.strategy = strategy 
        self.initial_equity = strategy._broker._cash
        self.initial_risk_per_trade = initial_risk_per_trade
        self.profit_risk_percentage = profit_risk_percentage
        self.closed_trade_profit = 0
        self.adx_threshold = adx_threshold

    def get_risk_per_trade(self):
        """
        Calculate the risk per trade based on the current ADX value.
        ADX value is fetched directly from the strategy object.
        """
        
        if hasattr(self.strategy, 'adx') and len(self.strategy.adx) > 0:
            adx_value = self.strategy.adx[-1] 
        else:
            raise ValueError("ADX data not found in the strategy object.")
        
        base_risk = self.initial_equity * self.initial_risk_per_trade
        profit_risk = self.closed_trade_profit * self.profit_risk_percentage
        total_risk = base_risk + profit_risk

        
        if adx_value >= self.adx_threshold:
            risk_multiplier = 1.0  
        else:
            risk_multiplier = 0.5  

        risk_per_trade = total_risk * risk_multiplier
        
        return risk_per_trade

    def update_after_loss(self):
        """Optional logic after a loss (e.g., reduce risk)"""
        self.initial_risk_per_trade *= 0.9  

    def update_after_win(self):
        """Optional logic after a win (e.g., increase risk)"""
        self.initial_risk_per_trade *= 1.1  
