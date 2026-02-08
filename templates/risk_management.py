import numpy as np
import os
import math
import sys


class AntiMartingaleRiskManagement:
    def __init__(self, strategy, initial_risk_per_trade=0.01, multiplier=1.5):
        self.strategy = strategy
        self.current_level = 0
        self.multiplier=multiplier
        self.initial_risk_per_trade = initial_risk_per_trade

    def calculate_risk_levels(self):
        # Calculate the risk levels using a martingale strategy
        risk_levels = []
        risk = self.initial_risk_per_trade
        for i in range(30):  # Assume a maximum of 10 levels
            risk_levels.append(risk)
            risk *= self.multiplier  # Double the risk at each level (Martingale approach)
        return risk_levels

    def get_risk_per_trade(self):
        risk_levels = self.calculate_risk_levels()
        if self.current_level >= len(risk_levels):
            return 0
        trade_size = self.strategy._broker._cash * risk_levels[self.current_level]
        return trade_size

    def update_after_loss(self):
        self.current_level = 0
   
    def update_after_win(self):
        self.current_level += 1


class CPPIRiskManagement:
    def __init__(self, strategy, initial_risk_per_trade=0.01, risk_percent=0.05):
        self.strategy = strategy # Reference to strategy object
        self.initial_risk_per_trade = initial_risk_per_trade
        self.protection_floor = self.strategy._broker._cash * (1 - self.initial_risk_per_trade)
        self.risk_percent = risk_percent
        
    def get_risk_per_trade(self):
        current_capital = self.strategy._broker._cash
        risk = (current_capital - self.protection_floor) * self.risk_percent
        return max(0, risk)
        
    def update_after_loss(self):
        pass
    
    def update_after_win(self):
        pass


class DAlembertRiskManagement:
    def __init__(self, strategy, initial_risk_per_trade=0.01, step=1):
        self.strategy = strategy 
        self.initial_risk_per_trade = initial_risk_per_trade
        self.current_level = 0
        self.step = step  # Step size to increase or decrease the risk

    def calculate_risk_levels(self):
        risk_levels = []
        risk = self.initial_risk_per_trade
        while self.strategy._broker._cash > risk:
            risk_levels.append(risk)
            risk += self.step
        return risk_levels

    def get_risk_per_trade(self):
        risk_levels = self.calculate_risk_levels()
        if self.strategy._broker._cash >= len(risk_levels):
            return 0
        trade_size = self.strategy._broker._cash * risk_levels[self.current_level]
        return trade_size

    def update_after_loss(self):
        self.current_level += 1  # Increase the level after a loss
        if self.current_level >= len(self.calculate_risk_levels()):
            self.current_level = len(self.calculate_risk_levels()) - 1  # Cap the level

    def update_after_win(self):
        if self.current_level > 0:
            self.current_level -= 1  # Decrease the level after a win



class EfficiencyRatio:
    def __init__(self, strategy, initial_risk_per_trade=0.01, profit_risk_percentage=0.1):
        self.initial_equity = strategy._broker._cash
        self.initial_risk_per_trade = initial_risk_per_trade
        self.profit_risk_percentage = profit_risk_percentage
        self.closed_trade_profit = 0
        self.prices = None

    def init(self):  # Properly indented as a class method
        """
        Optional initialization method for EfficiencyRatio.
        """
        pass



    def get_risk_per_trade(self):
        """
        Calculates the risk per trade using Efficiency Ratio Scaling.
        
        The total risk (base risk + profit bonus) is scaled by the Efficiency Ratio (ER):
        
            ER = (|last_price - first_price|) / (sum of absolute differences between consecutive prices)
        
        If no price data is available in self.prices, ER defaults to 1.
        
        Returns:
            float: The risk per trade in monetary units.
        """
        # Calculate the base risk and profit bonus.
        base_risk = self.initial_equity * self.initial_risk_per_trade
        profit_bonus = self.closed_trade_profit * self.profit_risk_percentage
        total_risk = base_risk + profit_bonus

        # Calculate the Efficiency Ratio (ER) using stored price data if available.
        if self.prices is not None and len(self.prices) >= 2:
            price_change = abs(self.prices[-1] - self.prices[0])
            volatility = np.sum(np.abs(np.diff(self.prices)))
            er = price_change / volatility if volatility != 0 else 0.0
            er = max(0.0, min(er, 1.0))
        else:
            er = 1.0  # Default to full risk if no price data is available

        risk_per_trade = total_risk * er
        return risk_per_trade

    def update_after_win(self):
        """
        Update internal state after a winning trade.
        
        For demonstration purposes, this method adds a fixed profit value
        to the cumulative closed trade profit.
        """
        # Update with a default profit amount (e.g., $500)
        default_profit = 500  
        self.closed_trade_profit += default_profit

    def update_after_loss(self):
        """
        Update internal state after a losing trade.
        
        For demonstration purposes, this method subtracts a fixed loss value
        from the cumulative closed trade profit.
        """
        # Update with a default loss amount (e.g., $300)
        default_loss = 300  
        self.closed_trade_profit -= default_loss


