
import backtrader as bt
from sqlalchemy import create_engine

#url中@必须用转义的%40
DB_URI_OTC = 'postgresql+psycopg2://clive:Welcome99%40%40@127.0.0.1:5432/crypto_quote'
engine = create_engine(
    DB_URI_OTC,
    echo=True,
    pool_timeout=5,
    pool_pre_ping=True,
    pool_recycle=3600,
)


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
    


class OptionsDataFeed(bt.feeds.PandasData):
    """
    期货DataFeed，基于现价和持仓量数据
    """
    lines = (
    # 'underlyer',
	# 'expiration_date',
	# 'claim_type',
	'mark_price',
	'mark_iv',
	'bid_iv',
	'ask_iv',
	# 'exercise',
	# 'settlement',
	'strike',
	'best_bid_price',
	'best_ask_price',
	'underlyer_spot',
	'forward_price',
	'volume',
	'best_ask_amount',
	'best_bid_amount',
	# 'instrument_name',
	# 'exchange',
    )  # 添加持仓量线
    
    params = (
        ('underlyer', -1),
        ('expiration_date', -1),
        ('claim_type', -1),
        ('mark_price', -1),
        ('mark_iv', -1),
        ('bid_iv', -1),
        ('ask_iv', -1),
        ('exercise', -1),
        ('settlement', -1),
        ('strike', -1),
        ('best_bid_price', -1),
        ('best_ask_price', -1),
        ('underlyer_spot', -1),
        ('forward_price', -1),
        ('volume', -1),
        ('best_ask_amount', -1),
        ('best_bid_amount', -1),
        ('instrument_name', -1),
        ('exchange', -1)
    )