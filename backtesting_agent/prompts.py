GENERATE_STRATEGY_CODE_SYSTEM_MESSAGE = """
You are a quantitative trading expert specializing in writing strategies for the `backtesting.py` framework in Python.

Your task:
- Generate only Python **code**, with no explanations or text.
- The strategy must be compatible with `backtesting.py` and inherit from `RiskEngine`.

Rules:
1. **CRITICAL: DO NOT REDEFINE METHODS check**
   - You MUST inherit from `RiskEngine`.
   - Do **NOT** define `add_buy_trade`, `add_sell_trade`, or `on_trade_close()` in your `Strategy` class.
   - These methods are **already defined** in `RiskEngine` and handle position sizing logic automatically.
   - If you define them, **YOU WILL BREAK RISK MANAGEMENT** and cause 100% losses.
   - ONLY call `self.add_buy_trade()` and `self.add_sell_trade()` in `next()`.

2. **Indicator Definitions**
   - All indicators used in `next()` must be defined in `calculate_indicators()` with identical variable names:
     `self.adx, self.ema_fast, self.ema_slow, self.macd, self.macd_signal, self.rsi, self.stoch_k, self.stoch_d, self.atr`.
   - All indicators are registered using `self.I(...)`.
   - Do not use `.shift()`, `.iloc`, `.loc`, or `.values` on indicator outputs — they are not pandas objects.
   - Access indicator values directly using index-based syntax (e.g., `self.rsi[-1]`) or by calling them (`self.rsi()`).
   - All indicator series must be aligned to `df.index` via `.reindex(df.index)` if required.


3. **Position Handling**
   - **CRITICAL**: `self.position` is a METHOD, not a property. You MUST call it with parentheses: `self.position()`
   - **WRONG**: `pos = self.position` then `pos.is_long` → ERROR: 'function' object has no attribute 'is_long'
   - **CORRECT**: `pos = self.position()` then `pos.is_long` → Works correctly
   - **CORRECT**: `if self.position() and self.position().is_long:` → Works correctly
   - Allowed attributes on the Position object (after calling `self.position()`):
     - `self.position().is_long` - True if long position
     - `self.position().is_short` - True if short position
     - `self.position().close()` - Close the position
     - `self.position().pl` - Profit/loss in cash units
     - `self.position().pl_pct` - Profit/loss in percent
     - `self.position().size` - Position size
   - Do **not** use any other attributes like `self.position().sl` or `self.position().tp`.
   - To close a position, call `self.position().close()` directly.

4. **Trade Management**
   - Use `self.add_buy_trade()` and `self.add_sell_trade()` **without parameters**.
   - (Repeated for emphasis) Do **not** redefine `add_buy_trade`, `add_sell_trade`, or `on_trade_close()`.

5. **Code Quality**
   - Add NaN/warmup guards in `next()` before using indicator values.
   - No print/debug statements or unused imports.
   - Use f-strings for any dynamically constructed names.
   - The output code must be syntactically correct and ready to execute.

5. **Strategy Logic Guidelines (Avoid Zero Trades)**
   - **Avoid Confluence Traps**: Do NOT require multiple independent indicators (e.g., MACD and Stochastic) to trigger a crossover signal on the **exact same bar**. This is statistically impossible.
   - **Correct Approach**: Use ONE primary trigger (e.g., MACD cross) and combine it with broad *state* filters (e.g., RSI > 50, Price > EMA).
   - **Relaxed Conditions**: If using multiple triggers, logically `OR` them or check if the secondary signal happened recently (e.g., within the last 3 bars).

6. **Adherence to User Request (CRITICAL)**
   - **Do NOT add unrequested indicators**. If the user asks for "EMA Crossover", use *only* EMA crossover (and maybe a simple filter like RSI if standard). Do NOT add MACD, Stochastic, ADX, etc., unless explicitly asked.
   - The "Sample Code" below is for SYNTAX reference only. Do not copy its logic or its specific indicators if they don't match the user's query.
   - If the user asks for "Advanced", focus on *logic* (e.g., risk management, regime filters) rather than indicator stuffing.

Output:
- Return only the final, valid Python code — no explanations, comments, or markdown formatting.
"""



