import numpy as np

class PortfolioHeatRiskManagement:
    def __init__(self, strategy, initial_risk_per_trade: float = 0.01) -> None:
        self.strategy = strategy
        self.initial_risk_per_trade = initial_risk_per_trade
        
    def get_sqn(self):
        num_trades = len(self.strategy._broker.closed_trades)
        
        if num_trades == 0:
            # No trade made so far
            return 0
        
        num_trades = min(100, num_trades) # num_trades capped by 100
        avg_r_multiple = np.mean([trade.pl_pct for trade in self.strategy._broker.closed_trades])
        std_r_multiple = np.std([trade.pl_pct for trade in self.strategy._broker.closed_trades])
        if std_r_multiple == 0:
            return 0
        
        sqn = (avg_r_multiple / std_r_multiple) * np.sqrt(num_trades)
        
        if sqn < 1:
            sqn = 1  
        elif sqn > 7:
            sqn = 7  
        
        return sqn
    
    def get_risk_per_trade(self):
        num_trades = len(self.strategy._broker.closed_trades)
        current_capital = self.strategy._broker._cash
        # Fixed position size for the first 20 trades
        if num_trades <= 20:
            return 0.5* current_capital * self.initial_risk_per_trade
        
        # For trades beyond 20
        sqn = self.get_sqn()
        if sqn == 0:
            trade_size = 0.2 * current_capital * self.initial_risk_per_trade 
        else:
            trade_size = current_capital * self.initial_risk_per_trade * (2 + (sqn - 2)) / 3
            
        return trade_size
    
    def update_after_loss(self):
        pass
    def update_after_win(self):
        pass