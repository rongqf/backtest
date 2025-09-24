import importlib
import os
import json

import core.backtesting_runer as bti_runer
import core.backtrader_runer as bt_runer

def snake_to_camel(s: str) -> str:
    if not s:
        return s
    # 分割蛇形命名并转换为首字母大写
    parts = s.split('_')
    # 第一个单词小写，后续单词首字母大写
    return parts[0].capitalize() + ''.join(word.capitalize() for word in parts[1:])


def pydantic_to_html_form(model: dict) -> str:
    html = []
    for name, field in model.items():
        title = name
        input_type = {
            "str": "text",
            "int": "number",
            "date": "date",
            "bool": "checkbox"
        }.get(field.get('type', 'str'), "text")
        
        # 获取默认值
        default_value = field.get('default', '')
        
        node = []
        node.append(f'<label>{title}</label>')
        node.append(f'<input type="{input_type}" name="{name}" value="{default_value}">')
        html.append(" ".join(node))
    

    return "<br><br>".join(html)

class StrategyRunner:
    """
    策略执行引擎
    功能：
    1. 动态加载策略类
    2. 执行回测
    3. 保存结果
    """
    
    def __init__(self, strategies_dir="strategies"):
        self.strategies_dir = strategies_dir
        os.makedirs("results", exist_ok=True)
    
    def load_strategy(self, strategy_name: str):
        """动态加载策略类"""
        try:
            m = f"{self.strategies_dir}.{strategy_name}"
            print(m)
            module = importlib.import_module(m)
            print(dir(module))
            cn = snake_to_camel(strategy_name)
            print(cn)
            StrategyClass = getattr(module, cn)
            return StrategyClass, module
        except Exception as e:
            raise ValueError(f"加载策略失败: {cn}")
    
    def run_backtest(self, strategy_name: str, **params):
        StrategyClass, module = self.load_strategy(strategy_name)
        bteng = getattr(module, 'backengine') or ''
        if bteng == 'backtesting':
            return bti_runer.run_backtest(strategy_name, StrategyClass, module, **params)
        else:
            return bt_runer.run_backtest(strategy_name, StrategyClass, module, **params)
        
    # def run_backtest(self, strategy_name: str, **params):
    #     """执行回测并保存结果"""
    #     StrategyClass = self.load_strategy(strategy_name)
        
    #     # 更新策略参数
    #     for k, v in params.items():
    #         if hasattr(StrategyClass, k):
    #             setattr(StrategyClass, k, v)
        
    #     # 执行回测
    #     bt = Backtest(
    #         GOOG, 
    #         StrategyClass, 
    #         cash=1000000, 
    #         commission=.002, 
    #         finalize_trades=True,
    #         )
    #     stats = bt.run()
        
    #     # 生成结果ID
    #     result_id = f"{strategy_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        
    #     #print(stats.to_json())
    #     # 保存JSON结果
    #     result_data = {
    #         "strategy": strategy_name,
    #         "parameters": params,
    #         "stats": stats.to_json(),
    #         "timestamp": datetime.now().isoformat(),
    #         "result_id": result_id,
    #     }
        
    #     dir = f"results/{strategy_name}"
    #     os.makedirs(dir, exist_ok=True)
        
    #     json_path = f"results/{strategy_name}/{result_id}.json"
    #     with open(json_path, "w") as f:
    #         json.dump(result_data, f, indent=4)
    #         # f.write(stats.to_json(indent=4))
        
    #     # 生成HTML报告
    #     html_path = f"results/{strategy_name}/{result_id}.html"
    #     bt.plot(filename=html_path, open_browser=False)
        
    #     rp_path = f"results/{strategy_name}/{result_id}_report.html"
    #     env = Environment(loader=FileSystemLoader('./templates', encoding='utf-8'))
    #     template = env.get_template('tmp.html') 
    #     cols=[
    #         'Size',
    #         'EntryPrice',
    #         'ExitPrice',
    #         'PnL',
    #         'Commission',
    #         'EntryTime',
    #         'ExitTime',
    #         'Duration',]
    #     trades = stats._trades[cols]
    #     with open(rp_path,'w+', encoding='utf-8') as fout:   
    #         html_content = template.render(
    #             stats_data=str(stats),
    #             html_path = f"{result_id}.html",
    #             trade_data=trades.to_html(classes='table table-striped', index=False)
    #         )
    #         fout.write(html_content)

    #     returns = stats._equity_curve['Equity'].pct_change()
    #     pf_rp_path = f"results/{strategy_name}/{result_id}_pf_report.html"
    #     qs.reports.html(returns, title='portfolio report', output=pf_rp_path)
    
    #     return {
    #         "status": "success",
    #         "result_id": result_id,
    #         "json_path": json_path,
    #         "html_path": html_path
    #     }
        
    def load_all_results(self, strategy_name: str):
        results = []
        
        results_dir = f"results/{strategy_name}"
        if os.path.exists(results_dir):
            for file in os.listdir(results_dir):
                if file.endswith(".json"):
                    with open(os.path.join(results_dir, file)) as f:
                        data = json.load(f)
                        results.append({
                            "strategy_name": strategy_name,
                            "result_id": '_'.join(data["result_id"].split("_")[-2:]),
                            "params": data["parameters"],
                            "timestamp": data["timestamp"],
                            "html_path": os.path.join(results_dir, f"{data['result_id']}.html"), 
                            "json_path": os.path.join(results_dir, file),
                            "report_path": os.path.join(results_dir, f"{data['result_id']}_report.html"),
                            "pf_report_path": os.path.join(results_dir, f"{data['result_id']}_pf_report.html")
                        })
        
        print(results)
        results.sort(key=lambda x: x['timestamp'], reverse=True)
        return results
            
            
    def get_strategies(self):
        strategies = []
        for file in os.listdir(self.strategies_dir):
            if file.endswith(".py"):
                strategy_name = file[:-3]
                params = self.get_strategy_params(strategy_name)
                strategies.append({
                    'name': strategy_name,
                    'params': params
                })
        return strategies
    
    def get_strategy_params(self, strategy_name: str):
        m = f"{self.strategies_dir}.{strategy_name}"
        module = importlib.import_module(m)
        params = getattr(module, 'paramecfg')
        html = pydantic_to_html_form(params)
        return html

        
if __name__ == "__main__":
    runner = StrategyRunner()
    
    # 执行sma_cross策略回测
    result = runner.run_backtest(
        strategy_name="sma_cross",
        n1=10,
        n2=20
    )
    
    # 输出结果
    print(result)