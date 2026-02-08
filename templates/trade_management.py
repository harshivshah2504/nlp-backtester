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

        return stop_loss, take_profit\


import os
import sys
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



import pandas as pd

class FixedTP_SL_TradeManagement:
    def __init__(self, strategy, sl=0.015, tp=0.03):
        """
        Initialize the FixedTP_SL_TradeManagement class.

        :param strategy: reference to the Strategy object
        """
        self.strategy = strategy
        self.sl = sl
        self.tp = tp
        df = self.strategy.data.df

    def calculate_tp_sl(self, direction):
        """
        Calculate stop loss and take profit based on fixed pip values passed as arguments.

        :param direction: 'buy' or 'sell'
        :param stop_loss_pips: fixed stop loss in price units
        :param take_profit_pips: fixed take profit in price units
        :return: tuple (stop_loss_price, take_profit_price)
        """
        entry_price = self.strategy.data.df['Close'].iloc[-1]

        if direction.lower() == 'buy':
            stop_loss = entry_price*(1-self.sl)
            take_profit = entry_price*(1+self.tp)
        elif direction.lower() == 'sell':
            stop_loss = entry_price*(1+self.sl)
            take_profit = entry_price*(1-self.tp)
        else:
            raise ValueError("Invalid direction. Must be 'buy' or 'sell'.")

        stop_loss = round(stop_loss, 5)
        take_profit = round(take_profit, 5)

        return stop_loss, take_profit


import pandas as pd
from backtester.helpers.indicators import calculate_atr 

class PSAR_TradeManagement:
    def __init__(self, strategy, af0=0.02, af=0.02, af_max=0.2, risk_reward_ratio=1.5):
        self.strategy = strategy
        self.af0 = af0
        self.af = af
        self.af_max = af_max
        self.risk_reward_ratio = risk_reward_ratio
        self.atr_period = 14  
        df = self.strategy.data.df
        psar_df = df.ta.psar(af0=self.af0, af=self.af, max_af=self.af_max)
        self.psar = psar_df[f'PSARl_{self.af}_{self.af_max}'].combine_first(psar_df[f'PSARs_{self.af}_{self.af_max}'])

    def calculate_tp_sl(self, direction):
        df = self.strategy.data.df
        entry_price = df['Close'].iloc[-1]
        if len(self.psar)<=(len(df)-2):
            self.psar= df.ta.psar(af0=self.af0, af=self.af, max_af=self.af_max)[f'PSARl_{self.af}_{self.af_max}'].combine_first(df.ta.psar(af0=self.af0, af=self.af, max_af=self.af_max)[f'PSARs_{self.af}_{self.af_max}'])
        psar_value = self.psar.iloc[len(df)-2]

        if pd.isna(psar_value):
            raise ValueError("PSAR value is NaN, insufficient data.")
        
        atr = calculate_atr(df, self.atr_period)  

        if direction.lower() == 'buy':
            # Ensure stop-loss is always below entry price
            stop_loss = min(psar_value, entry_price - 1.5 * atr)
            stop_loss = min(stop_loss, entry_price - 0.01)  # Ensure SL is below entry
            risk = entry_price - stop_loss
            take_profit = entry_price + (risk * self.risk_reward_ratio)

            # Validate SL and TP positioning
            if stop_loss >= entry_price or take_profit <= entry_price:
                stop_loss = entry_price * 0.99  # Adjust SL slightly below entry
                take_profit = entry_price * 1.01  # Adjust TP slightly above entry

        elif direction.lower() == 'sell':
            # Ensure stop-loss is always above entry price
            stop_loss = max(psar_value, entry_price + 1.5 * atr)
            stop_loss = max(stop_loss, entry_price + 0.01)  # Ensure SL is above entry
            risk = stop_loss - entry_price
            take_profit = entry_price - (risk * self.risk_reward_ratio)

            # Validate SL and TP positioning
            if stop_loss <= entry_price or take_profit >= entry_price:
                stop_loss = entry_price * 1.01  # Adjust SL slightly above entry
                take_profit = entry_price * 0.99  # Adjust TP slightly below entry

        else:
            raise ValueError(f"Invalid direction: {direction}. Must be 'buy' or 'sell'.")

        return round(stop_loss, 5), round(take_profit, 5)