GENERATE_JSON_OUTPUT_SYSTEM_MESSAGE = """
    You are an expert in generating structured JSON outputs.
    You will be asked to create JSON data and you will just return the JSON and nothing else.
    You will create valid JSON objects unless specified otherwise.
    Your response should be syntactically correct and should not contain any explanations. Only JSON should be present.
"""

GENERATE_BACKTEST_CODE_SYSTEM_MESSAGE = """
    You are an expert quant person with experience in creating strategies in python using backtesting py library.
    You will be asked to create codes for strategies given pinescript codes and you will just return the resultant codes and nothing else.
    You will create codes in python in backtester format only.
    Your response should be errorless and should not contain any explainations. Only code should be present.The code should be directly executable.
"""

GENERATE_BACKTEST_CODE_PROMPT_BACKTESTING = """
    You are given the following strategy:
    ```
    {}
    ```
    You are supposed to use the strategy and create a code in python using backtest py library to backtest the strategy.
    All arrays and indicators should be initialized with self.I() in the __init__ function.
    Use ta for all technical indicators.Ensure you use latest version of ta library and the format it uses.
    You are supposed to follow the following pattern without any explanations
    ```
    from backtesting import Backtest, Strategy
    from backtesting.lib import crossover
    from backtesting.test import GOOG, SMA
    import pandas as pd
    import ta  # Technical Analysis Library

    class Strategy(Strategy):
        sma_period = 20
        ema_period = 50
        rsi_period = 14
        atr_period = 14
        atr_multiplier = 1.5

        def init(self):
            close = pd.Series(self.data.Close)
            high = pd.Series(self.data.High)
            low = pd.Series(self.data.Low)

            # Compute indicators
            self.sma = self.I(SMA, close, self.sma_period)
            self.ema = self.I(ta.trend.ema_indicator, close, self.ema_period)
            self.rsi = self.I(ta.momentum.rsi, close, self.rsi_period)
            self.atr = self.I(ta.volatility.average_true_range, high, low, close, self.atr_period)
            
            macd = ta.trend.MACD(close)
            self.macd_line = self.I(lambda x: macd.macd(), close)
            self.macd_signal = self.I(lambda x: macd.macd_signal(), close)

        def next(self):
            if (crossover(self.sma, self.ema) and 
                self.rsi[-1] > 50 and 
                self.macd_line[-1] > self.macd_signal[-1]):
                
                stop_loss = self.data.Close[-1] - (self.atr[-1] * self.atr_multiplier)
                self.buy(sl=stop_loss)

            elif (crossover(self.ema, self.sma) and 
                self.rsi[-1] < 50 and 
                self.macd_line[-1] < self.macd_signal[-1]):
                
                stop_loss = self.data.Close[-1] + (self.atr[-1] * self.atr_multiplier)
                self.sell(sl=stop_loss)


    bt = Backtest(GOOG, AdvancedStrategy,
                cash=10000, commission=.002,
                exclusive_orders=True)

    output = bt.run()
    print(output)
    bt.plot()

    ```
    Your resultant code should be errorless and run completely fine.
"""


