from core.backtest_engine import StrategyRunner

# 示例用法
if __name__ == "__main__":
    runner = StrategyRunner()
    
    # runner.load_all_results("sma_cross")
    # 执行sma_cross策略回测
    result = runner.run_backtest(
        strategy_name="vol_sma"
    )
    
    print(f"回测完成！结果保存位置:")
    print(f"- JSON: {result['json_path']}")
    print(f"- HTML: {result['html_path']}")
    