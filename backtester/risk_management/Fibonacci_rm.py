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
