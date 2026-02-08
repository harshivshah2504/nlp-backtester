class TIIPRiskManagement:
    def __init__(self, strategy, initial_risk_per_trade=0.01, risk_percent=0.05):
        if not 0 < initial_risk_per_trade < 1:
            raise ValueError("initial_risk_per_trade must be between 0 and 1")
        if not 0 < risk_percent < 1:
            raise ValueError("risk_percent must be between 0 and 1")
        if not 0 < initial_risk_per_trade < 1:
            raise ValueError("initial_risk_per_trade must be between 0 and 1")
        if not 0 < risk_percent < 1:
            raise ValueError("risk_percent must be between 0 and 1")
        self.strategy = strategy # Reference to strategy object
        self.initial_risk_per_trade = initial_risk_per_trade
        self.protection_floor = self.strategy._broker._cash * (1 - self.initial_risk_per_trade)
        self.risk_percent = risk_percent
        
    def get_risk_per_trade(self):
        current_capital = self.strategy._broker._cash
        risk = (current_capital - self.protection_floor) * self.risk_percent
        return max(0, risk)
        
    def update_after_loss(self):
        pass
    
    def update_after_win(self):
        pass