class Pivots_Points_TradeManagement:
    def __init__(self, strategy):
        """
        Initialize pivot-based trade management system.
        
        :param strategy: Reference to Strategy class object
        """
        self.strategy = strategy

    def calculate_tp_sl(self, direction):
        """
        Calculate stop loss and take profit levels based on pivot points.
        
        :param direction: Trade direction ('buy' or 'sell')
        :return: Tuple (stop_loss, take_profit)
        """
        df = self.strategy.data.df
        
        # Get previous period's prices
        prev_high = df['High'].iloc[-1]
        prev_low = df['Low'].iloc[-1]
        prev_close = df['Close'].iloc[-1]
        
        # Calculate pivot points
        pp = (prev_high + prev_low + prev_close) / 3
        r1 = (2 * pp) - prev_low
        r2 = pp + (prev_high - prev_low)
        s1 = (2 * pp) - prev_high
        s2 = pp - (prev_high - prev_low)
        rmean = (r1+r2) / 2
        smean = (s1+s2) / 2

        if direction.lower() == 'buy':
            stop_loss = smean 
            take_profit = rmean 
            current_price = df['Close'].iloc[-1]  
        elif direction.lower() == 'sell':
            stop_loss = rmean 
            take_profit = smean 
            current_price = df['Close'].iloc[-1] 
        
        
        stop_loss = round(stop_loss, 5)
        take_profit = round(take_profit, 5)

        return stop_loss, take_profit



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


from backtester.helpers.indicators import calculate_atr

class Swing_High_Low:
    def __init__(self, strategy, swing_length=6, risk_reward_ratio=2):
        """
        Initialize swing-based trade management system with fixed ATR parameters.
        
        :param strategy: Reference to Strategy class object
        :param swing_length: Number of bars to consider for swing points (N)
        :param risk_reward_ratio: Desired risk-reward ratio (default 2:1)
        """
        self.strategy = strategy
        self.swing_length = swing_length
        self.risk_reward_ratio = risk_reward_ratio
        
        # Fixed parameters as per requirements
        self.buffer_multiplier = 2  
        self.atr_period = 14         
    def calculate_tp_sl(self, direction):
        """
        Calculate stop loss and take profit levels based on swing points.
        
        :param direction: Trade direction ('buy' or 'sell')
        :return: Tuple (stop_loss, take_profit) as raw float values
        """
        df = self.strategy.data.df
        entry_price = df['Close'].iloc[-1]
        

        atr = calculate_atr(df, self.atr_period)

        buffer = self.buffer_multiplier * atr
        
        # Calculate swing points
        window_size = self.swing_length + 1  
        swing_high = df['High'].rolling(window=window_size).max().iloc[-1]
        swing_low = df['Low'].rolling(window=window_size).min().iloc[-1]

        if direction.lower() == 'buy':
            stop_loss = swing_low - buffer
            risk = entry_price - stop_loss  # Use stop_loss instead of swing_low to ensure positive risk
            take_profit = entry_price + (risk * self.risk_reward_ratio)
            
            # Ensure valid order: SL < Entry < TP
            if stop_loss >= entry_price or take_profit <= entry_price:
                raise ValueError(f"Invalid buy levels: SL={stop_loss}, Entry={entry_price}, TP={take_profit}")

        elif direction.lower() == 'sell':
            stop_loss = swing_high + buffer
            risk = stop_loss - entry_price
            take_profit = entry_price - (risk * self.risk_reward_ratio)
            
            # Ensure valid order: TP < Entry < SL
            if stop_loss <= entry_price or take_profit >= entry_price:
                raise ValueError(f"Invalid sell levels: SL={stop_loss}, Entry={entry_price}, TP={take_profit}")

        else:
            raise ValueError(f"Invalid direction: {direction}. Must be 'buy' or 'sell'.")
        
        return round(stop_loss, 5), round(take_profit, 5)