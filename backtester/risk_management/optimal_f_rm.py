import numpy as np
import os
import sys
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

class OptimalFRiskManagement:
    def __init__(self, strategy, f_range=np.arange(0.01, 1.01, 0.01)):
        self.strategy = strategy
        self.initial_equity = strategy._broker._cash
        self.f_range = f_range  # Range of f values to optimize
        self.optimal_f = None  # Store optimal f value
    
    def get_trade_returns(self):
        trade_returns = []
        for trade in self.strategy.closed_trades:
            trade_returns.append(trade.pl_pct)
        return trade_returns

    def get_risk_per_trade(self):
        trade_returns = self.get_trade_returns()  # Assuming strategy has a function to get returns
        if len(trade_returns) == 0:
            return 0.01  # Default risk if no trades yet
        
        worst_loss = min(trade_returns)
        
        hprs = lambda f: [1 + f * (r / worst_loss) for r in trade_returns]
        twr_values = [np.prod(hprs(f)) for f in self.f_range]
        
        self.optimal_f = self.f_range[np.argmax(twr_values)]
        
        risk_per_trade =  self.optimal_f * self.initial_equity  
        return risk_per_trade
    
    def update_after_loss(self):
        pass  # Placeholder for potential adjustments after losses
    
    def update_after_win(self):
        pass  # Placeholder for potential adjustments after wins
