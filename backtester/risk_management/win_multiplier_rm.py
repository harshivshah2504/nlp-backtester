import numpy as np
import os
import sys
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

class WinMultiplier:
    def __init__(self, strategy, initial_risk_per_trade=0.01,num_past_trade= 5):
        """
        Initialize the RiskPerTrade class.
        
        :param strategy: The trading strategy object.
        :param initial_risk_per_trade: Initial risk percentage per trade (default: 3%).
        :param num_past_trades: Number of past trades to consider for win/loss ratio (default: 5).
        """
        self.strategy = strategy  
        self.initial_equity = strategy._broker._cash
        self.initial_risk_per_trade = initial_risk_per_trade
        self.past_trades = [] 
        self.num_past_trade = num_past_trade
        

    def get_risk_per_trade(self):
        """
        Calculate the risk per trade based on the past win/loss ratio and adjust position sizing.
        """
       
        if len(self.past_trades) < self.num_past_trade:
            raise ValueError("Not enough trades have been completed to calculate risk per trade.")
        
       
        wins = sum(self.past_trades[-self.num_past_trade:])  
        losses = self.num_past_trade - wins 

       
        win_ratio = wins / self.num_past_trade
        
        
        win_multiplier = win_ratio * 0.3  

        
        adjusted_position_size = self.initial_equity * self.initial_risk_per_trade * (1 + win_multiplier)

       
        risk_per_trade = adjusted_position_size  

        return risk_per_trade

    def update_after_loss(self):
        """Optional logic after a loss (e.g., reduce risk and add to past trades)"""
        self.past_trades.append(False) 
        self.initial_risk_per_trade *= 0.9  

    def update_after_win(self):
        """Optional logic after a win (e.g., increase risk and add to past trades)"""
        self.past_trades.append(True)  
        self.initial_risk_per_trade *= 1.1 
