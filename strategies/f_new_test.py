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

# test 策略
class FNewTest(bt.Strategy):
    def __init__(self):
        pass
    def prenext(self):
        self.next()         # 执行next()方法，实现买入/卖出逻辑
    def next(self):
        count = len(self.datas[0])
        if count % 7 == 0:
            self.buy()
        elif count % 8 == 0:
            self.sell()

    
class DataFeed:
    def __init__(self, paramecfg = {}):
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
        df['open'] = df['mark_price']
        df['high'] = df['mark_price']
        df['low'] = df['mark_price']
        dfs = df.groupby(['exchange', 'instrument_name', 'expiration_date'])
        n = 0
        for i, df in dfs:
            df = df.sort_values(by='datetime')
            data = FuturesDataFeed(dataname=df, datetime='datetime')
            cerebro.adddata(data, name=str(i))
            n += 1
            if n >= 1:
                break
    
        

            
if __name__ == "__main__":
    import numpy as np
    # 检查bool8是否存在，如果不存在，则将其指向np.bool_
    if not hasattr(np, 'bool8'):
        np.bool8 = np.bool_
    import matplotlib.pyplot as plt
    plt.rcParams['font.family'] = 'DejaVu Serif'  # 设置全局默认字体为DejaVu Sans
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

    datafeed = DataFeed(paramecfg)
    params = datafeed.get_strategy_params()
    # 添加自己编写的策略，opts是第1小节“策略所需数据”中提到的期权合约信息
    cerebro.addstrategy(SmaCross, **params)
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
        'id:volsma': dict(
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
        voloverlay=True,
        plotconfig=plotconfig,
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