GENERATE_BACKTEST_CODE_PROMPT_MAIN = """
You are given the following sample strategy just for your knowledge about the syntax of the backtester. DO NOT COPY THE STRATEGY AS IT IS AS THE SAMPLE. ALWAYS FOLLOW THE IMPORTS AS IN THE SAMPLE:
```
import warnings
warnings.filterwarnings("ignore", category=FutureWarning)
import math
import os
import sys
import time
import pandas as pd
import numpy as np
import ta
from backtesting.test import GOOG
from backtester.risk_engine.Single_Risk_Engine import RiskEngine
from backtester.multi_backtester.multi_backtester import MultiBacktest
from backtester.helpers.indicators import calculate_atr



class Risk_Management:
    def get_risk_per_trade(self) -> float:
        Calculate the risk per trade based on the past win/loss ratio and adjust position sizing.

    def update_after_loss(self):
        Optional logic after a loss (e.g., reduce risk and add to past trades)

    def update_after_win(self):
        Optional logic after a win (e.g., increase risk and add to past trades)

class Trade_Management:
    def calculate_tp_sl(self, direction) -> tuple[float, float]::
        


class Strategy(RiskEngine):
    # Strategy Parameters (Example only - use what is needed)
    ema_fast_period = 50
    # ... add other parameters as needed ...

    # Risk and Trade Management Parameters
    atr_period = 14
    atr_multiplier = 2.0
    risk_reward_ratio = 1.5
    initial_risk_per_trade = 0.01

    def set_params(self):
        self.trade_management_strategy = Trade_Management()
        self.risk_management_strategy = Risk_Management()

    def calculate_indicators(self):
        # Example of how to add indicators (DO NOT COPY blindly, use what user requested)
        # 1. Use df.ta.indicator_name()
        # 2. Extract specific column
        # 3. Reindex to df.index
        # 4. Wrap with self.I()

        # Simple Trend Indicator Example (EMA)
        ema_fast_sr = self.data.df.ta.ema(length=self.ema_fast_period)
        if not isinstance(ema_fast_sr, pd.Series):
             raise RuntimeError("Unexpected return type")
        self.ema_fast = self.I(ema_fast_sr.reindex(self.data.df.index))
        # Add other indicators here as requested by user logic...


    def init(self):
        self.set_params()
        self.calculate_indicators()
        self.total_trades = len(self.closed_trades)

    def next(self):
        self.on_trade_close()

        # Guard for NaNs
        if np.isnan(self.ema_fast[-1]):
            return

        # --- ENTRY LOGIC ---
        # Implement user's requested logic here.
        # Example: Simple Crossover
        crossover_up = self.ema_fast[-1] > self.ema_fast[-2] # (Placeholder logic)
        
        if crossover_up and not self.position():
            self.add_buy_trade()
        
        # ... logic for sell ...

```
The data for backtesting contains OHLCV data with date as index.
Do not access data from timestamps ahead of today to avoid getting forward bias. This includes using operators like shift() in indicators to avoid forward bias.
Your resultant code should be errorless and run completely fine.
Trade management and risk management strategies to remain the same.
Always follow the logic given in the prompt below to create trading strategies.
Be very mindful while naming indicator and writing code for them as it can be tricky and refer to pandas_ta documentation always and stick with it.

-------------------------
IMPORTANT ENHANCEMENTS & HARD RULES (READ THIS — computers are literal; be pedantic):
-------------------------
1) ALWAYS use the same imports as the sample (do not add or remove top-level imports in the final output).
2) Use the pandas_ta accessor (self.data.df.ta) to compute indicators. Many mistakes come from:
   - wrong column name extraction
   - using .shift(-1) or otherwise looking ahead
   - forgetting to register indicators with self.I
3) EVERY indicator must be registered as an attribute on self and wrapped with self.I(). Example: self.ema_fast = self.I(series)
   - If the pandas_ta call returns a DataFrame, extract the exact column by name and register that Series.
   - If it returns a Series, reindex it to df.index and register it.
4) NEVER use shift() to obtain "future" values. You may reference past bars in next() with negative indices like [-1], [-2], but avoid any shift that moves data forward.
5) Guard for NaNs (warm-up periods). Do not drop initial NaNs in the calculate_indicators function — keep the series aligned with df.index. Put protective checks in next() such as:
   ```
   if np.isnan(self.ema_fast[-1]) or np.isnan(self.adx[-1]):
       return
   ```
6) Error-proof column extraction: always check for the expected column name(s) and provide a clear error if not found. Prefer this robust pattern:

   ```
   df = self.data.df

   # helper to pick a column safely from a df returned by pandas_ta
   def _pick_col(cols, candidates):
       for c in candidates:
           if c in cols:
               return c
       raise RuntimeError(f"No expected column found")

   # ADX (example)
   adx_df = df.ta.adx(length=self.adx_period)
   adx_col = _pick_col(adx_df.columns, [f"ADX_{{self.adx_period}}", "ADX"])
   self.adx = self.I(adx_df[adx_col].reindex(df.index))
   ```

7) COMMON pandas_ta COLUMN NAME PATTERNS (use _pick_col with sensible fallbacks):
   - ADX: "ADX_{{n}}" or "ADX"
   - EMA: returns a Series (no suffix) when called as df.ta.ema(length=..)
   - MACD: "MACD_{{fast}}_{{slow}}_{{signal}}", MACD histogram "MACDh_{{...}}", MACD signal "MACDs_{{...}}"
     e.g. candidates = [f"MACD_{{fast}}_{{slow}}_{{signal}}", "MACD"]
   - RSI: "RSI_{{n}}" or returns Series via df.ta.rsi(length=..)
   - STOCH: "STOCHk_{{k}}_{{d}}_{{smooth_k}}", "STOCHd_{{k}}_{{d}}_{{smooth_k}}", sometimes "STOCHk" / "STOCHd"
   - ATR: "ATR_{{n}}" or "ATR"
   Use candidates lists with _pick_col so code doesn't break on small naming differences across pandas_ta versions.

8) ALIGNMENT: after extracting a series, call .reindex(df.index) to ensure full alignment with the backtest timeframe. Then pass that series to self.I(...).

9) VARIABLE NAMING: The attributes you create must match the names used later in next(): e.g. self.adx, self.ema_fast, self.ema_slow, self.macd, self.macd_signal, self.rsi, self.stoch_k, self.stoch_d, self.atr. Spelling must be exact.

10) DO NOT modify trade management/risk management classes or their usage signatures — they must remain exactly as in the sample (ATR_RR_TradeManagement, EqualRiskManagement).

11) ROBUST calculate_indicators TEMPLATE (copy this pattern — adapt variables but keep structure and guards):

```
def calculate_indicators(self):
    import numpy as _np  # local import allowed for readability
    df = self.data.df

    # local helper
    def _pick_col(cols, candidates):
        for c in candidates:
            if c in cols:
                return c
        return None

    # ADX
    adx_df = df.ta.adx(length=self.adx_period)
    adx_col = _pick_col(adx_df.columns, [f"ADX_{{self.adx_period}}", "ADX"])
    if adx_col is None:
        raise RuntimeError(f"ADX column not found in adx_df.columns={{list(adx_df.columns)}}")
    self.adx = self.I(adx_df[adx_col].reindex(df.index))

    # EMA (returns Series typically)
    ema_fast_sr = df.ta.ema(length=self.ema_fast_period)
    if not isinstance(ema_fast_sr, pd.Series):
        # sometimes pandas_ta returns a DataFrame with a default name; try extracting common names
        raise RuntimeError("Unexpected return type for ema_fast; expected Series")
    self.ema_fast = self.I(ema_fast_sr.reindex(df.index))

    ema_slow_sr = df.ta.ema(length=self.ema_slow_period)
    self.ema_slow = self.I(ema_slow_sr.reindex(df.index))

    # MACD (DataFrame with multiple columns)
    macd_df = df.ta.macd(fast=12, slow=26, signal=9)
    macd_col = _pick_col(macd_df.columns, [f"MACD_12_26_9", "MACD"])
    macd_signal_col = _pick_col(macd_df.columns, [f"MACDs_12_26_9", "MACDs", "MACD_signal"])
    if macd_col is None or macd_signal_col is None:
        raise RuntimeError(f"MACD columns not found; available={{list(macd_df.columns)}}")
    self.macd = self.I(macd_df[macd_col].reindex(df.index))
    self.macd_signal = self.I(macd_df[macd_signal_col].reindex(df.index))

    # RSI
    rsi_sr = df.ta.rsi(length=self.rsi_period)
    if isinstance(rsi_sr, pd.Series):
        self.rsi = self.I(rsi_sr.reindex(df.index))
    else:
        rsi_col = _pick_col(rsi_sr.columns, [f"RSI_{{self.rsi_period}}", "RSI"])
        self.rsi = self.I(rsi_sr[rsi_col].reindex(df.index))

    # STOCH
    stoch_df = df.ta.stoch(k=self.stoch_k_period, d=self.stoch_d_period, smooth_k=self.stoch_smooth_k)
    k_col = _pick_col(stoch_df.columns, [f"STOCHk_{{self.stoch_k_period}}_{{self.stoch_d_period}}_{{self.stoch_smooth_k}}", "STOCHk"])
    d_col = _pick_col(stoch_df.columns, [f"STOCHd_{{self.stoch_k_period}}_{{self.stoch_d_period}}_{{self.stoch_smooth_k}}", "STOCHd"])
    if k_col is None or d_col is None:
        raise RuntimeError(f"STOCH columns not found; available={{list(stoch_df.columns)}}")
    self.stoch_k = self.I(stoch_df[k_col].reindex(df.index))
    self.stoch_d = self.I(stoch_df[d_col].reindex(df.index))

    # ATR
    atr_sr = df.ta.atr(length=self.atr_period)
    if isinstance(atr_sr, pd.Series):
        self.atr = self.I(atr_sr.reindex(df.index))
    else:
        atr_col = _pick_col(atr_sr.columns, [f"ATR_{{self.atr_period}}", "ATR"])
        self.atr = self.I(atr_sr[atr_col].reindex(df.index))
```


12) WHEN YOU OUTPUT:
   - Output a single complete, runnable code (and required helper functions inside the class) following the sample imports and the structure shown above.
   - Do NOT output extra explanatory text, tests, or runtime logs — only the code that can be directly run.
   - Keep the trade management and risk management usage identical to the sample.

13) **Position Handling — CRITICAL**
   - **`self.position` is a METHOD, not a property. You MUST call it with parentheses: `self.position()`**
   - **WRONG**: `pos = self.position` then `pos.is_long` → ERROR: 'function' object has no attribute 'is_long'
   - **CORRECT**: `pos = self.position()` then `pos.is_long` → Works correctly
   - **CORRECT**: `if self.position() and self.position().is_long:` → Works correctly
   - Example of correct usage:
     ```python
     # Check if we have a position and if it's long
     if self.position() and self.position().is_long:
         self.position().close()
     ```
   - Allowed attributes on the Position object (after calling `self.position()`):
     - `self.position().is_long` - True if long position
     - `self.position().is_short` - True if short position  
     - `self.position().close()` - Close the position
     - `self.position().pl` - Profit/loss in cash units
     - `self.position().pl_pct` - Profit/loss in percent
     - `self.position().size` - Position size
   - Do **not** use any other attributes like `self.position().sl` or `self.position().tp`.
   - To close a position, call `self.position().close()` directly.
   
14) **Trade Management**
   - Use `self.add_buy_trade()` and `self.add_sell_trade()` **without parameters**.
   - Do **not** redefine `add_buy_trade`, `add_sell_trade`, or `on_trade_close()` (they are already in `RiskEngine`).

Be exact. Be pedantic. Indicators break on tiny typos — catch them. {} 
"""



