import pandas as pd

class FixedTP_SL_TradeManagement:
    def __init__(self, strategy, sl=0.015, tp=0.03):
        """
        Initialize the FixedTP_SL_TradeManagement class.

        :param strategy: reference to the Strategy object
        """
        self.strategy = strategy
        self.sl = sl
        self.tp = tp
        df = self.strategy.data.df

    def calculate_tp_sl(self, direction):
        """
        Calculate stop loss and take profit based on fixed pip values passed as arguments.

        :param direction: 'buy' or 'sell'
        :param stop_loss_pips: fixed stop loss in price units
        :param take_profit_pips: fixed take profit in price units
        :return: tuple (stop_loss_price, take_profit_price)
        """
        entry_price = self.strategy.data.df['Close'].iloc[-1]

        if direction.lower() == 'buy':
            stop_loss = entry_price*(1-self.sl)
            take_profit = entry_price*(1+self.tp)
        elif direction.lower() == 'sell':
            stop_loss = entry_price*(1+self.sl)
            take_profit = entry_price*(1-self.tp)
        else:
            raise ValueError("Invalid direction. Must be 'buy' or 'sell'.")

        stop_loss = round(stop_loss, 5)
        take_profit = round(take_profit, 5)

        return stop_loss, take_profit

# # Test block
# if __name__ == "__main__":
#     # Mock strategy with dummy data
#     class MockStrategy:
#         def __init__(self):
#             self.data = type('data', (object,), {})()
#             self.data.df = pd.DataFrame({
#                 'Close': [1.1000, 1.1050, 1.1100]  # Last close = 1.1100
#             })

#     # Create mock strategy
#     strategy = MockStrategy()

#     # Initialize with 1% SL and 2% TP
#     trade_manager = FixedTP_SL_TradeManagement(strategy=strategy, sl=0.01, tp=0.02)

#     # Test for buy
#     sl_buy, tp_buy = trade_manager.calculate_tp_sl('buy')
#     print(f"[BUY] SL: {sl_buy}, TP: {tp_buy}")  # Expected: SL=1.0989, TP=1.1322

#     # Test for sell
#     sl_sell, tp_sell = trade_manager.calculate_tp_sl('sell')
#     print(f"[SELL] SL: {sl_sell}, TP: {tp_sell}")  # Expected: SL=1.1211, TP=1.0878