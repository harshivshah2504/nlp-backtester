class ProfitRiskManagement:
    def __init__(self, strategy, initial_risk_per_trade=0.01, profit_risk_pct=0.1):
        self.strategy = strategy # Reference to strategy object
        self.initial_capital = self.strategy._broker._cash
        self.profit_risk_pct = profit_risk_pct # Inputted as a real value not percentage
        self.initial_risk_per_trade = initial_risk_per_trade
        
    def get_risk_per_trade(self):
        profit = self.strategy._broker._cash - self.initial_capital # Positive or negative
        trade_size = (self.initial_risk_per_trade * self.initial_capital) + (self.profit_risk_pct * profit)
        return trade_size
    
    def update_after_loss(self):
        pass
    
    def update_after_win(self):
        pass