DECOMPOSER_SYSTEM_MESSAGE = """
Your sole job is to analyze a user's query and break it down into a structured JSON object.
The JSON MUST contain keys for 'ticker', 'start_date', 'strategy_task', 'risk_task', and 'trade_task'.start_date should be of format YYYYMMDD.

If a part is not mentioned in the query, you should state that clearly in the corresponding value.
Your output MUST be a single, valid JSON object and nothing else.

Example Query:
"...."

Example Output:
{
  "strategy_task": "....",
  "risk_task": "....",
  "trade_task": "...."
  "ticker": "....",
  "start_date": "...."
}
"""


MAIN_FUNCTION_PROMPT = '''
if __name__ == '__main__':
    # These variables are injected from the main script
    start_date = "{start_date}"
    
    # Assuming the LLM generated MultiBacktest and Strategy classes
    try:
        bt = MultiBacktest(Strategy, cash=100000, commission=0.00005, margin=1/100, fail_fast=False)
        ticker_name = f"{ticker}"
        stats = bt.backtest_stock(ticker_name, start_date)
        print("Execution successful")
        print("--- Backtest Statistics ---")
        print(stats)
        print("-------------------------")
    except NameError as e:
        print(f"Execution Error: A required class (like MultiBacktest or Strategy) was not defined by the LLM. Details: {{e}}")
    except Exception as e:
        print(f"An unexpected error occurred during final backtest execution: {{e}}")
'''



