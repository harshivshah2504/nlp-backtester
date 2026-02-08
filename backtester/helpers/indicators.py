import pandas as pd
import pandas_ta as ta
import numpy as np

def calculate_atr(df, atr_period):
    """
    Calculate the Average True Range (ATR) manually without modifying the input DataFrame.

    :param df: pandas DataFrame, must contain 'High', 'Low', and 'Close' columns
    :param atr_period: int, the period for ATR calculation
    :return: float, the ATR value
    """
    # Create a copy to avoid modifying the original dataframe
    df_copy = df.copy()
    
    # Calculate True Range (TR) without modifying the DataFrame
    prev_close = df_copy['Close'].shift(1)
    high_low = df_copy['High'] - df_copy['Low']
    high_close = abs(df_copy['High'] - prev_close)
    low_close = abs(df_copy['Low'] - prev_close)
    
    # True Range is the max of the three
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    
    # Calculate ATR as the rolling mean of TR
    atr = tr.rolling(window=atr_period).mean().iloc[-1]
    
    return atr


def calculate_donchian_channel_and_atr(df, atr_period, channel_period):
    """
    Calculate the Donchian Channel and ATR manually using custom Donchian function.
    
    :param df: pandas DataFrame, must contain 'High', 'Low', and 'Close' columns
    :param atr_period: int, the period for ATR calculation
    :param channel_period: int, the period for Donchian Channel calculation
    :return: tuple (lower_channel, upper_channel, atr)
    """
    # Calculate ATR using manual method
    atr = calculate_atr(df, atr_period)
    
    # Calculate Donchian Channel using pandas-ta
    donchian_result = ta.donchian(high=df['High'], low=df['Low'], lower_length=channel_period, upper_length=channel_period)
    print(donchian_result.columns)  # Debugging
    
    # Extract the Lower and Upper Channels from the Donchian result
    lower_channel_col = f'DCL_{channel_period}_{channel_period}'
    upper_channel_col = f'DCU_{channel_period}_{channel_period}'
    
    if lower_channel_col not in donchian_result.columns or upper_channel_col not in donchian_result.columns:
        raise ValueError(f"Expected columns '{lower_channel_col}' and '{upper_channel_col}' not found. Available columns: {donchian_result.columns}")
    
    lower_channel = donchian_result[lower_channel_col].iloc[-1]
    upper_channel = donchian_result[upper_channel_col].iloc[-1]
    
    return lower_channel, upper_channel, atr



def calculate_standard_deviation(df, std_dev_period):
    """
    Calculate the Standard Deviation of the closing prices over a given period.

    :param df: pandas DataFrame, must contain 'Close' column
    :param std_dev_period: int, the period for Standard Deviation calculation
    :return: float, the standard deviation value
    """
    # Calculate standard deviation over the given period
    std_dev = df['Close'].rolling(window=std_dev_period).std().iloc[-1]

    
    return std_dev




def calculate_ad_line(df):
        """
        Calculate the Accumulation/Distribution (A/D) line.

        :param df: DataFrame containing 'High', 'Low', 'Close', and 'Volume' columns
        :return: DataFrame with 'AD' column added
        """
        # Calculate Money Flow Multiplier (MFM)
        df['MFM'] = ((df['Close'] - df['Low']) - (df['High'] - df['Close'])) / (df['High'] - df['Low'])
        
        # Calculate Money Flow Volume (MFV)
        df['MFV'] = df['MFM'] * df['Volume']
        
        # Calculate Accumulation/Distribution (A/D) line
        df['AD'] = df['MFV'].cumsum()
        
        return df