class ManhattanRiskManagement:
    def __init__(self, strategy, initial_risk_per_trade: float = 0.01) -> None:
        self.strategy = strategy
        self.initial_risk_per_trade = initial_risk_per_trade
        self.stake_increment = self.initial_risk_per_trade
        self.current_stake = self.initial_risk_per_trade
        self.current_capital = self.strategy._broker._cash
        self.initial_capital = self.strategy._broker._cash
        self.losses = 0

    def get_risk_per_trade(self):
        self.current_capital = self.strategy._broker._cash
        return self.current_stake

    def update_after_loss(self):
        self.losses += 1
        self.current_stake = self.initial_risk_per_trade + (self.stake_increment * self.losses)

    def update_after_win(self):
        self.current_stake = self.initial_risk_per_trade
        self.losses = 0

    def reset(self):
        self.current_stake = self.initial_risk_per_trade
        self.current_capital = self.initial_capital
        self.losses = 0