
class PriceDeltaTradeManagement:
    def __init__(self, strategy, price_delta = 0.015):
        """
        Initialize the PriceDeltaTradeManagement class.

        :param price_delta: float, the percentage delta to set stop loss and take profit levels.
        """
        self.strategy = strategy
        self.price_delta = price_delta

    def calculate_tp_sl(self, direction):
        """
        Calculate the stop loss and take profit levels based on the percentage price delta.

        :param df: pandas DataFrame, must contain 'Close' column.
        :param direction: str, either 'buy' or 'sell'.
        :return: tuple, stop loss and take profit prices.
        """
        entry_price = self.strategy.data.df['Close'].iloc[-1]
        delta = entry_price * self.price_delta

        if direction.lower() == 'buy':
            stop_loss = entry_price * (1 - self.price_delta)
            take_profit = entry_price * (1 + self.price_delta)
        elif direction.lower() == 'sell':
            stop_loss = entry_price * (1 + self.price_delta)
            take_profit = entry_price * (1 - self.price_delta)
        else:
            raise ValueError("Invalid direction. Must be 'buy' or 'sell'.")
        
        return stop_loss, take_profit