class EqualRiskManagement:
    def __init__(self, strategy, initial_risk_per_trade=0.01):
        '''A reference to the strategy object is stored here. 
        So, updates in strategy object directly reflected here as well
        '''
        self.strategy = strategy 
        self.initial_risk_per_trade = initial_risk_per_trade
        self.current_level = 0

    def get_risk_per_trade(self):
        trade_size = (self.strategy._broker._cash) * self.initial_risk_per_trade
        return trade_size

    def update_after_loss(self):
        self.current_level += 1

    def update_after_win(self):
        self.current_level = 0


class EquityCrossoverRiskManagement:
    def __init__(self, strategy, initial_risk_per_trade=0.01, size_increment=0.25, size_decrement=0.15, n_trades=20):
        self.strategy = strategy # Reference to strategy object
        self.size_increment = size_increment
        self.size_decrement = size_decrement
        self.n_trades = n_trades
        self.risk_percent = initial_risk_per_trade # Initial risk percent
        self.equity_history = [] # Store the equities at the beginning of the trades
        
    def get_risk_per_trade(self):
        if len(self.equity_history) >= self.n_trades: # Changing the risk percentage only when atleast n_trades have occured
            current_capital = self.strategy._broker._cash
            moving_average = sum(self.equity_history[-self.n_trades:]) / self.n_trades
            if current_capital > moving_average:
                self.risk_percent *= (1 + self.size_increment)
            else:
                self.risk_percent *= (1 - self.size_decrement)
        self.equity_history.append(self.strategy._broker._cash)
        risk = self.strategy._broker._cash * self.risk_percent
        return risk
    
    def update_after_loss(self):
        pass
    
    def update_after_win(self):
        pass


    
class FibonacciRiskManagement:
    def __init__(self, strategy, initial_risk_per_trade=0.01, multiplier=1.5):
        self.strategy = strategy
        self.current_level = 0
        self.multiplier=multiplier
        self.initial_risk_per_trade = initial_risk_per_trade

    def calculate_risk_levels(self):
        # Calculate the risk levels using a martingale strategy
        risk_levels = []
        risk = self.initial_risk_per_trade
        #Adding first two risk levels for fibonacci
        for i in range(0,2):
            risk_levels.append(risk)
        #creating fibonacci risk levels
        i1 = 0
        i2 = 1
        
        for i in range(30):  # Assume a maximum of 10 levels
            risk_levels.append(risk_levels[i1]+risk_levels[i2])
            i1=i1+1
            i2=i2+1
        return risk_levels

    def get_risk_per_trade(self):
        risk_levels = self.calculate_risk_levels()
        if self.current_level >= len(risk_levels):
            return 0
        trade_size = self.strategy._broker._cash * risk_levels[self.current_level]
        return trade_size

    def update_after_loss(self):
        self.current_level += 1

    def update_after_win(self):
        self.current_level = 0





