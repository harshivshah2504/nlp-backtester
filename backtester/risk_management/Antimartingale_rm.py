class AntiMartingaleRiskManagement:
    def __init__(self, strategy, initial_risk_per_trade=0.01, multiplier=1.5):
        self.strategy = strategy
        self.current_level = 0
        self.multiplier=multiplier
        self.initial_risk_per_trade = initial_risk_per_trade

    def calculate_risk_levels(self):
        # Calculate the risk levels using a martingale strategy
        risk_levels = []
        risk = self.initial_risk_per_trade
        for i in range(30):  # Assume a maximum of 10 levels
            risk_levels.append(risk)
            risk *= self.multiplier  # Double the risk at each level (Martingale approach)
        return risk_levels

    def get_risk_per_trade(self):
        risk_levels = self.calculate_risk_levels()
        if self.current_level >= len(risk_levels):
            return 0
        trade_size = self.strategy._broker._cash * risk_levels[self.current_level]
        return trade_size

    def update_after_loss(self):
        self.current_level = 0
   
    def update_after_win(self):
        self.current_level += 1
