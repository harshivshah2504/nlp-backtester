import math

class FixedRatioPositionSizing:
    def __init__(self, strategy, initial_risk_per_trade=0.01, delta=5000):
        self.strategy = strategy
        self.initial_risk_per_trade = initial_risk_per_trade  # Initial risk as % of capital
        self.initial_capital = self.strategy._broker._cash  # Starting capital
        self.delta = delta  # Dollar profit needed to increase position size
        self.equity = [self.initial_capital]  # Track equity over trades
        self.profit = 0  # Cumulative profit (P)

    def calculate_profit(self):
        # Calculate cumulative profit as the difference between current equity and initial capital
        self.profit = self.equity[-1] - self.initial_capital

    def get_risk_per_trade(self):
        capital = self.strategy._broker._cash
        
        # Append the latest equity
        self.equity.append(capital)
        
        # Calculate the profit P
        self.calculate_profit()

        # If profit is negative, default to initial risk per trade
        if self.profit <= 0:
            risk_per_trade = self.initial_risk_per_trade * self.initial_capital
        else:
            # Calculate risk per trade using the Fixed Ratio Position Sizing formula
            ##N = 0.5 * [((2 * N0 – 1)^2 + 8 * P/delta)^0.5 + 1] N0 = 1 for as of now
            risk_per_trade = (
                0.5 * (math.sqrt(1 + 8 * (self.profit / self.delta)) + 1)
                * self.initial_risk_per_trade
                * self.initial_capital
            )

        return risk_per_trade
    
    def update_after_loss(self):
        pass

    def update_after_win(self):
        pass