class FixedRatioPositionSizing:
    def __init__(self, strategy, initial_risk_per_trade=0.01, delta=5000, m=0.5):
        self.strategy = strategy
        self.initial_risk_per_trade = initial_risk_per_trade  # Initial risk as % of capital
        self.initial_capital = self.strategy._broker._cash  # Starting capital
        self.delta = delta  # Dollar profit needed to increase position size
        self.m = m #this is the exponent factor
        self.equity = [self.initial_capital]  # Track equity over trades
        self.profit = 0  # Cumulative profit (P)
        self.current_risk_percent = initial_risk_per_trade  # Current risk as % of capital
    

    def calculate_profit(self):
        # Calculate cumulative profit as the difference between current equity and initial capital
        self.profit = self.equity[-1] - self.initial_capital

    def get_risk_per_trade(self):
        capital = self.strategy._broker._cash
        # Append the latest equity
        self.equity.append(capital)
        
        # Calculate the profit P
        self.calculate_profit()

        # If profit is negative, default to initial risk per trade
        if self.profit <= 0:
            risk_per_trade = self.initial_risk_per_trade * self.initial_capital
        else:
            # Calculate risk per trade using the Fixed Ratio Position Sizing formula
            #N = 0.5 * [(1 + 8 * P/delta)^m + 1] 
            risk_per_trade = (
                0.5 * (pow((1 + 8 * (self.profit / self.delta)),self.m) + 1)
                * self.initial_risk_per_trade
                * self.initial_capital
            )

        return risk_per_trade
    
    def print_equity(self):
        return self.equity
    
    def update_after_loss(self):
        # Custom logic for loss can be added if needed
        pass

    def update_after_win(self):
        # Custom logic for win can be added if needed
        pass



class FixedRatioPositionSizing:
    def __init__(self, strategy, initial_risk_per_trade=0.01, delta=5000):
        self.strategy = strategy
        self.initial_risk_per_trade = initial_risk_per_trade  # Initial risk as % of capital
        self.initial_capital = self.strategy._broker._cash  # Starting capital
        self.delta = delta  # Dollar profit needed to increase position size
        self.equity = [self.initial_capital]  # Track equity over trades
        self.profit = 0  # Cumulative profit (P)

    def calculate_profit(self):
        # Calculate cumulative profit as the difference between current equity and initial capital
        self.profit = self.equity[-1] - self.initial_capital

    def get_risk_per_trade(self):
        capital = self.strategy._broker._cash
        
        # Append the latest equity
        self.equity.append(capital)
        
        # Calculate the profit P
        self.calculate_profit()

        # If profit is negative, default to initial risk per trade
        if self.profit <= 0:
            risk_per_trade = self.initial_risk_per_trade * self.initial_capital
        else:
            # Calculate risk per trade using the Fixed Ratio Position Sizing formula
            ##N = 0.5 * [((2 * N0 – 1)^2 + 8 * P/delta)^0.5 + 1] N0 = 1 for as of now
            risk_per_trade = (
                0.5 * (math.sqrt(1 + 8 * (self.profit / self.delta)) + 1)
                * self.initial_risk_per_trade
                * self.initial_capital
            )

        return risk_per_trade
    
    def update_after_loss(self):
        pass

    def update_after_win(self):
        pass


class ManhattanRiskManagement:
    def __init__(self, strategy, initial_risk_per_trade: float = 0.01) -> None:
        self.strategy = strategy
        self.initial_risk_per_trade = initial_risk_per_trade
        self.stake_increment = self.initial_risk_per_trade
        self.current_stake = self.initial_risk_per_trade
        self.current_capital = self.strategy._broker._cash
        self.initial_capital = self.strategy._broker._cash
        self.losses = 0

    def get_risk_per_trade(self):
        self.current_capital = self.strategy._broker._cash
        return self.current_stake

    def update_after_loss(self):
        self.losses += 1
        self.current_stake = self.initial_risk_per_trade + (self.stake_increment * self.losses)

    def update_after_win(self):
        self.current_stake = self.initial_risk_per_trade
        self.losses = 0

    def reset(self):
        self.current_stake = self.initial_risk_per_trade
        self.current_capital = self.initial_capital
        self.losses = 0



