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
    
    