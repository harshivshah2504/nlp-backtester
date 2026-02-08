
import time, concurrent.futures, os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)
import pandas as pd
import os
import pyarrow.dataset as ds
from multiprocessing import Pool, cpu_count
from backtester.backtesting import Backtest
from bokeh.io import save, output_file
from datetime import datetime
import warnings
import uuid
import inspect
import numpy as np
from numba import njit, prange
import shutil
import pickle
import pyarrow.parquet as pq
import traceback
import yfinance as yf

'''
Data is fetched at once and then passed during multiprocessing for backtesting.
'''


@njit(parallel=True, fastmath=True)
def mark_trade_points_numba_optimized(entry_indices, exit_indices, sizes, exit_reasons, check_array):
    """
    Ultra-optimized function to mark trade entry and exit points.
    Eliminates unnecessary data conversion and uses direct array operations.
    """
    for i in prange(len(entry_indices)):
        entry_idx = entry_indices[i]
        exit_idx = exit_indices[i]
        size = sizes[i]
        exit_reason = exit_reasons[i]
        
        # Direct array access without bounds checking for speed
        # Mark entry bar
        if entry_idx >= 0:
            check_array[entry_idx] = 1 if size > 0 else -1
        
        # Mark exit bar
        if exit_idx >= 0 and exit_reason == 0 and check_array[exit_idx] == 0:
            check_array[exit_idx] = -1 if size > 0 else 1
    
    return check_array

@njit(fastmath=True)
def compare_dataframes_numba_optimized(full_values, cut_values, tolerance):
    """
    Ultra-optimized DataFrame comparison with minimal operations.
    """
    n = len(full_values)
    differences = np.zeros(n, dtype=np.bool_)
    
    for i in range(n):
        a, b = full_values[i], cut_values[i]
        
        # Fast NaN check
        if a != a and b != b:  # NaN check without np.isnan
            continue
        
        # Fast numerical comparison
        if a == a and b == b:  # Both are numbers
            if abs(a - b) > tolerance:
                differences[i] = True
        elif a != b:
            differences[i] = True
    
    return differences

