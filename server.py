from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional
from core.backtest_engine import StrategyRunner
import os, json

app = FastAPI()
runner = StrategyRunner()

# 挂载静态文件
# 确保静态文件目录存在
os.makedirs("static", exist_ok=True)
os.makedirs("results", exist_ok=True)
app.mount("/results", StaticFiles(directory="results"), name="results")
app.mount("/static", StaticFiles(directory="static"), name="static")


# 模板引擎
# 确保模板目录存在
os.makedirs("templates", exist_ok=True)
templates = Jinja2Templates(directory="templates")

class BacktestRequest(BaseModel):
    strategy_name: str
    params: Optional[dict] = {}

@app.get("/", response_class=HTMLResponse)
async def get_strategy_manager(request: Request):
    """返回策略管理页面"""
    return templates.get_template("strategy-manager.html").render({"request": request})

@app.post("/api/backtest")
async def run_backtest(request: BacktestRequest):
    """执行策略回测并保存记录"""
    # 执行回测
    result = runner.run_backtest(
        strategy_name=request.strategy_name,
        **request.params
    )
    return result

@app.get("/api/records")
async def get_records(strategies_name: str):
    """获取回测记录列表"""
    res = runner.load_all_results(strategies_name)
    return res

@app.get("/api/strategies")
async def list_strategies():
    """获取可用策略列表"""
    res = runner.get_strategies()
    return {"strategies": res}


@app.get("/api/strategies/{strategy_name}/params")
async def get_strategy_params(strategy_name: str):
    """获取策略参数配置"""
    strategies = runner.get_strategies()
    for strategy in strategies:
        if strategy['name'] == strategy_name:
            return {"params": strategy['params']}
    raise HTTPException(status_code=404, detail="Strategy not found")