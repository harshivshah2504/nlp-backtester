class DAlembertRiskManagement:
    def __init__(self, strategy, initial_risk_per_trade=0.01, step=1):
        self.strategy = strategy 
        self.initial_risk_per_trade = initial_risk_per_trade
        self.current_level = 0
        self.step = step  # Step size to increase or decrease the risk

    def calculate_risk_levels(self):
        risk_levels = []
        risk = self.initial_risk_per_trade
        while self.strategy._broker._cash > risk:
            risk_levels.append(risk)
            risk += self.step
        return risk_levels

    def get_risk_per_trade(self):
        risk_levels = self.calculate_risk_levels()
        if self.strategy._broker._cash >= len(risk_levels):
            return 0
        trade_size = self.strategy._broker._cash * risk_levels[self.current_level]
        return trade_size

    def update_after_loss(self):
        self.current_level += 1  # Increase the level after a loss
        if self.current_level >= len(self.calculate_risk_levels()):
            self.current_level = len(self.calculate_risk_levels()) - 1  # Cap the level

    def update_after_win(self):
        if self.current_level > 0:
            self.current_level -= 1  # Decrease the level after a win