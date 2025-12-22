import backtrader as bt
from backtrader.feeds import PandasData

class FuturesDataFeed(bt.feeds.PandasData):
    """
    期货DataFeed，基于现价和持仓量数据
    """
    lines = ('mark_price', 'volume_usd', 'open_interest', 'underlyer_spot', 'bid', 'ask')  # 添加持仓量线
    
    params = (
        ('datetime', -1),
        ('mark_price', -1),        # 使用现价作为主要价格
        ('volume', -1),
        ('volume_usd', -1),
        ('open_interest', -1),   # 持仓量字段
        ('underlyer_spot', -1),
        ('bid', -1),          # 买价
        ('ask', -1),          # 卖价
        ('bid_amount', -1),          # 买价
        ('ask_amount', -1),          # 卖价
        ('instrument_name', -1),          # 卖价
        ('underlyer', -1),          # 卖价
        ('expiration_date', -1),          # 卖价
        ('exchange', -1),          # 卖价
    )