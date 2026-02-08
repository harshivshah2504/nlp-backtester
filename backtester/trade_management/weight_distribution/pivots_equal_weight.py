import os
import sys
import math
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)
#from backtester.trade_management.tp_sl.atr_tm import ATR_RR_TradeManagement
from backtester.trade_management.tp_sl.pivot_points_tm import Pivots_Points_TradeManagement
from backtester.trade_management.level_distribution.pivots_multi_tp_sl import TradeLevelsCalculator

class EqualWeightedDistribution:
    def __init__(self, strategy, n_tp_levels, n_sl_levels):
        self.strategy = strategy
        self.n_tp_levels = n_tp_levels
        self.n_sl_levels = n_sl_levels

    def calculate_weights(self, n_sl_levels, n_tp_levels):
        """Distributes weights evenly between levels"""
        weight_per_sl_level = round(1.0 / self.n_sl_levels, 5)
        weight_per_tp_level = round(1.0 / self.n_tp_levels, 5)
        
        
        weighted_sl = [{level: weight_per_sl_level} for level in n_sl_levels]
        weighted_tp = [{level: weight_per_tp_level} for level in n_tp_levels]
        
        return weighted_sl, weighted_tp
    
    
    def get_weighted_levels(self, direction):
        pivot_points_tm = Pivots_Points_TradeManagement(self.strategy)
        stop_loss, take_profit = pivot_points_tm.calculate_tp_sl(direction)
        
        # Fetch the TP/SL levels
        n_sl_levels, n_tp_levels = TradeLevelsCalculator(
            strategy=self.strategy,
            n_tp_levels=self.n_tp_levels,
            n_sl_levels=self.n_sl_levels,
            direction=direction,
        )
        
        # Add weights
        return self.calculate_weights(n_sl_levels, n_tp_levels)