class MarketRegimeADX:
    def __init__(self, strategy, initial_risk_per_trade=0.01, profit_risk_percentage=0.1, adx_threshold=20):
        """
        Initialize the RiskPerTrade class.

        :param strategy: The trading strategy object (must have an `adx` attribute or method).
        :param initial_risk_per_trade: Initial risk percentage per trade (default: 3%).
        :param profit_risk_percentage: Percentage of profits to add to risk (default: 10%).
        :param adx_threshold: ADX threshold for determining trending markets (default: 25).
        """
        self.strategy = strategy 
        self.initial_equity = strategy._broker._cash
        self.initial_risk_per_trade = initial_risk_per_trade
        self.profit_risk_percentage = profit_risk_percentage
        self.closed_trade_profit = 0
        self.adx_threshold = adx_threshold

    def get_risk_per_trade(self):
        """
        Calculate the risk per trade based on the current ADX value.
        ADX value is fetched directly from the strategy object.
        """
        
        if hasattr(self.strategy, 'adx') and len(self.strategy.adx) > 0:
            adx_value = self.strategy.adx[-1] 
        else:
            raise ValueError("ADX data not found in the strategy object.")
        
        base_risk = self.initial_equity * self.initial_risk_per_trade
        profit_risk = self.closed_trade_profit * self.profit_risk_percentage
        total_risk = base_risk + profit_risk

        
        if adx_value >= self.adx_threshold:
            risk_multiplier = 1.0  
        else:
            risk_multiplier = 0.5  

        risk_per_trade = total_risk * risk_multiplier
        
        return risk_per_trade

    def update_after_loss(self):
        """Optional logic after a loss (e.g., reduce risk)"""
        self.initial_risk_per_trade *= 0.9  

    def update_after_win(self):
        """Optional logic after a win (e.g., increase risk)"""
        self.initial_risk_per_trade *= 1.1  



class MartingaleRiskManagement:
    def __init__(self, strategy, initial_risk_per_trade: float = 0.01, multiplier: float = 1.5) -> None:
        self.current_level = 0
        self.multiplier=multiplier
        self.strategy = strategy
        self.initial_risk_per_trade = initial_risk_per_trade

    def calculate_risk_levels(self):
        # Calculate the risk levels using a martingale strategy
        risk_levels = []
        risk = self.initial_risk_per_trade
        for i in range(30):  # Assume a maximum of 10 levels
            risk_levels.append(risk)
            risk *= self.multiplier  # Double the risk at each level (Martingale approach)
        return risk_levels

    def get_risk_per_trade(self):
        risk_levels = self.calculate_risk_levels()
        if self.current_level >= len(risk_levels):
            return 0
        trade_size = self.strategy._broker._cash * risk_levels[self.current_level]
        #print("trade size is",trade_size)
        return trade_size

    def update_after_loss(self):
        self.current_level += 1

    def update_after_win(self):
        self.current_level = 0



class MoneyMarketRiskManagement:
    def __init__(self, strategy, market_money_risk_pct = 0.1, base_money_risk_pct = 0.01, 
                 max_equity_risk_pct = 0.04, base_dividing_factor = 4, n_trades = 4):
        self.strategy = strategy # Reference to strategy object
        self.initial_capital = self.strategy._broker._cash
        self.market_money_risk_pct = market_money_risk_pct
        self.base_money_risk_pct = base_money_risk_pct
        self.max_equity_risk_pct = max_equity_risk_pct
        self.base_dividing_factor = base_dividing_factor
        self.n_trades = n_trades
        self.equity_history = []
        
    def get_risk_per_trade(self):
        # Assuming every time a trade occurs, this function gets called once
        if len(self.equity_history) < self.n_trades:
            equity_before_n_trades = self.initial_capital
            gain_in_n_trades = 0
        else:
            equity_before_n_trades = self.equity_history[-self.n_trades]
            gain_in_n_trades = self.strategy._broker._cash - equity_before_n_trades
        self.equity_history.append(self.strategy._broker._cash) # Append cuurent capital to equity history
        base_money = equity_before_n_trades + gain_in_n_trades/self.base_dividing_factor
        market_money = self.strategy._broker._cash - base_money
        total = base_money + market_money
        risk = min(base_money * self.base_money_risk_pct + market_money * self.market_money_risk_pct,
                   self.max_equity_risk_pct * total)
        return risk
    
    def update_after_loss(self):
        pass
    
    def update_after_win(self):
        pass
    
    

