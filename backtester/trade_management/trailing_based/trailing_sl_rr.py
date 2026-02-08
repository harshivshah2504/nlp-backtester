from backtester.helpers.indicators import calculate_atr
from backtester.lib import TrailingStrategy  # Import the TrailingStrategy class from lib.py

class TrailingSLRR:
    def __init__(self, strategy, risk_reward_ratio=1.5, atr_multiplier=3, atr_period=14, trailing_stop=False, n_atr=6):
        """
        Initialize the TrailingSLRR class.
        A reference to Strategy class object is included to access all of its parameters.
        """
        self.strategy = strategy
        self.risk_reward_ratio = risk_reward_ratio
        self.atr_multiplier = atr_multiplier
        self.atr_period = atr_period
        self.trailing_stop = trailing_stop  # Flag to enable trailing stop

        # Create instance of TrailingStrategy with required arguments
        self.trailing_strategy = TrailingStrategy(
            self.strategy._broker,  # Ensure your strategy object has a 'broker' attribute
            self.strategy.data,    # Ensure your strategy object has a 'data' attribute
            self.strategy._params   # Ensure your strategy object has a 'params' attribute
        )
        self.trailing_strategy.set_trailing_sl(n_atr)  # Set trailing stop-loss multiplier

    def calculate_tp_sl(self, direction):
        """
        Calculate the stop loss and take profit levels based on ATR and R:R ratio.

        :param direction: str, either 'buy' or 'sell'
        :return: tuple, stop loss and take profit prices
        """
        entry_price = self.strategy.data['Close'].iloc[-1]
        atr = calculate_atr(self.strategy.data, self.atr_period)
        risk = atr * self.atr_multiplier

        if direction.lower() == 'buy':
            stop_loss = entry_price - risk
            take_profit = entry_price + (risk * self.risk_reward_ratio)
        elif direction.lower() == 'sell':
            stop_loss = entry_price + risk
            take_profit = entry_price - (risk * self.risk_reward_ratio)
        else:
            raise ValueError("Invalid direction. Must be 'buy' or 'sell'.")

        stop_loss = round(stop_loss, 5)
        take_profit = round(take_profit, 5)

        if self.trailing_stop:
            # If trailing stop is enabled, adjust the stop loss dynamically.
            # Assuming the trailing strategy provides a method to update or calculate the trailing stop loss.
            current_price = self.strategy.data['Close'].iloc[-1]
            stop_loss = self.trailing_strategy.set_trailing_sl(n_atr=self.trailing_strategy._TrailingStrategy__n_atr)

        return stop_loss, take_profit
