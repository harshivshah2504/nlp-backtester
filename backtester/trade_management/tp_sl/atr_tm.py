from backtester.helpers.indicators import calculate_atr


class ATR_RR_TradeManagement:
    def __init__(self, strategy, risk_reward_ratio = 2, atr_multiplier = 1.5, atr_period = 14):
        """
        Initialize the ATR_RR_TradeManagement class.
        A reference to Strategy class object is included to access all of its parameters
        """
        self.strategy = strategy
        self.risk_reward_ratio = risk_reward_ratio
        self.atr_multiplier = atr_multiplier
        self.atr_period = atr_period
        
        
        
    def init(self): 
        """
        Optional initialization method for EfficiencyRatio.
        """
        pass
        

    def calculate_tp_sl(self, direction):
        """
        Calculate the stop loss and take profit levels based on ATR and R:R ratio.

        :param df: pandas DataFrame, must contain 'High', 'Low', and 'Close' columns
        :param direction: str, either 'buy' or 'sell'
        :return: tuple, stop loss and take profit prices
        """
        entry_price = self.strategy.data.df['Close'].iloc[-1]
        atr = calculate_atr(self.strategy.data.df, self.atr_period)
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
        take_profit = round(take_profit,5)

        return stop_loss, take_profit