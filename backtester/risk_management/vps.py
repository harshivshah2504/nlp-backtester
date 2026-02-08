import numpy as np
import os
import sys
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)


class VolatilityBasedPositionSizing:
    def __init__(self, strategy, initial_risk_per_trade = 0.01, target_var=0.015):
        self.strategy = strategy
        self.initial_equity = strategy._broker._cash
        self.initial_risk_per_trade = initial_risk_per_trade
        self.target_var = target_var
        self.lambda_decay = 0.94
        self.window_size = 74  # Number of trades for the estimation window

    def get_risk_per_trade(self):
        price_data = self.strategy.data['Close'] 
        returns = np.diff(price_data) / price_data[:-1]  
        
        # Check if the number of returns is less than the window size
        if len(returns) < self.window_size:
            # If insufficient data, use all available returns
            effective_window_size = len(returns)
        else:
            effective_window_size = self.window_size
        
        # Compute exponentially weighted moving average (EWMA) volatility
        weights = np.array([self.lambda_decay ** (effective_window_size - t - 1) for t in range(effective_window_size)])
        weights /= weights.sum()
        mean_return = np.mean(returns[-effective_window_size:])
        volatility = np.sqrt(np.sum(weights * (returns[-effective_window_size:] - mean_return) ** 2))  # EWMA volatility
        
        # Compute Value at Risk (VaR)
        var = -(mean_return - 1.65 * volatility)  # 95% VaR corresponds to 1.65 standard deviations
        leverage_adjustment = self.target_var / var
        
        risk_per_trade = self.initial_risk_per_trade * leverage_adjustment
        return risk_per_trade

    def update_after_loss(self):
        pass

    def update_after_win(self):
        pass
