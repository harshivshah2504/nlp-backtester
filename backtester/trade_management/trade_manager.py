import os
import sys
from typing import List, Tuple, Optional

parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

class TradeManager:
    def __init__(self, 
                 trade_management_strategy,  
                 level_distribution_model=None,  
                 weight_distribution_model=None,
                 n_tp_levels: int = None,
                 n_sl_levels: int = None):
        """Initialize TradeManager with custom TP/SL and Level Distribution models."""
        self.trade_management_strategy = trade_management_strategy  
        self.level_distribution_model = level_distribution_model
        self.weight_distribution_model = weight_distribution_model
        self.n_tp_levels = n_tp_levels
        self.n_sl_levels = n_sl_levels

    def calculate_tp_sl_levels(self, direction):
        """Calculate TP/SL levels using both single and multi-level models."""
        stop_loss, take_profit = self.trade_management_strategy.calculate_tp_sl(direction)
        
        if self.level_distribution_model and self.n_tp_levels and self.n_sl_levels:
            sl_levels, tp_levels = self.level_distribution_model.calculate_levels(
                self.n_tp_levels,  
                self.n_sl_levels,  
                direction
            )
            return sl_levels, tp_levels
        
        return [stop_loss], [take_profit]

    def calculate_weighted_tp_sl_levels(self, direction):
        """Calculate weighted TP/SL levels by combining single and multi-level models."""
        sl_levels, tp_levels = self.calculate_tp_sl_levels(direction)
        
        if self.weight_distribution_model:
            return self.weight_distribution_model.calculate_weights(sl_levels, tp_levels)
        
        
        print("tp levels: ", tp_levels)
        print("sl levels: ", sl_levels)
        return sl_levels, tp_levels
    
