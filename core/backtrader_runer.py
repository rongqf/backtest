import json
import os
from datetime import datetime
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['DejaVu Sans']  # 开源字体，兼容性好
plt.rcParams['axes.unicode_minus'] = False

import matplotlib.font_manager as fm
fonts = sorted(set([f.name for f in fm.fontManager.ttflist]))
print("可用字体:", fonts)


import pandas as pd
import numpy as np
import backtrader as bt
from backtrader.feeds import PandasData
import pyfolio as pf
import quantstats as qs


if not hasattr(np, 'bool8'):
    np.bool8 = np.bool_

from backtrader_plotting import Bokeh
from backtrader_plotting.schemes import Tradimo

def get_quote_data(**params):
    return pd.DataFrame([])


def run_backtest(strategy_name: str, StrategyClass, module, **params):
    """执行回测并保存结果"""

    # 初始化回测引擎
    cerebro = bt.Cerebro()

    # 设置交易资金和交易费用
    cash = float(params.get('cash', 500000))
    commission = float(params.get('commission', 0.002))
    cerebro.broker.set_cash(cash)
    cerebro.broker.setcommission(commission=commission)

    DataFeed = getattr(module, 'DataFeed', None)
    if DataFeed:
        datafeed = DataFeed(params)
        params_ = datafeed.get_strategy_params()
        # 添加自己编写的策略，opts是第1小节“策略所需数据”中提到的期权合约信息
        cerebro.addstrategy(StrategyClass, **params_)
        datafeed.add_data_to_engine(cerebro)
    else:
        code, pddata = get_quote_data(**params)
        data = PandasData(dataname=pddata, datetime='date')
        cerebro.adddata(data, name=code) 
        
    # 在执行策略之前添加分析器，我添加了3个，分别是：收益，回撤和夏普比率
    cerebro.addanalyzer(bt.analyzers.Returns, _name='treturn')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')    
    # 回测时需要添加 PyFolio 分析器
    cerebro.addanalyzer(bt.analyzers.PyFolio, _name='pyfolio')
    # 执行回测
    thestrats = cerebro.run()

    
    
    print(thestrats)
    # 获取分析结果
    thestrat = thestrats[0]
    print(thestrat.analyzers.treturn.get_analysis())
    print(thestrat.analyzers.drawdown.get_analysis())
    print(thestrat.analyzers.sharpe.get_analysis())


    pyfolio = thestrat.analyzers.getbyname('pyfolio')
    returns, positions, transactions, gross_lev = pyfolio.get_pf_items()


    # 生成结果ID
    result_id = f"{strategy_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    result_data = {
        "strategy": strategy_name,
        "parameters": params,
        "stats": '{}',
        "timestamp": datetime.now().isoformat(),
        "result_id": result_id,
    }
    
    dir = f"results/{strategy_name}"
    os.makedirs(dir, exist_ok=True)
    
    json_path = f"results/{strategy_name}/{result_id}.json"
    with open(json_path, "w") as f:
        json.dump(result_data, f, indent=4)
        
        # 生成HTML报告
    html_path = f"results/{strategy_name}/{result_id}_report.html"
    scheme=Tradimo()
    scheme.volup = 'red',
    scheme.voldown = 'red'
    # 配置 Bokeh 绘图器并保存
    b = Bokeh(
        # style='candle',        # 主图样式，例如 'candle' 为K线图
        plot_mode='single',    # 绘图模式，'single' 将所有内容放在一个标签页
        scheme=scheme,      # 使用 Tradimo 浅色主题
        filename=html_path,  # 指定输出的HTML文件名
        output_mode='save',     # 模式设为 'save' 表示保存文件
        #voloverlay=False,
        # plotconfig=plotconfig,
        volup='red',       # 上涨日的成交量设置为红色
        voldown='red'    # 下跌日的成交量设置为绿色
    )
    cerebro.plot(b)
    
     
    pf_rp_path = f"results/{strategy_name}/{result_id}_pf_report.html"
    qs.reports.html(returns, title='portfolio report', output=pf_rp_path)
       
    return {
        "status": "success",
        "result_id": result_id,
        "json_path": json_path,
        "html_path": html_path,
    }