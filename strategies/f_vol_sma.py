import os
import pandas as pd
import numpy as np
import backtrader as bt
from backtrader.feeds import PandasData

from utils.data_feed_utils import FuturesDataFeed, engine


backengine = 'backtrader'
paramecfg = {
    'cash': {
        'type': int,
        'default': 500000
    },
    'commission': {
        'type': float,
        'default': 0.002
    },
    'begin_time': {
        'type': str,
        'default': '2025-09-01'
    },
    'end_time': {
        'type': str,
        'default': '2025-09-10'
    },
    'code': {
        'type': str,
        'default': ''
    }
}

class VolumeIndicator(bt.Indicator):
    lines = ('volume', 'buy_signal', 'sell_signal')
    plotinfo = dict(
        subplot=True,
        buy_signal=dict(marker='^', markersize=8.0, color='lime', fillstyle='full'),
        sell_signal=dict(marker='v', markersize=8.0, color='red', fillstyle='full'),
        )

    def __init__(self):
        # 确认 self.data 是有效的，或者明确指定数据源，例如 self.data.volume
        # 最简单的调试方法：直接将数据源赋值给指标线
        self.lines.volume = self.data.volume # 尝试直接将数据源的volume线赋给指标线

        # 分配买卖信号
        # 假设您的策略已经将信号添加到了数据源中
        if hasattr(self.data, 'buy_signal'):
            self.lines.buy_signal = self.data.buy_signal
            
        if hasattr(self.data, 'sell_signal'):
            self.lines.sell_signal = self.data.sell_signal
      
# 1. 定义一个在成交量子图上显示买卖信号的观测器
class VolumeBuySell(bt.observers.BuySell):
    """
    自定义观测器，将买卖信号也绘制在成交量子图上。
    """
    def __init__(self):
        super(VolumeBuySell, self).__init__()  # 首先调用父类的初始化方法
        # 核心设置：修改绘图信息
        # 假设您的成交量指标对象在策略中命名为 `my_volume_ind`
        # 关键一步：将这个观测器的"主人"设置为您的成交量指标
        # 这样买卖信号就会和成交量画在同一个坐标系中
        self.plotinfo.plotmaster = self._owner.volume  # 注意这里需要通过_owner来访问策略的属性
        # 同时，必须设置不创建独立子图，而是叠加在"主人"的图上
        self.plotinfo.subplot = False

        # (可选) 您可以自定义在这个子图上买卖信号的显示样式，比如缩小标记大小
        self.plotlines.buy.markersize = 6.0
        self.plotlines.sell.markersize = 6.0
          
# VolSma 策略
class FVolSma(bt.Strategy):
    
    def __init__(self):
        pass
        self.volume = VolumeIndicator(self.data)
        # 成交量
        self.vol = self.data.volume
        
        sma1 = bt.indicators.SMA(self.vol, period=10)
        sma2 = bt.indicators.SMA(self.vol, period=20)
        self.crossover = bt.indicators.CrossOver(sma1, sma2)
        # sma1.plotinfo.plotid = 'volsma1'
        # sma2.plotinfo.plotid = 'volsma2'
        
        sma1.plotinfo.plotmaster = self.volume
        sma2.plotinfo.plotmaster = self.volume
        
        # self.volume_buysell = VolumeBuySell()
        # # 更直接可靠的方式：在这里设置plotmaster
        # self.volume_buysell.plotinfo.plotmaster = self.volume
        # self.volume_buysell.plotinfo.subplot = False
        
    def prenext(self):
        self.next()         # 执行next()方法，实现买入/卖出逻辑
        
        
    def next(self):
        #print(self.datetime.datetime(0))
        pass
        if self.crossover > 0:
            self.buy()  # 买入
        elif self.crossover < 0:
            self.sell()  # 卖出
        

    # 订单状态变化时引擎会调用notify_order
    def notify_order(self, order):
        print('*' * 100)
        print('notify_order', order)
    
        if order.status in [order.Submitted, order.Accepted]:
            return

        # 如果交易已经完成，显示成交信息
        if order.status in [order.Completed]:
            if order.isbuy() or order.issell():
                print('{}  Buy/Sell {}, Price: {:.4f}, Size: {:6.0f}, Cost: {:.4f}, Comm {:.4f}'.format(
                        self.datetime.date(),
                        order.info['ticker'],
                        order.executed.price,
                        order.executed.size,
                        order.executed.value,
                        order.executed.comm)
                )

        # 如果订单未成交则给出提示
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            print('Order Canceled/Margin/Rejected: {}'.format(order.info['ticker']))


    
class DataFeed:
    def __init__(self, paramecfg={}):
        self.code = ''
        self.begin_time = paramecfg.get('begin_time', '2025-09-01') 
        self.end_time = paramecfg.get('end_time', '2025-09-05')

    def get_strategy_params(self):
        return {}

    def add_data_to_engine(self, cerebro, datas=[]):
        sql = f"""
        select * from crypto_futures_5m where datetime >= '{self.begin_time}' and datetime < '{self.end_time}'
        """
        df = pd.read_sql(sql, engine)
        df['close'] = df['mark_price']
        df['open'] = df['close']
        df['high'] = df['close']
        df['low'] = df['close']
        dfs = df.groupby(['exchange', 'instrument_name', 'expiration_date'])
        
        n = 0
        dfss = []
        for i, df in dfs:
            #dfi = df[['datetime', 'mark_price', 'close', 'volume', 'volume_usd', 'open_interest', 'underlyer_spot', 'bid', 'ask']]
            
            #df.index = pd.to_datetime(df['datetime'])
            df.set_index('datetime', inplace=True)
            if n != 0:
                dfss[0]['volume'] += df['volume']
                dfss[0]['volume_usd'] += df['volume_usd']
                dfss[0]['open_interest'] += df['open_interest']
            dfss.append(df)
            
        df = dfss[0].sort_values(by='datetime').reset_index()
        # df['close'] = df['volume']
        # df['open'] = df['close']
        # df['high'] = df['close']
        # df['low'] = df['close']
        data = FuturesDataFeed(dataname=df, datetime='datetime')
        cerebro.adddata(data, name='allvol')
        print(i)
        print(df[['mark_price', 'datetime', 'date']])
        print(df.head())
            
    
        

            
