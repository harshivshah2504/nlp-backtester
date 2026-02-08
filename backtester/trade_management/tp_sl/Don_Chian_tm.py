import os
import sys
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0,parent_dir)

from backtester.helpers.indicators import calculate_donchian_channel_and_atr
import pandas as pd

class Donn_China_RR_TradeManagement:
    def __init__(self, strategy, atr_multiplier = 1.5, atr_period = 14, channel_period = 20,risk_reward_ratio = 2):
        self.strategy = strategy
        self.atr_multiplier = atr_multiplier
        self.atr_period = atr_period
        self.channel_period = channel_period
        self.risk_reward_ratio = risk_reward_ratio

    def calculate_tp_sl(self, direction):
        df = self.strategy.data.df
        entry_price = df['Close'].iloc[-1]

        # Fetch Donchian Channel and ATR using the imported function
        lower_channel, upper_channel, atr = calculate_donchian_channel_and_atr(
            df, atr_period=self.atr_period, channel_period=self.channel_period
        )

        # Ensure valid data
        if any(pd.isna([lower_channel, upper_channel, atr, entry_price])):
            raise ValueError(f"Invalid data detected. Lower Channel: {lower_channel}, Upper Channel: {upper_channel}, ATR: {atr}, Entry Price: {entry_price}")

        # Calculate Stop Loss and Take Profit
        if direction.lower() == 'buy':
            stop_loss = lower_channel - (atr * self.atr_multiplier)
            take_profit = entry_price + (entry_price - stop_loss)   
        elif direction.lower() == 'sell':
            stop_loss = upper_channel + (atr * self.atr_multiplier)
            take_profit = entry_price - (stop_loss - entry_price)  


        # Validate Stop Loss and Take Profit
        if stop_loss <= 0 or take_profit <= 0:
            raise ValueError(
                f"Invalid Stop Loss ({stop_loss}) or Take Profit ({take_profit}) calculated for direction '{direction}'. "
                f"Entry Price: {entry_price}, Lower Channel: {lower_channel}, Upper Channel: {upper_channel}, ATR: {atr}"
            )

        return stop_loss, take_profit
