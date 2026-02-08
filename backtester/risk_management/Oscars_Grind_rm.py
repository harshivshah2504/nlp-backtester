class OscardsGrindRiskManagement:
    def __init__(self, strategy, initial_risk_per_trade=0.01):
        self.strategy = strategy
        self.initial_risk_per_trade = self.initial_risk_per_trade
        self.initial_capital = self.strategy._broker._cash
        self.winning_goal = self.initial_risk_per_trade
        self.current_stake = self.initial_risk_per_trade
        self.current_capital = self.initial_capital
        self.current_wins = 0

    def get_risk_per_trade(self):
        self.current_capital = self.strategy._broker._cash
        return self.current_stake

    def update_after_loss(self):
        # After a loss or tie, the stake remains the same
        self.current_stake = self.winning_goal

    def update_after_win(self):
        # After a win, increase the next bet by one unit
        self.current_stake += self.winning_goal

    def reset(self):
        # Optionally, reset to initial settings
        self.current_stake = self.winning_goal
        self.current_capital = self.initial_capital