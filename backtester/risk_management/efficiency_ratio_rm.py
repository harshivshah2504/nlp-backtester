import numpy as np
import os
import sys
# Setting up parent directory for imports if needed
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

class EfficiencyRatio:
    def __init__(self, strategy, initial_risk_per_trade=0.01, profit_risk_percentage=0.1):
        self.initial_equity = strategy._broker._cash
        self.initial_risk_per_trade = initial_risk_per_trade
        self.profit_risk_percentage = profit_risk_percentage
        self.closed_trade_profit = 0
        self.prices = None

    def init(self):  # Properly indented as a class method
        """
        Optional initialization method for EfficiencyRatio.
        """
        pass



    def get_risk_per_trade(self):
        """
        Calculates the risk per trade using Efficiency Ratio Scaling.
        
        The total risk (base risk + profit bonus) is scaled by the Efficiency Ratio (ER):
        
            ER = (|last_price - first_price|) / (sum of absolute differences between consecutive prices)
        
        If no price data is available in self.prices, ER defaults to 1.
        
        Returns:
            float: The risk per trade in monetary units.
        """
        # Calculate the base risk and profit bonus.
        base_risk = self.initial_equity * self.initial_risk_per_trade
        profit_bonus = self.closed_trade_profit * self.profit_risk_percentage
        total_risk = base_risk + profit_bonus

        # Calculate the Efficiency Ratio (ER) using stored price data if available.
        if self.prices is not None and len(self.prices) >= 2:
            price_change = abs(self.prices[-1] - self.prices[0])
            volatility = np.sum(np.abs(np.diff(self.prices)))
            er = price_change / volatility if volatility != 0 else 0.0
            er = max(0.0, min(er, 1.0))
        else:
            er = 1.0  # Default to full risk if no price data is available

        risk_per_trade = total_risk * er
        return risk_per_trade

    def update_after_win(self):
        """
        Update internal state after a winning trade.
        
        For demonstration purposes, this method adds a fixed profit value
        to the cumulative closed trade profit.
        """
        # Update with a default profit amount (e.g., $500)
        default_profit = 500  
        self.closed_trade_profit += default_profit

    def update_after_loss(self):
        """
        Update internal state after a losing trade.
        
        For demonstration purposes, this method subtracts a fixed loss value
        from the cumulative closed trade profit.
        """
        # Update with a default loss amount (e.g., $300)
        default_loss = 300  
        self.closed_trade_profit -= default_loss