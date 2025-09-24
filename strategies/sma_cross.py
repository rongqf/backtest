from backtesting import Strategy
from backtesting.lib import crossover
from backtesting.test import SMA


from pydantic import BaseModel, Field
from datetime import date
from typing import Literal

paramecfg = {
    'short_sma': {
        'type': int,
        'default': 10
    },
    'long_sma': {
        'type': int,
        'default': 20
    }
}

class SmaCross(Strategy):
    """双均线交叉策略"""
    short_sma = 10
    long_sma = 20

    def init(self, short_sma=10, long_sma=20):
        self.short_sma = short_sma
        self.long_sma = long_sma
        close = self.data.Close
        self.sma1 = self.I(SMA, close, self.short_sma)
        self.sma2 = self.I(SMA, close, self.long_sma)

    def next(self):
        if crossover(self.sma1, self.sma2):
            self.position.close()
            self.buy()
        elif crossover(self.sma2, self.sma1):
            self.position.close()
            self.sell()
            
if __name__ == "__main__":
    from backtesting import Backtest
    from backtesting.test import GOOG
    # 执行回测
    bt = Backtest(
        GOOG, 
        SmaCross, 
        cash=1000000, 
        commission=.002, 
        finalize_trades=True,
        )
    stats = bt.run()
    print(stats._trades.iloc[0])