class OptimalFRiskManagement:
    def __init__(self, strategy, f_range=np.arange(0.01, 1.01, 0.01)):
        self.strategy = strategy
        self.initial_equity = strategy._broker._cash
        self.f_range = f_range  # Range of f values to optimize
        self.optimal_f = None  # Store optimal f value
    
    def get_trade_returns(self):
        trade_returns = []
        for trade in self.strategy.closed_trades:
            trade_returns.append(trade.pl_pct)
        return trade_returns

    def get_risk_per_trade(self):
        trade_returns = self.get_trade_returns()  # Assuming strategy has a function to get returns
        if len(trade_returns) == 0:
            return 0.01  # Default risk if no trades yet
        
        worst_loss = min(trade_returns)
        
        hprs = lambda f: [1 + f * (r / worst_loss) for r in trade_returns]
        twr_values = [np.prod(hprs(f)) for f in self.f_range]
        
        self.optimal_f = self.f_range[np.argmax(twr_values)]
        
        risk_per_trade =  self.optimal_f * self.initial_equity  
        return risk_per_trade
    
    def update_after_loss(self):
        pass  # Placeholder for potential adjustments after losses
    
    def update_after_win(self):
        pass  # Placeholder for potential adjustments after wins



class OscardsGrindRiskManagement:
    def __init__(self, strategy, initial_risk_per_trade=0.01):
        self.strategy = strategy
        self.initial_risk_per_trade = self.initial_risk_per_trade
        self.initial_capital = self.strategy._broker._cash
        self.winning_goal = self.initial_risk_per_trade
        self.current_stake = self.initial_risk_per_trade
        self.current_capital = self.initial_capital
        self.current_wins = 0

    def get_risk_per_trade(self):
        self.current_capital = self.strategy._broker._cash
        return self.current_stake

    def update_after_loss(self):
        # After a loss or tie, the stake remains the same
        self.current_stake = self.winning_goal

    def update_after_win(self):
        # After a win, increase the next bet by one unit
        self.current_stake += self.winning_goal

    def reset(self):
        # Optionally, reset to initial settings
        self.current_stake = self.winning_goal
        self.current_capital = self.initial_capital

class ParoliRiskManagement:
    def __init__(self, strategy, initial_risk_per_trade=0.01):
        self.strategy = strategy
        self.initial_risk_per_trade = initial_risk_per_trade
        self.initial_capital = strategy._broker._cash
        self.base_stake = initial_risk_per_trade
        self.current_stake = initial_risk_per_trade
        self.current_capital = strategy._broker._cash
        self.consecutive_wins = 0

    def get_risk_per_trade(self):
        self.current_capital = self.strategy._broker._cash
        return self.current_stake

    def update_after_loss(self):
        self.current_stake = self.base_stake
        self.consecutive_wins = 0

    def update_after_win(self):
        self.consecutive_wins += 1
        if self.consecutive_wins >= 3:
            self.current_stake = self.base_stake
            self.consecutive_wins = 0
        else:
            self.current_stake = self.base_stake * (2 ** self.consecutive_wins)



class PortfolioHeatRiskManagement:
    def __init__(self, strategy, initial_risk_per_trade: float = 0.01) -> None:
        self.strategy = strategy
        self.initial_risk_per_trade = initial_risk_per_trade
        
    def get_sqn(self):
        num_trades = len(self.strategy._broker.closed_trades)
        
        if num_trades == 0:
            # No trade made so far
            return 0
        
        num_trades = min(100, num_trades) # num_trades capped by 100
        avg_r_multiple = np.mean([trade.pl_pct for trade in self.strategy._broker.closed_trades])
        std_r_multiple = np.std([trade.pl_pct for trade in self.strategy._broker.closed_trades])
        if std_r_multiple == 0:
            return 0
        
        sqn = (avg_r_multiple / std_r_multiple) * np.sqrt(num_trades)
        
        if sqn < 1:
            sqn = 1  
        elif sqn > 7:
            sqn = 7  
        
        return sqn
    
    def get_risk_per_trade(self):
        num_trades = len(self.strategy._broker.closed_trades)
        current_capital = self.strategy._broker._cash
        # Fixed position size for the first 20 trades
        if num_trades <= 20:
            return 0.5* current_capital * self.initial_risk_per_trade
        
        # For trades beyond 20
        sqn = self.get_sqn()
        if sqn == 0:
            trade_size = 0.2 * current_capital * self.initial_risk_per_trade 
        else:
            trade_size = current_capital * self.initial_risk_per_trade * (2 + (sqn - 2)) / 3
            
        return trade_size
    
    def update_after_loss(self):
        pass
    def update_after_win(self):
        pass


