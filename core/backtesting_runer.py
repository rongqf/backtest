import json
import os
from datetime import datetime
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['DejaVu Sans']  # 开源字体，兼容性好
plt.rcParams['axes.unicode_minus'] = False

import matplotlib.font_manager as fm
fonts = sorted(set([f.name for f in fm.fontManager.ttflist]))
print("可用字体:", fonts)

from backtesting import Backtest
import quantstats as qs
from backtesting.test import GOOG
from jinja2 import Template
from jinja2 import Environment, FileSystemLoader


def run_backtest(strategy_name: str, StrategyClass, module, **params):
    """执行回测并保存结果"""

    # 更新策略参数
    for k, v in params.items():
        if hasattr(StrategyClass, k):
            setattr(StrategyClass, k, v)
    
    # 执行回测
    bt = Backtest(
        GOOG, 
        StrategyClass, 
        cash=1000000, 
        commission=.002, 
        finalize_trades=True,
        )
    stats = bt.run()
    
    # 生成结果ID
    result_id = f"{strategy_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    
    #print(stats.to_json())
    # 保存JSON结果
    result_data = {
        "strategy": strategy_name,
        "parameters": params,
        "stats": stats.to_json(),
        "timestamp": datetime.now().isoformat(),
        "result_id": result_id,
    }
    
    dir = f"results/{strategy_name}"
    os.makedirs(dir, exist_ok=True)
    
    json_path = f"results/{strategy_name}/{result_id}.json"
    with open(json_path, "w") as f:
        json.dump(result_data, f, indent=4)
        # f.write(stats.to_json(indent=4))
    
    # 生成HTML报告
    html_path = f"results/{strategy_name}/{result_id}.html"
    bt.plot(filename=html_path, open_browser=False)
    
    rp_path = f"results/{strategy_name}/{result_id}_report.html"
    env = Environment(loader=FileSystemLoader('./templates', encoding='utf-8'))
    template = env.get_template('tmp.html') 
    cols=[
        'Size',
        'EntryPrice',
        'ExitPrice',
        'PnL',
        'Commission',
        'EntryTime',
        'ExitTime',
        'Duration',]
    trades = stats._trades[cols]
    with open(rp_path,'w+', encoding='utf-8') as fout:   
        html_content = template.render(
            stats_data=str(stats),
            html_path = f"{result_id}.html",
            trade_data=trades.to_html(classes='table table-striped', index=False)
        )
        fout.write(html_content)

    returns = stats._equity_curve['Equity'].pct_change()
    pf_rp_path = f"results/{strategy_name}/{result_id}_pf_report.html"
    qs.reports.html(returns, title='portfolio report', output=pf_rp_path)

    return {
        "status": "success",
        "result_id": result_id,
        "json_path": json_path,
        "html_path": html_path
    }
    