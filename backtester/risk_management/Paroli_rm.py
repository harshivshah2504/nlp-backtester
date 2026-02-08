class ParoliRiskManagement:
    def __init__(self, strategy, initial_risk_per_trade=0.01):
        self.strategy = strategy
        self.initial_risk_per_trade = initial_risk_per_trade
        self.initial_capital = strategy._broker._cash
        self.base_stake = initial_risk_per_trade
        self.current_stake = initial_risk_per_trade
        self.current_capital = strategy._broker._cash
        self.consecutive_wins = 0

    def get_risk_per_trade(self):
        self.current_capital = self.strategy._broker._cash
        return self.current_stake

    def update_after_loss(self):
        self.current_stake = self.base_stake
        self.consecutive_wins = 0

    def update_after_win(self):
        self.consecutive_wins += 1
        if self.consecutive_wins >= 3:
            self.current_stake = self.base_stake
            self.consecutive_wins = 0
        else:
            self.current_stake = self.base_stake * (2 ** self.consecutive_wins)