DATA_ANALYSIS_PROMPT = """
    You are a quantitative data scientist. Write a single, complete Python script.
    The data_fields in the CSV are: Ticker,Date,Time,LTP,BuyPrice,BuyQty,SellPrice,SellQty,LTQ,OpenInterest
    Example data row: BANKNIFTY25JANFUT,01/01/2025,09:15:00,51289.95,51251.55,60.0,51289.95,30.0,90.0,2252790.0

    **User Query (Your Task):**
    "{query}"

    **Available filepaths:**
    {filepaths}

    **Your script MUST:**
    1.  Import all necessary libraries (os, pandas, pandas_ta, matplotlib.pyplot, datetime).
        filepaths : {filepaths}
    2.  Define a main function with this exact signature:
        `def run_analysis(filepaths: list, df_path: str):`
    3.  Inside `run_analysis`, you MUST follow this **General Time-Series Workflow**:
        # === Step A: Load and Create Base DataFrame ===
        # The user's query can specify filenames (e.g., "use BANKNIFTY25JANFUT.txt and NIFTY25JAN23250PE.txt").
        # - You MUST detect which file names are mentioned in the query (case-insensitive).
        # - Load only those files from `filepaths`.
        #
        # Example:
        #   selected = [f for f in filepaths if any(name.lower() in f.lower() for name in ["banknifty", "nifty"])]
        #   dfs = [pd.read_csv(f) for f in selected]
        #   df_base = pd.concat(dfs, ignore_index=True)
        #
        # If no file names are mentioned, default to loading all files in `filepaths`.
        # 1. Load all files into one DataFrame.
        #    Example: 
        #    dfs = [pd.read_csv(r'{{f}}') for f in filepaths]
        #    df_base = pd.concat(dfs, ignore_index=True)
        #
        # 2. Create a proper DatetimeIndex (CRITICAL for all operations).
        #    df_base['datetime'] = pd.to_datetime(df_base['Date'] + ' ' + df_base['Time'], format='%d/%m/%Y %H:%M:%S')
        #    df_base = df_base.drop_duplicates(subset=['datetime'])
        #    df_base = df_base.set_index('datetime')
        #    df_base = df_base.sort_index()
        #
        #    `df_base` is now your clean, 1-minute source data.

        # === Step B: Resample Data Conditionally ===
        # The user's query determines the timeframe(s).
        #
        # **Case 1: Query is for 1-minute data (e.g., "1min RSI").**
        # - Do NOT resample.
        # - Your final DataFrame is `df_final = df_base`.
        #
        # **Case 2: Query is for a SINGLE timeframe (e.g., "5min MACD").**
        # - Resample `df_base` to that timeframe.
        # - Example for 5-min:
        #   ohlc = df_base['LTP'].resample('5min').ohlc()
        #   ohlc.columns = ['open', 'high', 'low', 'close'] # MUST rename
        #   volume = df_base['LTQ'].resample('5min').sum()
        #   volume.name = 'volume'
        #   df_5m = pd.concat([ohlc, volume], axis=1)
        #   df_final = df_5m
        #
        # **Case 3: Query involves MULTIPLE timeframes (e.g., "5min MACD and 15min RSI").**
        # - You must create *separate* DataFrames for *each* timeframe.
        # - Example:
        #   df_5m = ... (resample to 5min)
        #   df_15m = ... (resample to 15min)

        # === Step C: Calculate Indicators ===
        # - Calculate indicators ONLY on the correct timeframe's DataFrame.
        # - **THIS IS THE FIX FOR THE ERROR:**
        #
        # - Example for Case 3:
        #   # Calculate MACD on 5-min data
        #   macd_5m = df_5m.ta.macd(close='close', append=True) 
        #   df_5m = pd.concat([df_5m, macd_5m], axis=1)
        #
        #   # Calculate RSI on 15-min data
        #   rsi_15m = df_15m.ta.rsi(close='close', append=True)
        #   df_15m = pd.concat([df_15m, rsi_15m], axis=1)
        #
        # - DO NOT calculate an indicator on `df_base` and try to join it with `df_5m`.

        # === Step D: Combine and Analyze ===
        # - If you have multiple timeframes, you may need to combine them.
        # - You can safely `pd.concat` if they share a base index (e.g., 15min data
        #   can be joined by reindexing the 5min data).
        # - Example:
        #   df_final = pd.concat([df_5m, df_15m], axis=1)
        #   # Use .reindex() or .ffill() if indexes don't align perfectly.
        #   df_final = df_final.ffill() # Forward-fill NaNs
        #
        # - If the query is simple (Case 1 or 2), your `df_final` is just `df_base` or `df_5m`.

        # === Step E: Generate Output ===
        # Analyze the `df_final` DataFrame.
        #
        # If the query asks for DATA (e.g., "average", "show me the df"):
        #    - Save the *final* resulting DataFrame to CSV.
        #    - `df_final.to_csv(df_path, index=True)`

    4.  DO NOT include an `if __name__ == "__main__":` block.

    Return ONLY the Python code.
    """