if __name__ == "__main__":
    import numpy as np
    # 检查bool8是否存在，如果不存在，则将其指向np.bool_
    if not hasattr(np, 'bool8'):
        np.bool8 = np.bool_
    # import matplotlib.pyplot as plt
    # plt.rcParams['font.family'] = 'DejaVu Serif'  # 设置全局默认字体为DejaVu Sans
    import pyfolio as pf
    import quantstats
    from backtrader_plotly.plotter import BacktraderPlotly
    from backtrader_plotly.scheme import PlotScheme
    import plotly.io
    import quantstats as qs
    from backtrader_plotting import Bokeh
    from backtrader_plotting.schemes import Tradimo

    # 设置 quantstats 的默认字体
    #qs.extend_pandas()
    #qs.plots.defaults.fontname = 'DejaVu Sans'
    # 初始化回测引擎
    cerebro = bt.Cerebro()

    # 设置交易资金和交易费用
    cerebro.broker.set_cash(500000)
    cerebro.broker.setcommission(commission=0.002)
    cerebro.addsizer(bt.sizers.FixedSize, stake=1)

    datafeed = DataFeed({'begin_time': '2025-09-01', 'end_time': '2025-09-05'})
    params = datafeed.get_strategy_params()
    # 添加自己编写的策略，opts是第1小节“策略所需数据”中提到的期权合约信息
    cerebro.addstrategy(VolSma, **params)
    datafeed.add_data_to_engine(cerebro)
        
    # 在执行策略之前添加分析器，我添加了3个，分别是：收益，回撤和夏普比率
    cerebro.addanalyzer(bt.analyzers.Returns, _name='treturn', timeframe=bt.TimeFrame.Minutes)
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe', timeframe=bt.TimeFrame.Minutes)    
    # 回测时需要添加 PyFolio 分析器
    cerebro.addanalyzer(bt.analyzers.PyFolio, _name='pyfolio', timeframe=bt.TimeFrame.Minutes)
        
    # 执行回测
    thestrats = cerebro.run()

    plotconfig = {
        'id:volsma1': dict(
            subplot=True,
        ),
        'id:volsma2': dict(
            subplot=True,
        ),
    }
    scheme=Tradimo()
    scheme.volup = 'red',
    scheme.voldown = 'red'
    # 配置 Bokeh 绘图器并保存
    b = Bokeh(
        # style='candle',        # 主图样式，例如 'candle' 为K线图
        plot_mode='single',    # 绘图模式，'single' 将所有内容放在一个标签页
        scheme=scheme,      # 使用 Tradimo 浅色主题
        filename='my_backtest_result.html',  # 指定输出的HTML文件名
        output_mode='save',     # 模式设为 'save' 表示保存文件
        #voloverlay=False,
        # plotconfig=plotconfig,
        volup='red',       # 上涨日的成交量设置为红色
        voldown='red'    # 下跌日的成交量设置为绿色
    )
    cerebro.plot(b)
    # scheme = PlotScheme(decimal_places=5, max_legend_text_width=16)
    # # scheme.voloverlay = False
    # figs = cerebro.plot(BacktraderPlotly(show=False, scheme=scheme))
    # for i, each_run in enumerate(figs):
    #     for j, each_strategy_fig in enumerate(each_run):
    #         # open plot in browser
    #         #each_strategy_fig.show()

    #         # save the html of the plot to a variable
    #         html = plotly.io.to_html(each_strategy_fig, full_html=False)

    #         # write html to disk
    #         plotly.io.write_html(each_strategy_fig, f'{i}_{j}.html', full_html=True, auto_play=False)

    print(thestrats)
    # 获取分析结果
    thestrat = thestrats[0]
    print(thestrat.analyzers.treturn.get_analysis())
    print(thestrat.analyzers.drawdown.get_analysis())
    print(thestrat.analyzers.sharpe.get_analysis())


    pyfolio = thestrat.analyzers.getbyname('pyfolio')
    returns, positions, transactions, gross_lev = pyfolio.get_pf_items()

    print(positions)
    print(returns)
    #returns.fillna(0, inplace=True)

    # 详细检查收益数据
    print("=== 收益数据详细分析 ===")
    print(f"数据总量: {len(returns)}")
    print(f"非空数据量: {returns.notna().sum()}")
    print(f"空值数据量: {returns.isna().sum()}")
    print(f"收益数据统计:")
    print(returns.describe())

  
    # # 清理有效数据
    # valid_returns = returns.dropna()
    # if len(valid_returns) > 0:
    #     print("使用有效数据生成报告...")
    quantstats.reports.html(returns, output="stats.html", 
                        title="策略报告", fontname='DejaVu Serif')
