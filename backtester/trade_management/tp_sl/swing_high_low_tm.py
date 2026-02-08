from backtester.helpers.indicators import calculate_atr

class Swing_High_Low:
    def __init__(self, strategy, swing_length=6, risk_reward_ratio=2):
        """
        Initialize swing-based trade management system with fixed ATR parameters.
        
        :param strategy: Reference to Strategy class object
        :param swing_length: Number of bars to consider for swing points (N)
        :param risk_reward_ratio: Desired risk-reward ratio (default 2:1)
        """
        self.strategy = strategy
        self.swing_length = swing_length
        self.risk_reward_ratio = risk_reward_ratio
        
        # Fixed parameters as per requirements
        self.buffer_multiplier = 2  
        self.atr_period = 14         
    def calculate_tp_sl(self, direction):
        """
        Calculate stop loss and take profit levels based on swing points.
        
        :param direction: Trade direction ('buy' or 'sell')
        :return: Tuple (stop_loss, take_profit) as raw float values
        """
        df = self.strategy.data.df
        entry_price = df['Close'].iloc[-1]
        

        atr = calculate_atr(df, self.atr_period)

        buffer = self.buffer_multiplier * atr
        
        # Calculate swing points
        window_size = self.swing_length + 1  
        swing_high = df['High'].rolling(window=window_size).max().iloc[-1]
        swing_low = df['Low'].rolling(window=window_size).min().iloc[-1]

        if direction.lower() == 'buy':
            stop_loss = swing_low - buffer
            risk = entry_price - stop_loss  # Use stop_loss instead of swing_low to ensure positive risk
            take_profit = entry_price + (risk * self.risk_reward_ratio)
            
            # Ensure valid order: SL < Entry < TP
            if stop_loss >= entry_price or take_profit <= entry_price:
                raise ValueError(f"Invalid buy levels: SL={stop_loss}, Entry={entry_price}, TP={take_profit}")

        elif direction.lower() == 'sell':
            stop_loss = swing_high + buffer
            risk = stop_loss - entry_price
            take_profit = entry_price - (risk * self.risk_reward_ratio)
            
            # Ensure valid order: TP < Entry < SL
            if stop_loss <= entry_price or take_profit >= entry_price:
                raise ValueError(f"Invalid sell levels: SL={stop_loss}, Entry={entry_price}, TP={take_profit}")

        else:
            raise ValueError(f"Invalid direction: {direction}. Must be 'buy' or 'sell'.")
        
        return round(stop_loss, 5), round(take_profit, 5)