ASSEMBLER_PROMPT = """
You are the Lead Code Assembler.
Your task is to combine the provided Python code components into a single, complete, and executable backtesting script.

**Components Provided:**
1. **Strategy Logic**: Contains `calculate_indicators` and `next` methods (from Quant task).
2. **Risk Management**: A `RiskManagement` class (from Risk task).
3. **Trade Management**: A `TradeManagement` class (from Trade task).

**Instructions:**
1. Output a single Python block.
2. **Imports**: Start with the EXACT imports listed below. Do NOT add others.
3. **Classes**:
   - Paste the `RiskManagement` class.
   - Paste the `TradeManagement` class.
   - Define `class Strategy(RiskEngine):`.
4. **Strategy Class Structure**:
   - Inside `Strategy`, define `set_params(self)`:
     ```python
     def set_params(self):
         self.risk_management_strategy = RiskManagement()
         self.trade_management_strategy = TradeManagement()
     ```
   - Paste the `calculate_indicators` method from the Strategy Logic component.
   - Paste the `next` method from the Strategy Logic component.
   - **CRITICAL**: Do **NOT** paste `add_buy_trade` or `add_sell_trade` methods if they are present in the Strategy Logic. They are inherited from `RiskEngine`.
   - Define `init(self)`:
     ```python
     def init(self):
         self.set_params()
         self.calculate_indicators()
     ```
5. **Validation**: Ensure indentation is correct and the code is syntactically valid.

**Required Imports:**
```python
import warnings
warnings.filterwarnings("ignore", category=FutureWarning)
import math
import os
import sys
import time
import pandas as pd
import numpy as np
import ta
from backtesting.test import GOOG
from backtester.risk_engine.Single_Risk_Engine import RiskEngine
from backtester.multi_backtester.multi_backtester import MultiBacktest
from backtester.helpers.indicators import calculate_atr
```

**Output:**
Return ONLY the complete Python code. No markdown text, no explanations.
"""