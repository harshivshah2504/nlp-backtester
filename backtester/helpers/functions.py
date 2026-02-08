
from decimal import Decimal

from matplotlib import pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns




def generate_range(start, stop, step):
    if isinstance(start, int) and isinstance(stop, int) and isinstance(step, int):
        return list(range(start, stop, step))
    else:
        start = Decimal(start)
        stop = Decimal(stop)
        step = Decimal(step)
        num_steps = int((stop - start) / step) + 1
        return [start + step * i for i in range(num_steps)]
    
def generate_heatmap(heatmap):
    heatmap
    heatmap.sort_values().iloc[-3:]
    hm = heatmap.groupby(['n1', 'n2']).mean().unstack()
    sns.heatmap(hm[::-1], cmap='viridis')
    
def combine_dataframes(**kwargs):
    """
    Combine multiple DataFrames into one MultiIndex DataFrame.
    
    Parameters:
    **kwargs: Dictionary of DataFrames with keys as the asset names.
    
    Returns:
    DataFrame with MultiIndex columns (asset, OHLC/Volume).
    """
    combined_df = pd.concat(kwargs.values(), axis=1, keys=kwargs.keys())
    combined_df.ffill(inplace=True)  # Fill missing values with the last available value.
    if 'Ticker' in combined_df.columns.names:
        combined_df.columns = combined_df.columns.droplevel('Ticker')
    return combined_df