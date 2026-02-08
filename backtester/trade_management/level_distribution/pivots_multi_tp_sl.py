class TradeLevelsCalculator:
    """
    Class to calculate pivot-based TP/SL levels with separate TP and SL level counts.
    """
    def __init__(self, strategy, n_tp_levels, n_sl_levels):
        """
        Initialize the TradeLevelsCalculator with separate TP and SL level counts.

        Parameters:
            strategy: The trading strategy instance.
            n_tp_levels (int): Number of take profit levels to generate.
            n_sl_levels (int): Number of stop loss levels to generate.
        """
        self.strategy = strategy
        self.n_tp_levels = n_tp_levels
        self.n_sl_levels = n_sl_levels

    def calculate_levels(self, n_tp_levels, n_sl_levels, direction):
        """
        Calculate the TP and SL levels based on pivot points and the direction of the trade.

        Parameters:
            direction (str): The trade direction ('buy' or 'sell').

        Returns:
            tuple: A tuple containing lists of SL levels and TP levels.
        """
        df = self.strategy.data.df
        entry = df['Close'].iloc[-1]

        daily_df = df.resample('D').agg({
            'High': 'max',
            'Low': 'min',
            'Close': 'last'
        }).dropna()

        if len(daily_df) < 2:
            raise ValueError("Insufficient data to compute pivot levels. Need at least two days of data.")

        # Previous completed day's data
        prev_day = daily_df.iloc[-2]
        prev_high = prev_day['High']
        prev_low = prev_day['Low']
        prev_close = prev_day['Close']

        # Calculate pivot point and ranges
        pp = (prev_high + prev_low + prev_close) / 3
        h_l_range = prev_high - prev_low

        # Calculate resistance and support levels up to R4 and S4
        r4 = pp + 3 * h_l_range
        s4 = pp - 3 * h_l_range

        if direction.lower() == 'buy':
            final_tp = r4
            final_sl = s4
            tp_distance = final_tp - entry
            sl_distance = entry - final_sl

            tp_step = tp_distance / self.n_tp_levels
            sl_step = sl_distance / self.n_sl_levels

            tp_levels = [round(entry + (i * tp_step), 5) for i in range(1, self.n_tp_levels + 1)]
            sl_levels = [round(entry - (i * sl_step), 5) for i in range(1, self.n_sl_levels + 1)]

        elif direction.lower() == 'sell':
            final_tp = s4
            final_sl = r4
            tp_distance = entry - final_tp
            sl_distance = final_sl - entry

            if tp_distance <= 0 or sl_distance <= 0:
                raise ValueError("For a sell trade, final TP must be below entry and final SL above entry.")

            tp_step = tp_distance / self.n_tp_levels
            sl_step = sl_distance / self.n_sl_levels

            tp_levels = [round(entry - (i * tp_step), 5) for i in range(1, self.n_tp_levels + 1)]
            sl_levels = [round(entry + (i * sl_step), 5) for i in range(1, self.n_sl_levels + 1)]

        else:
            raise ValueError("Direction must be 'buy' or 'sell'.")

        return sl_levels, tp_levels