class ProfitRiskManagement:
    def __init__(self, strategy, initial_risk_per_trade=0.01, profit_risk_pct=0.1):
        self.strategy = strategy # Reference to strategy object
        self.initial_capital = self.strategy._broker._cash
        self.profit_risk_pct = profit_risk_pct # Inputted as a real value not percentage
        self.initial_risk_per_trade = initial_risk_per_trade
        
    def get_risk_per_trade(self):
        profit = self.strategy._broker._cash - self.initial_capital # Positive or negative
        trade_size = (self.initial_risk_per_trade * self.initial_capital) + (self.profit_risk_pct * profit)
        return trade_size
    
    def update_after_loss(self):
        pass
    
    def update_after_win(self):
        pass




class RiskPerTrade:
    def __init__(self, strategy, initial_risk_per_trade=0.01, profit_risk_percentage=0.1):
        self.initial_equity = strategy._broker._cash
        self.initial_risk_per_trade = initial_risk_per_trade
        self.profit_risk_percentage = profit_risk_percentage
        self.closed_trade_profit = 0 

    def get_risk_per_trade(self):
        base_risk = self.initial_equity * self.initial_risk_per_trade
        profit_risk = self.closed_trade_profit * self.profit_risk_percentage
        risk_per_trade = base_risk + profit_risk
        return risk_per_trade

    def update_after_loss(self):
        pass
    def update_after_win(self):
        pass
    



class TIIPRiskManagement:
    def __init__(self, strategy, initial_risk_per_trade=0.01, risk_percent=0.05):
        if not 0 < initial_risk_per_trade < 1:
            raise ValueError("initial_risk_per_trade must be between 0 and 1")
        if not 0 < risk_percent < 1:
            raise ValueError("risk_percent must be between 0 and 1")
        if not 0 < initial_risk_per_trade < 1:
            raise ValueError("initial_risk_per_trade must be between 0 and 1")
        if not 0 < risk_percent < 1:
            raise ValueError("risk_percent must be between 0 and 1")
        self.strategy = strategy # Reference to strategy object
        self.initial_risk_per_trade = initial_risk_per_trade
        self.protection_floor = self.strategy._broker._cash * (1 - self.initial_risk_per_trade)
        self.risk_percent = risk_percent
        
    def get_risk_per_trade(self):
        current_capital = self.strategy._broker._cash
        risk = (current_capital - self.protection_floor) * self.risk_percent
        return max(0, risk)
        
    def update_after_loss(self):
        pass
    
    def update_after_win(self):
        pass




class VolatilityATR:
    def __init__(self, strategy, initial_risk_per_trade=0.01, profit_risk_percentage=0.1, atr=1.5, lot_size=10_00000, tick_size=0.01, exchange_rate=1.0):
        """
        Initialize the VolatilityATR class.

        :param strategy: The trading strategy object.
        :param initial_risk_per_trade: Initial risk percentage per trade (default: 2%).
        :param profit_risk_percentage: Percentage of profits to add to risk (default: 10%).
        :param atr: Average True Range (ATR) value (default: 1.5).
        :param lot_size: Trade size (e.g., 100,000 for a standard lot in forex).
        :param tick_size: Smallest price movement (e.g., 0.0001 for forex).
        :param exchange_rate: Exchange rate of the quote currency to the account currency.
        """
        self.initial_equity = strategy._broker._cash
        self.initial_risk_per_trade = initial_risk_per_trade
        self.profit_risk_percentage = profit_risk_percentage
        self.closed_trade_profit = 0
        self.atr = atr
        self.lot_size = lot_size
        self.tick_size = tick_size
        self.exchange_rate = exchange_rate

    def get_risk_per_trade(self):
        """
        Calculate the risk per trade based on ATR and dynamically computed point_value.

        :return: Risk per trade as a percentage of equity.
        """
        point_value = self.lot_size * self.tick_size * self.exchange_rate
        point_value_percentage = point_value / self.initial_equity * 100

        base_risk = self.initial_equity * self.initial_risk_per_trade
        profit_risk = self.closed_trade_profit * self.profit_risk_percentage
        total_risk = base_risk + profit_risk

        risk_per_trade = total_risk / (self.atr * point_value_percentage)
        return risk_per_trade

    def update_after_win(self):
        """
        Update logic after a winning trade.
        """
        self.initial_risk_per_trade *= 1.1 

    def update_after_loss(self):
        """
        Update logic after a losing trade.
        """
        self.initial_risk_per_trade *= 0.9




