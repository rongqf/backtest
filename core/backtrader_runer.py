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
import backtrader as bt
from backtrader.feeds import PandasData
import pyfolio as pf
import quantstats as qs



def get_quote_data(**params):
    return pd.DataFrame([])


def run_backtest(strategy_name: str, StrategyClass, module, **params):
    """执行回测并保存结果"""

    # 初始化回测引擎
    cerebro = bt.Cerebro()

    # 设置交易资金和交易费用
    cerebro.broker.set_cash(500000)
    cerebro.broker.setcommission(commission=0.002)

    DataFeed = getattr(module, 'DataFeed', None)
    if DataFeed:
        datafeed = DataFeed()
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

    # 设置回测结果中不显示期权K线
    for d in cerebro.datas:
        d.plotinfo.plot = False
        
    # 显示策略运行结果
    #cerebro.plot(iplot=False)

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
     
    pf_rp_path = f"results/{strategy_name}/{result_id}_pf_report.html"
    qs.reports.html(returns, title='portfolio report', output=pf_rp_path)
       
    return {
        "status": "success",
        "result_id": result_id,
        "json_path": json_path,
        "html_path": ''
    }