import os
import sys
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)


class EqualRiskManagement:
    def __init__(self, strategy, initial_risk_per_trade=0.01):
        '''A reference to the strategy object is stored here. 
        So, updates in strategy object directly reflected here as well
        '''
        self.strategy = strategy 
        self.initial_risk_per_trade = initial_risk_per_trade
        self.current_level = 0

    def get_risk_per_trade(self):
        trade_size = (self.strategy._broker._cash) * self.initial_risk_per_trade
        return trade_size

    def update_after_loss(self):
        self.current_level += 1

    def update_after_win(self):
        self.current_level = 0