@njit(fastmath=True)
def calculate_statistics_numba_optimized(data_array):
    """
    Ultra-optimized statistical calculations with single-pass operations.
    """
    n = len(data_array)
    if n == 0:
        return np.array([np.nan] * 9)
    
    # Fast NaN removal
    valid_mask = data_array == data_array  # Fast NaN check
    valid_data = data_array[valid_mask]
    n_valid = len(valid_data)
    
    if n_valid == 0:
        return np.array([np.nan] * 9)
    
    # Single-pass statistics calculation
    mean_val = np.sum(valid_data) / n_valid
    sorted_data = np.sort(valid_data)
    median_val = sorted_data[n_valid // 2] if n_valid % 2 == 1 else (sorted_data[n_valid // 2 - 1] + sorted_data[n_valid // 2]) / 2
    max_val = sorted_data[-1]
    min_val = sorted_data[0]
    
    # Fast variance calculation
    variance = np.sum((valid_data - mean_val) ** 2) / n_valid
    std_val = np.sqrt(variance)
    
    # Fast percentile calculations
    q90_idx = int(0.9 * n_valid)
    q75_idx = int(0.75 * n_valid)
    q50_idx = int(0.5 * n_valid)
    q25_idx = int(0.25 * n_valid)
    
    q90_avg = np.mean(sorted_data[q90_idx:])
    q75_avg = np.mean(sorted_data[q75_idx:])
    q50_avg = np.mean(sorted_data[q50_idx:])
    q25_avg = np.mean(sorted_data[q25_idx:])
    
    return np.array([mean_val, median_val, max_val, min_val, std_val, q90_avg, q75_avg, q50_avg, q25_avg])

@njit(fastmath=True)
def split_array_numba_optimized(data_length, n_chunks):
    """
    Ultra-optimized array splitting with minimal calculations.
    """
    chunk_size = (data_length + n_chunks - 1) // n_chunks  # Ceiling division
    chunk_starts = np.arange(n_chunks, dtype=np.int64) * chunk_size
    return chunk_starts

@njit(fastmath=True)
def filter_attributes_numba_optimized(attr_names, allowed_prefixes):
    """
    Ultra-optimized attribute filtering with vectorized operations.
    """
    n_attrs = len(attr_names)
    keep_mask = np.zeros(n_attrs, dtype=np.bool_)
    
    for i in range(n_attrs):
        attr_name = attr_names[i]
        for prefix in allowed_prefixes:
            if attr_name.startswith(prefix):
                keep_mask[i] = True
                break
    
    return keep_mask

@njit(parallel=True, fastmath=True)
def process_trades_batch_numba(trade_data, data_length):
    """
    Ultra-optimized batch trade processing for maximum speed.
    """
    n_trades = len(trade_data)
    check_array = np.zeros(data_length, dtype=np.int64)
    
    for i in prange(n_trades):
        entry_idx = int(trade_data[i, 0])  # Cast to int for array indexing
        exit_idx = int(trade_data[i, 1])   # Cast to int for array indexing
        size = trade_data[i, 2]
        exit_reason = trade_data[i, 3]
        
        # Mark entry bar
        if entry_idx >= 0:
            check_array[entry_idx] = 1 if size > 0 else -1
        
        # Mark exit bar
        if exit_idx >= 0 and exit_reason == 0 and check_array[exit_idx] == 0:
            check_array[exit_idx] = -1 if size > 0 else 1
    
    return check_array

@njit(fastmath=True)
def vectorized_statistics_numba(data_matrix):
    """
    Vectorized statistics calculation for multiple columns at once.
    """
    n_cols = data_matrix.shape[1]
    results = np.zeros((n_cols, 9))  # 9 statistics per column
    
    for col in range(n_cols):
        col_data = data_matrix[:, col]
        valid_mask = col_data == col_data  # Fast NaN check
        valid_data = col_data[valid_mask]
        
        if len(valid_data) == 0:
            results[col] = np.nan
            continue
        
        # Fast statistics
        mean_val = np.sum(valid_data) / len(valid_data)
        sorted_data = np.sort(valid_data)
        median_val = sorted_data[len(valid_data) // 2]
        max_val = sorted_data[-1]
        min_val = sorted_data[0]
        
        variance = np.sum((valid_data - mean_val) ** 2) / len(valid_data)
        std_val = np.sqrt(variance)
        
        # Percentiles
        q90_idx = int(0.9 * len(valid_data))
        q75_idx = int(0.75 * len(valid_data))
        q50_idx = int(0.5 * len(valid_data))
        q25_idx = int(0.25 * len(valid_data))
        
        results[col] = np.array([
            mean_val, median_val, max_val, min_val, std_val,
            np.mean(sorted_data[q90_idx:]),
            np.mean(sorted_data[q75_idx:]),
            np.mean(sorted_data[q50_idx:]),
            np.mean(sorted_data[q25_idx:])
        ])
    
    return results

class MultiBacktest:
    def __init__(self, strategy, * ,
                 cash: float = 10_000,
                 holding: dict = {},
                 commission: float = .0,
                 spread: float = .0,
                 margin: float = 1.,
                 trade_on_close=False,
                 hedging=False,
                 exclusive_orders=False,
                 trade_start_date=None,
                 lot_size=1,
                 fail_fast=True,
                 storage: dict | None = None,
                 is_option: bool = False,
                 equity_curve: bool = False,
                 load = 0.6,
                 bt_file: str = None,
                 stats_file: str = None,
                 look_ahead_bias: bool = False,
                 show_progress: bool = False,
                 database_name: str = 'bin'):

        """
        Takes as input the universe, timeframe and optional exchange name. 
        Fetches all datasets correspondingly, and thereafter runs the strategy on all 
        of them. Finally generates all tearsheets in the same directory of run.

        strategy, cash, commission forced as keyword arguments. 
        This allows exchange to be an optional parameter in the middle of the parameter list
        """
        stack = inspect.stack()
        caller_frame = stack[1]
        self.caller_filename = caller_frame.filename
        
        # Capture the actual code content at initialization time
        try:
            with open(self.caller_filename, 'r', encoding='utf-8') as source_file:
                self.caller_code_content = source_file.read()
        except Exception as e:
            print(f"Warning: Could not read caller file {self.caller_filename}: {e}")
            self.caller_code_content = None
            
        self.strategy = strategy
        self.cash = cash
        self.commission = commission
        self.spread = spread
        self.holding = holding
        self.margin = margin
        self.trade_on_close = trade_on_close
        self.hedging = hedging
        self.exclusive_orders = exclusive_orders
        self.trade_start_date = trade_start_date
        self.lot_size= lot_size
        self.fail_fast = fail_fast
        self.storage = storage
        self.is_option = is_option 
        self.equity_curve = equity_curve
        self.results = []
        self.num_processes = (int)(os.cpu_count()*load)
        self.show_progress = show_progress
        self.bt_file = bt_file
        self.stats_file = stats_file
        self.database_name = database_name

    def check_and_get_filepath(self, args):
        """
        Worker function that checks if a single file meets the criteria.
        Returns the full path if it matches, otherwise None.
        """
        filename, base_path, ticker, start_date = args
        
        if filename.startswith(f"{ticker}_") and filename.endswith(".parquet"):
            try:
                date_part = filename.split('_')[1].split('.')[0]
                if date_part >= start_date:
                    return os.path.join(base_path, filename)
            except IndexError:
                return None
        return None

    def fetch_data(self, ticker: str, start_date: str, end_date: str = None, 
                   chunk_months: int = 6, max_retries: int = 3, 
                   base_delay: float = 2.0) -> pd.DataFrame:
        """
        Fetches daily OHLC data from Yahoo Finance for the given ticker and date range.
        Uses chunking to avoid rate limiting for large date ranges.
        
        Args:
            ticker: Stock ticker symbol (e.g., 'MSFT', 'AAPL')
            start_date: Start date in YYYYMMDD format (e.g., '20250101')
            end_date: End date in YYYYMMDD format (e.g., '20251231'). If None, uses today's date.
            chunk_months: Number of months per chunk (default 6). Smaller = less rate limiting risk.
            max_retries: Maximum number of retries per chunk on failure (default 3).
            base_delay: Base delay in seconds between retries, doubles with each retry (default 2.0).
        
        Returns:
            DataFrame with OHLC data indexed by datetime
        """
        try:
            from dateutil.relativedelta import relativedelta
            
            # Parse start_date from YYYYMMDD format
            start_dt = datetime.strptime(start_date, '%Y%m%d')
            
            # Parse end_date or use today
            if end_date:
                end_dt = datetime.strptime(end_date, '%Y%m%d')
            else:
                end_dt = datetime.now()
            
            print(f"Fetching data for {ticker} from Yahoo Finance...")
            print(f"Date range: {start_dt.strftime('%Y-%m-%d')} to {end_dt.strftime('%Y-%m-%d')}")
            
            # Generate date chunks
            chunks = []
            current_start = start_dt
            while current_start < end_dt:
                current_end = min(current_start + relativedelta(months=chunk_months), end_dt)
                chunks.append((current_start, current_end))
                current_start = current_end
            
            total_chunks = len(chunks)
            print(f"Splitting request into {total_chunks} chunk(s) of ~{chunk_months} months each")
            
            # Fetch each chunk with retry logic
            all_data = []
            for i, (chunk_start, chunk_end) in enumerate(chunks, 1):
                chunk_df = self._fetch_chunk_with_retry(
                    ticker, chunk_start, chunk_end, 
                    chunk_num=i, total_chunks=total_chunks,
                    max_retries=max_retries, base_delay=base_delay
                )
                if not chunk_df.empty:
                    all_data.append(chunk_df)
                
                # Small delay between chunks to be respectful of rate limits
                if i < total_chunks:
                    time.sleep(0.5)
            
            if not all_data:
                print(f"No data available for ticker '{ticker}' in the specified date range.")
                return pd.DataFrame()
            
            # Combine all chunks
            df = pd.concat(all_data)
            
            # Handle multi-level columns if present (yfinance sometimes returns multi-index)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            
            # Ensure column names are correct
            df = df.rename(columns={
                'open': 'Open',
                'high': 'High',
                'low': 'Low',
                'close': 'Close',
                'volume': 'Volume',
                'adj close': 'Adj Close'
            })
            
            # Ensure we have the required columns
            required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
            for col in required_cols:
                if col not in df.columns:
                    print(f"Warning: Missing column '{col}' in fetched data")
            
            # Remove any duplicate indices and sort
            df = df[~df.index.duplicated(keep='last')]
            df = df.sort_index()
            
            print(f"Successfully fetched {len(df)} rows of data for {ticker}")
            return df
            
        except Exception as e:
            print(f"Error fetching data from Yahoo Finance: {e}")
            traceback.print_exc()
            return pd.DataFrame()
    
    def _fetch_chunk_with_retry(self, ticker: str, start_dt: datetime, end_dt: datetime,
                                 chunk_num: int, total_chunks: int,
                                 max_retries: int = 3, base_delay: float = 2.0) -> pd.DataFrame:
        """
        Fetches a single chunk of data with exponential backoff retry logic.
        
        Args:
            ticker: Stock ticker symbol
            start_dt: Start datetime for this chunk
            end_dt: End datetime for this chunk
            chunk_num: Current chunk number (for logging)
            total_chunks: Total number of chunks (for logging)
            max_retries: Maximum number of retry attempts
            base_delay: Base delay in seconds, doubles with each retry
        
        Returns:
            DataFrame with OHLC data for this chunk, or empty DataFrame on failure
        """
        for attempt in range(max_retries):
            try:
                print(f"  Fetching chunk {chunk_num}/{total_chunks}: "
                      f"{start_dt.strftime('%Y-%m-%d')} to {end_dt.strftime('%Y-%m-%d')}"
                      f"{f' (attempt {attempt + 1})' if attempt > 0 else ''}")
                
                df = yf.download(
                    ticker,
                    start=start_dt.strftime('%Y-%m-%d'),
                    end=end_dt.strftime('%Y-%m-%d'),
                    interval='1d',
                    progress=False
                )
                
                if df.empty:
                    print(f"    No data for this chunk (might be a weekend/holiday period)")
                    return pd.DataFrame()
                
                print(f"    Retrieved {len(df)} rows")
                return df
                
            except Exception as e:
                error_msg = str(e).lower()
                
                # Check if it's a rate limit error
                is_rate_limit = any(keyword in error_msg for keyword in 
                                   ['rate limit', 'too many requests', '429', 'throttl'])
                
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)  # Exponential backoff
                    if is_rate_limit:
                        delay *= 2  # Extra delay for rate limit errors
                        print(f"    Rate limited! Waiting {delay:.1f}s before retry...")
                    else:
                        print(f"    Error: {e}. Retrying in {delay:.1f}s...")
                    time.sleep(delay)
                else:
                    print(f"    Failed after {max_retries} attempts: {e}")
                    return pd.DataFrame()



    def backtest_stock(self, stock, start_date, end_date=None, **kwargs):

        data = self.fetch_data(stock, start_date, end_date)
        if len(data) == 0:
            print("No data available for the given specifications")
            return
        print("Data fetched")
        bt = Backtest(data, self.strategy,
                    cash = self.cash,
                    commission = self.commission,
                    spread = self.spread,
                    holding = self.holding,
                    margin = self.margin,
                    trade_on_close = self.trade_on_close,
                    hedging = self.hedging,
                    exclusive_orders = self.exclusive_orders,
                    trade_start_date = self.trade_start_date,
                    lot_size= self.lot_size,
                    fail_fast = self.fail_fast,
                    storage = self.storage,
                    is_option = self.is_option
                    )
        result = bt.run(show_progress=self.show_progress, **kwargs)
        fig = bt.plot()
        output_file(self.bt_file, title="Backtest Plot")
        save(fig)
        with open(self.stats_file, "wb") as f:
            temp_result = result.copy() if hasattr(result, 'copy') else dict(result)
            if isinstance(temp_result, (dict,)):
                temp_result.pop('_strategy', None)
            elif hasattr(temp_result, 'drop'):
                temp_result = temp_result.drop(labels=['_strategy'], errors='ignore')
            pickle.dump(temp_result, f)
        result["_equity_curve"]["Date"] = result["_equity_curve"].index
        result['strategy_name'] = self.strategy.__name__ if self.strategy else None
        strategy_instance = bt._results._strategy
        result['rm_name'] = strategy_instance.risk_management_strategy.__class__.__name__ if hasattr(strategy_instance, 'risk_management_strategy') and strategy_instance.risk_management_strategy else None
        result['tm_name'] = strategy_instance.trade_management_strategy.__class__.__name__ if hasattr(strategy_instance, 'trade_management_strategy') and strategy_instance.trade_management_strategy else None

        print("Backtest finished")
        return result
    


    