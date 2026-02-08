import math

class FixedRatioPositionSizing:
    def __init__(self, strategy, initial_risk_per_trade=0.01, delta=5000, m=0.5):
        self.strategy = strategy
        self.initial_risk_per_trade = initial_risk_per_trade  # Initial risk as % of capital
        self.initial_capital = self.strategy._broker._cash  # Starting capital
        self.delta = delta  # Dollar profit needed to increase position size
        self.m = m #this is the exponent factor
        self.equity = [self.initial_capital]  # Track equity over trades
        self.profit = 0  # Cumulative profit (P)
        self.current_risk_percent = initial_risk_per_trade  # Current risk as % of capital
    

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
            #N = 0.5 * [(1 + 8 * P/delta)^m + 1] 
            risk_per_trade = (
                0.5 * (pow((1 + 8 * (self.profit / self.delta)),self.m) + 1)
                * self.initial_risk_per_trade
                * self.initial_capital
            )

        return risk_per_trade
    
    def print_equity(self):
        return self.equity
    
    def update_after_loss(self):
        # Custom logic for loss can be added if needed
        pass

    def update_after_win(self):
        # Custom logic for win can be added if needed
        pass
