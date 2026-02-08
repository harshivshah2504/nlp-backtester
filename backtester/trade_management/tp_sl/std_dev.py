from backtester.helpers.indicators import calculate_standard_deviation


class Standard_Deviation_TradeManagement:
    def __init__(self, strategy, risk_reward_ratio = 1.5, std_dev_multiplier = 2, std_dev_period = 16):
        """
        Initialize the Standard Deviation based TradeManagement class.
        A reference to Strategy class object is included to access all of its parameters
        """
        self.strategy = strategy
        self.risk_reward_ratio = risk_reward_ratio
        self.std_dev_multiplier = std_dev_multiplier
        self.std_dev_period = std_dev_period

    def calculate_tp_sl(self, direction):
        """
        Calculate the stop loss and take profit levels based on Standard Deviation and R:R ratio.

        :param df: pandas DataFrame, must contain 'High', 'Low', and 'Close' columns
        :param direction: str, either 'buy' or 'sell'
        :return: tuple, stop loss and take profit prices
        """
        entry_price = self.strategy.data.df['Close'].iloc[-1]
        
        # Initialize the StandardDeviation class and calculate std deviation
        std_dev = calculate_standard_deviation(self.strategy.data.df, self.std_dev_period)


        risk = std_dev * self.std_dev_multiplier

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

        return stop_loss, take_profit
