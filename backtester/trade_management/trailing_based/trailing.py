from backtester.backtesting import Backtest, Strategy
import numpy as np
import pandas as pd



class TrailingStrategy(Strategy):
    """
    A strategy with automatic trailing stop-loss, trailing the current
    price at distance of some multiple of average true range (ATR). Call
    `TrailingStrategy.set_trailing_sl()` to set said multiple
    (`6` by default). See [tutorials] for usage examples.

    """
    __n_atr = 6.
    __atr = None

    def init(self):
        super().init()
        self.set_atr_periods()

    def set_atr_periods(self, periods: int = 100):
        """
        Set the lookback period for computing ATR. The default value
        of 100 ensures a _stable_ ATR.
        """
        hi, lo, c_prev = self.data.High, self.data.Low, pd.Series(self.data.Close).shift(1)
        tr = np.max([hi - lo, (c_prev - hi).abs(), (c_prev - lo).abs()], axis=0)
        atr = pd.Series(tr).rolling(periods).mean().bfill().values
        self.__atr = atr

    def set_trailing_sl(self, n_atr: float = 6):
        """
        Sets the future trailing stop-loss as some multiple (`n_atr`)
        average true bar ranges away from the current price.
        """
        self.__n_atr = n_atr

    def next(self):
        super().next()
        index = len(self.data)-1
        for trade in self.trades():
            if trade.is_long:
                trade.sl = max(trade.sl or -np.inf,
                               self.data.Close[index] - self.__atr[index] * self.__n_atr)
            else:
                trade.sl = min(trade.sl or np.inf,
                               self.data.Close[index] + self.__atr[index] * self.__n_atr)