import numpy as np
import os
import sys

# Setting up parent directory for imports if needed
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

class RiskPerTrade:
    def __init__(self, strategy, initial_risk_per_trade=0.01, profit_risk_percentage=0.1):
        self.initial_equity = strategy._broker._cash
        self.initial_risk_per_trade = initial_risk_per_trade
        self.profit_risk_percentage = profit_risk_percentage
        self.closed_trade_profit = 0 

    def get_risk_per_trade(self):
        base_risk = self.initial_equity * self.initial_risk_per_trade
        profit_risk = self.closed_trade_profit * self.profit_risk_percentage
        risk_per_trade = base_risk + profit_risk
        return risk_per_trade

    def update_after_loss(self):
        pass
    def update_after_win(self):
        pass
    