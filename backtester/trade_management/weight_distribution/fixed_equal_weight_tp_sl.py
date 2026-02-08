import os
import sys
import math
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)
from backtester.trade_management.tp_sl.fixed_tm import FixedTP_SL_TradeManagement
from backtester.trade_management.level_distribution.fixed_multi_tp_sl import TradeLevelsCalculator

class FixedTP_SL_WeightDistribution:

    def __init__(self, strategy, n_tp_levels, n_sl_levels):
        """
        Initialize with number of TP and SL levels.
        
        :param n_tp_levels: Number of take profit levels.
        :param n_sl_levels: Number of stop loss levels.
        """
        self.strategy = strategy
        self.n_tp_levels = n_tp_levels
        self.n_sl_levels = n_sl_levels

    def calculate_weights(self, sl_levels, tp_levels):
        """
        Evenly distributes integer weights (percentages) across stop loss and take profit levels.
        Weights are integers and sum to 100.
        :param sl_levels: List of stop loss price levels.
        :param tp_levels: List of take profit price levels.
        :return: Tuple of (weighted_sl, weighted_tp), each a list of dicts.
        """
        if len(sl_levels) != self.n_sl_levels:
            raise ValueError(f"Expected {self.n_sl_levels} SL levels, but got {len(sl_levels)}")
        if len(tp_levels) != self.n_tp_levels:
            raise ValueError(f"Expected {self.n_tp_levels} TP levels, but got {len(tp_levels)}")

        total_weight = 100  # total percentage points

        weight_per_sl_level = total_weight // self.n_sl_levels
        sl_remainder = total_weight - weight_per_sl_level * self.n_sl_levels
        weighted_sl = []
        for i, level in enumerate(sl_levels):
            w = weight_per_sl_level + (sl_remainder if i == self.n_sl_levels - 1 else 0)
            w /= 100
            weighted_sl.append({level: w})

        weight_per_tp_level = total_weight // self.n_tp_levels
        tp_remainder = total_weight - weight_per_tp_level * self.n_tp_levels
        weighted_tp = []
        for i, level in enumerate(tp_levels):
            w = weight_per_tp_level + (tp_remainder if i == self.n_tp_levels - 1 else 0)
            w/= 100
            weighted_tp.append({level: w})

        total_sl_weight = sum(list(d.values())[0] for d in weighted_sl)
        total_tp_weight = sum(list(d.values())[0] for d in weighted_tp)

        if total_sl_weight != total_weight/100:
            raise ValueError(f"Sum of SL weights must be {total_weight} but is {total_sl_weight}")
        if total_tp_weight != total_weight/100:
            raise ValueError(f"Sum of TP weights must be {total_weight} but is {total_tp_weight}")

        return weighted_sl, weighted_tp
    
    def get_weighted_levels(self, direction):

        # Create an instance of TradeLevelsCalculator
        level_calculator = TradeLevelsCalculator(self.strategy, self.n_tp_levels, self.n_sl_levels, self.strategy.sl, self.strategy.tp)
        
        n_sl_levels, n_tp_levels = level_calculator.calculate_levels(
            n_tp_levels=self.n_tp_levels,
            n_sl_levels=self.n_sl_levels,
            direction=direction,
            df=self.strategy.data.df
        )

        # Add weights
        return self.calculate_weights(n_sl_levels, n_tp_levels)