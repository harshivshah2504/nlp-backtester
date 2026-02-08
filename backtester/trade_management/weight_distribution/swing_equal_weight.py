import os
import sys
import math
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)
from backtester.trade_management.tp_sl.swing_high_low_tm import Swing_High_Low
from backtester.trade_management.level_distribution.swing_atr_multi_tp_sl import TradeLevelsCalculator

class EqualWeightedDistribution:
    def __init__(self, strategy, n_tp_levels, n_sl_levels):
        self.strategy = strategy
        self.n_tp_levels = n_tp_levels
        self.n_sl_levels = n_sl_levels
        
        
    def init(self): 
        """
        Optional initialization method for EfficiencyRatio.
        """
        pass

    def calculate_weights(self, n_sl_levels, n_tp_levels):
        """Distributes weights evenly between levels"""
        weight_per_sl_level = round(1.0 / self.n_sl_levels, 5)
        weight_per_tp_level = round(1.0 / self.n_tp_levels, 5)
        
        
        weighted_sl = [{level: weight_per_sl_level} for level in n_sl_levels]
        weighted_tp = [{level: weight_per_tp_level} for level in n_tp_levels]
        
        return weighted_sl, weighted_tp

    def get_weighted_levels(self, direction):

        # Create an instance of TradeLevelsCalculator
        level_calculator = TradeLevelsCalculator(self.strategy)

        
        n_sl_levels, n_tp_levels = level_calculator.calculate_levels(
            n_tp_levels=self.n_tp_levels,
            n_sl_levels=self.n_sl_levels,
            direction=direction,
            df=self.strategy.data.df
        )

        # Add weights
        return self.calculate_weights(n_sl_levels, n_tp_levels)
