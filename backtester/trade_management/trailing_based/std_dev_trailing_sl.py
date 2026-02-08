import os 
import sys
from backtester.helpers.indicators import calculate_standard_deviation  # Import the function
import numpy as np
import pandas as pd
from typing import List


class StdDevTrailingStrategy:
    def __init__(self, std_dev_multiplier=1.5, std_dev_period=16):
        """
        Initialize the StdDevTrailingStrategy with parameters.

        Args:
            std_dev_multiplier: Multiplier for standard deviation to set trailing SL distance
            std_dev_period: Lookback period for calculating rolling standard deviation
        """
        self.std_dev_multiplier = std_dev_multiplier
        self.std_dev_period = std_dev_period
        self.std_dev = None
        self.trailing_sl_levels = []
        self.data = None  # Will be set by the strategy when used

    def init(self):
        """Initialize the trailing SL strategy."""
        self.set_std_dev()

    def set_std_dev(self):
        """
        Calculate the standard deviation of closing prices over the specified period
        using the imported calculate_standard_deviation function.
        """
        if self.data is None:
            raise ValueError("Data must be set before calculating standard deviation")
        
        # Use the imported function to calculate std dev for the entire series
        close_prices = pd.Series(self.data.Close)
        rolling_std = close_prices.rolling(window=self.std_dev_period).apply(
            lambda x: calculate_standard_deviation(pd.DataFrame({'Close': x}), self.std_dev_period),
            raw=False
        ).bfill()
        self.std_dev = rolling_std.values

    def set_trailing_sl(self, std_dev_multiplier: float = 1.5):
        """
        Set the multiplier for the trailing stop-loss based on standard deviation.
        """
        self.std_dev_multiplier = std_dev_multiplier

    def next(self):
        """Update trailing SL for active trades."""
        index = len(self.data) - 1
        current_price = self.data.Close[index]
        std_dev_value = self.std_dev[index]

        for trade in self.trades(): 
            if trade.is_long:
                new_sl = current_price - std_dev_value * self.std_dev_multiplier
                current_sl_levels = trade.sl 
                trailing_sl = max(current_sl_levels) if current_sl_levels else -np.inf
                new_trailing_sl = max(trailing_sl, new_sl)
            else:  
                new_sl = current_price + std_dev_value * self.std_dev_multiplier
                current_sl_levels = trade.sl  # List of SL prices
                trailing_sl = min(current_sl_levels) if current_sl_levels else np.inf
                new_trailing_sl = min(trailing_sl, new_sl)

            self._update_trailing_sl(trade, new_trailing_sl)
            self.trailing_sl_levels.append(round(new_trailing_sl, 5))

    def _update_trailing_sl(self, trade, new_sl: float):
        """
        Update the trailing stop-loss level for the trade.
        Assumes the first SL in the list is the trailing SL; additional SLs are static.
        """
        current_sl_orders = trade._sl_orders
        if not current_sl_orders:
            trade.sl = new_sl  
        else:
            trailing_order = current_sl_orders[0]
            trailing_order.cancel()
            current_sl_orders[0] = trade._broker.new_order(
                trade.ticker,
                -trade.size,
                trade=trade,
                tag=trade.tag,
                stop=new_sl
            )

    def get_sl_levels(self) -> List[float]:
        """
        Return the historical trailing stop-loss levels.
        """
        return self.trailing_sl_levels