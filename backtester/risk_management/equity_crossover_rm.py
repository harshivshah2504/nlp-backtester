class EquityCrossoverRiskManagement:
    def __init__(self, strategy, initial_risk_per_trade=0.01, size_increment=0.25, size_decrement=0.15, n_trades=20):
        self.strategy = strategy # Reference to strategy object
        self.size_increment = size_increment
        self.size_decrement = size_decrement
        self.n_trades = n_trades
        self.risk_percent = initial_risk_per_trade # Initial risk percent
        self.equity_history = [] # Store the equities at the beginning of the trades
        
    def get_risk_per_trade(self):
        if len(self.equity_history) >= self.n_trades: # Changing the risk percentage only when atleast n_trades have occured
            current_capital = self.strategy._broker._cash
            moving_average = sum(self.equity_history[-self.n_trades:]) / self.n_trades
            if current_capital > moving_average:
                self.risk_percent *= (1 + self.size_increment)
            else:
                self.risk_percent *= (1 - self.size_decrement)
        self.equity_history.append(self.strategy._broker._cash)
        risk = self.strategy._broker._cash * self.risk_percent
        return risk
    
    def update_after_loss(self):
        pass
    
    def update_after_win(self):
        pass
    
if __name__ == '__main__':
    print("Here in main!")