class VolatilityBasedPositionSizing:
    def __init__(self, strategy, initial_risk_per_trade = 0.01, target_var=0.015):
        self.strategy = strategy
        self.initial_equity = strategy._broker._cash
        self.initial_risk_per_trade = initial_risk_per_trade
        self.target_var = target_var
        self.lambda_decay = 0.94
        self.window_size = 74  # Number of trades for the estimation window

    def get_risk_per_trade(self):
        price_data = self.strategy.data['Close'] 
        returns = np.diff(price_data) / price_data[:-1]  
        
        # Check if the number of returns is less than the window size
        if len(returns) < self.window_size:
            # If insufficient data, use all available returns
            effective_window_size = len(returns)
        else:
            effective_window_size = self.window_size
        
        # Compute exponentially weighted moving average (EWMA) volatility
        weights = np.array([self.lambda_decay ** (effective_window_size - t - 1) for t in range(effective_window_size)])
        weights /= weights.sum()
        mean_return = np.mean(returns[-effective_window_size:])
        volatility = np.sqrt(np.sum(weights * (returns[-effective_window_size:] - mean_return) ** 2))  # EWMA volatility
        
        # Compute Value at Risk (VaR)
        var = -(mean_return - 1.65 * volatility)  # 95% VaR corresponds to 1.65 standard deviations
        leverage_adjustment = self.target_var / var
        
        risk_per_trade = self.initial_risk_per_trade * leverage_adjustment
        return risk_per_trade

    def update_after_loss(self):
        pass

    def update_after_win(self):
        pass




class WinMultiplier:
    def __init__(self, strategy, initial_risk_per_trade=0.01,num_past_trade= 5):
        """
        Initialize the RiskPerTrade class.
        
        :param strategy: The trading strategy object.
        :param initial_risk_per_trade: Initial risk percentage per trade (default: 3%).
        :param num_past_trades: Number of past trades to consider for win/loss ratio (default: 5).
        """
        self.strategy = strategy  
        self.initial_equity = strategy._broker._cash
        self.initial_risk_per_trade = initial_risk_per_trade
        self.past_trades = [] 
        self.num_past_trade = num_past_trade
        

    def get_risk_per_trade(self):
        """
        Calculate the risk per trade based on the past win/loss ratio and adjust position sizing.
        """
       
        if len(self.past_trades) < self.num_past_trade:
            raise ValueError("Not enough trades have been completed to calculate risk per trade.")
        
       
        wins = sum(self.past_trades[-self.num_past_trade:])  
        losses = self.num_past_trade - wins 

       
        win_ratio = wins / self.num_past_trade
        
        
        win_multiplier = win_ratio * 0.3  

        
        adjusted_position_size = self.initial_equity * self.initial_risk_per_trade * (1 + win_multiplier)

       
        risk_per_trade = adjusted_position_size  

        return risk_per_trade

    def update_after_loss(self):
        """Optional logic after a loss (e.g., reduce risk and add to past trades)"""
        self.past_trades.append(False) 
        self.initial_risk_per_trade *= 0.9  

    def update_after_win(self):
        """Optional logic after a win (e.g., increase risk and add to past trades)"""
        self.past_trades.append(True)  
        self.initial_risk_per_trade *= 1.1 
