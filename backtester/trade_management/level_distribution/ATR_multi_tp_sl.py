import os
import sys
import pandas as pd


parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)
from backtester.helpers.indicators import calculate_atr  

class ATR_Multiple_TP_SL_TradeManagement:
    def __init__(self, strategy, atr_period=14):
        """
        Initialize the ATR-based Trade Management class.
        A reference to the Strategy class object is included to access its parameters.
        """
        self.strategy = strategy
        self.atr_period = atr_period
    
    def calculate_tp_sl(self, direction):
        """
        Calculate multiple take profit and stop loss levels based on ATR.
        
        :param direction: str, either 'buy' or 'sell'
        :return: tuple, (list of take profit levels, list of stop loss levels)
        """
        
        entry_price = self.strategy.data.df['Close'].iloc[-1]
        
        atr = calculate_atr(self.strategy.data.df, self.atr_period)

        if direction.lower() == 'buy':
            
            tp_levels = [
                entry_price + (1 * atr),
                entry_price + (1.5 * atr),
                entry_price + (2 * atr)
            ]
            sl_levels = [
                entry_price - (2 * atr),
                self.strategy.data.df['Low'].iloc[-2:].min(),
                entry_price - (1 * atr)
            ]
        elif direction.lower() == 'sell':
            
            tp_levels = [
                entry_price - (1 * atr),
                entry_price - (1.5 * atr),
                entry_price - (2 * atr)
            ]
            sl_levels = [
                entry_price + (2 * atr),
                self.strategy.data.df['High'].iloc[-2:].max(),
                entry_price + (1 * atr)
            ]
        else:
            raise ValueError("Invalid direction. Must be 'buy' or 'sell'.")

        # Round the values and return as two lists.
        tp_levels = [round(tp, 5) for tp in tp_levels]
        sl_levels = [round(sl, 5) for sl in sl_levels]
        return tp_levels, sl_levels
