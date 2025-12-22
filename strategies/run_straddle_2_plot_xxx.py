import backtrader as bt
import pandas as pd
import datetime as dt
import pytz
import os
import math

# ==========================================
# 1. CONFIGURATION
# ==========================================
DATA_FOLDER = './data'
INITIAL_CAPITAL = 1_000_000
HKT = pytz.timezone('Asia/Hong_Kong')

# Date Range (HKT)
TARGET_START_HKT = dt.datetime(2025, 12, 13, 16, 5, 0)
TARGET_END_HKT   = dt.datetime(2025, 12, 14, 16, 0, 0)

SCHEDULE = [
    (dt.time(16, 5), 1/3), (dt.time(20, 0), 1/12), (dt.time(0, 0), 1/12),
    (dt.time(4, 0), 1/12), (dt.time(8, 0), 1/12), (dt.time(12, 0), 1/3)
]

# ==========================================
# 2. DATA LOADERS
# ==========================================
def get_required_filenames(start_hkt, end_hkt):
    start_utc = HKT.localize(start_hkt).astimezone(pytz.utc)
    end_utc = HKT.localize(end_hkt).astimezone(pytz.utc)
    current_date = start_utc.date()
    end_date = end_utc.date()
    file_paths = []
    while current_date <= end_date:
        filename = f"DERIBIT_BTC_{current_date.strftime('%Y-%m-%d')}.csv"
        path = os.path.join(DATA_FOLDER, filename)
        file_paths.append(path)
        current_date += dt.timedelta(days=1)
    return file_paths

def load_and_merge_data(file_paths):
    df_list = []
    use_cols = [
        'date', 'underlyer_spot', 'expiration_date', 'claim_type', 
        'strike', 'best_ask_price', 'ask_iv', 'datetime'
    ]
    print(f"\n--- Loading Files ---")
    for path in file_paths:
        if os.path.exists(path):
            print(f"Loading: {path}")
            try:
                df_temp = pd.read_csv(path, usecols=use_cols)
                df_list.append(df_temp)
            except Exception as e:
                print(f"Error reading {path}: {e}")
    
    if not df_list: return None
    df_master = pd.concat(df_list, ignore_index=True)
    
    print(df_master.head().to_dict('records'))
    
    df_master['datetime_idx'] = pd.to_datetime(df_master['date'], unit='ms').dt.tz_localize('UTC')
    df_master.set_index('datetime_idx', inplace=True)
    df_master.sort_index(inplace=True)
    return df_master

# ==========================================
# 3. CUSTOM INDICATORS (FOR PLOTTING)
# ==========================================
class TradeMarker(bt.Indicator):
    """
    Helper Indicator to plot the triangles on the main chart.
    We separate this from Strategy to ensure overlay works correctly.
    """
    lines = ('buy_entry', 'sell_exit')
    
    # Overlay on the main data (Spot Price)
    plotinfo = dict(subplot=False, plotlinelabels=True)
    
    plotlines = dict(
        # Green Up Triangle for Entry
        buy_entry=dict(marker='^', markersize=10.0, color='lime', fillstyle='full', ls=''),
        # Red Down Triangle for Exit
        sell_exit=dict(marker='v', markersize=10.0, color='red', fillstyle='full', ls='')
    )

class PnLIndicator(bt.Indicator):
    """
    Helper Indicator to plot P/L in a separate subplot.
    """
    lines = ('pnl',)
    plotinfo = dict(subplot=True, plotname='Cumulative P/L ($)')
    plotlines = dict(pnl=dict(color='blue', linewidth=2.0))

# ==========================================
# 4. STRATEGY
# ==========================================
class SpotClockData(bt.feeds.PandasData):
    params = (('datetime', None), ('close', 'spot'), ('open', -1), ('high', -1), ('low', -1), ('volume', -1), ('openinterest', -1),)

class StraddleStrategy(bt.Strategy):
    params = (('df_market', None), ('schedule', ''),)

    def __init__(self):
        self.df = self.p.df_market
        self.spot = self.datas[0]
        self.schedule = SCHEDULE
        
        print(self.df.head().to_dict('records'))
        
        # Instantiate Indicators for Plotting
        self.markers = TradeMarker(self.spot)
        self.pnl_plot = PnLIndicator(self.spot)
        
        # State Tracking
        self.open_positions = []
        self.trade_log = []
        self.last_trade_signature = None
        self.cum_pnl = 0.0

    def next(self):
        # 1. Reset Markers for this bar (default to NaN)
        self.markers.lines.buy_entry[0] = math.nan
        self.markers.lines.sell_exit[0] = math.nan
        
        # 2. Update PnL Line
        self.pnl_plot.lines.pnl[0] = self.cum_pnl

        # 3. Strategy Logic
        current_dt_utc = self.spot.datetime.datetime(0).replace(tzinfo=pytz.utc)
        current_dt_hkt = current_dt_utc.astimezone(HKT)
        
        self.process_expiries(current_dt_utc)
        self.check_schedule(current_dt_hkt, current_dt_utc)

    def process_expiries(self, current_dt_utc):
        active_positions = []
        for pos in self.open_positions:
            if current_dt_utc >= pos['expiry_dt']:
                self.settle_position(pos, current_dt_utc)
            else:
                active_positions.append(pos)
        self.open_positions = active_positions

    def settle_position(self, pos, current_dt_utc):
        settlement_spot = self.spot.close[0]
        strike = float(pos['strike'])
        
        # --- PLOT EXIT MARKER ---
        self.markers.lines.sell_exit[0] = settlement_spot

        # Calculate P/L
        call_payoff = max(0.0, settlement_spot - strike)
        put_payoff = max(0.0, strike - settlement_spot)
        
        call_cost = pos['call_ask'] * pos['entry_spot'] * pos['size']
        put_cost = pos['put_ask'] * pos['entry_spot'] * pos['size']
        
        total_pnl = ((call_payoff + put_payoff) * pos['size']) - (call_cost + put_cost)
        
        self.broker.setcash(self.broker.getcash() + total_pnl + (call_cost + put_cost)) # Simply add net P/L impact
        self.cum_pnl += total_pnl
        self.pnl_plot.lines.pnl[0] = self.cum_pnl # Update immediately

        record = {
            'Entry UTC': pos['entry_dt'].strftime('%Y-%m-%d %H:%M'),
            'Exit UTC': current_dt_utc.strftime('%Y-%m-%d %H:%M'),
            'Strike': strike,
            'Size': round(pos['size'], 4),
            'Start Spot': round(pos['entry_spot'], 2),
            'End Spot': round(settlement_spot, 2),
            'Total P/L ($)': round(total_pnl, 2),
        }
        self.trade_log.append(record)
        print(f"[SETTLE] Strike {strike} | P/L: ${total_pnl:,.2f}")

    def check_schedule(self, current_dt_hkt, current_dt_utc):
        current_time = current_dt_hkt.time()
        for sched_time, portion in self.schedule:
            if current_time.hour == sched_time.hour:
                if sched_time.minute <= current_time.minute < (sched_time.minute + 5):
                    sig = f"{current_dt_hkt.date()}_{sched_time.hour}:{sched_time.minute}"
                    if self.last_trade_signature != sig:
                        self.execute_straddle(current_dt_utc, portion)
                        self.last_trade_signature = sig

    def execute_straddle(self, current_dt_utc, portion):
        # Data Slicing & Strike Logic
        df_now = self.df[self.df.index == current_dt_utc]
        if df_now.empty: return
        current_spot = self.spot.close[0]
        
        future_mask = df_now['expiration_date'] > current_dt_utc
        valid_expiries = df_now.loc[future_mask, 'expiration_date'].unique()
        if len(valid_expiries) == 0: return
        target_expiry = min(valid_expiries)
        
        df_exp = df_now[df_now['expiration_date'] == target_expiry].copy()
        df_exp['dist'] = abs(df_exp['strike'] - current_spot)
        best_row = df_exp.sort_values('dist').iloc[0]
        target_strike = best_row['strike']
        
        legs = df_exp[df_exp['strike'] == target_strike]
        try:
            call_row = legs[legs['claim_type'] == 'call'].iloc[0]
            put_row = legs[legs['claim_type'] == 'put'].iloc[0]
        except IndexError: return 
        
        call_ask = call_row['best_ask_price']
        put_ask = put_row['best_ask_price']
        if (pd.isna(call_ask) or call_ask <= 0) or (pd.isna(put_ask) or put_ask <= 0): return

        premium_btc = call_ask + put_ask
        cost_unit_usd = premium_btc * current_spot
        size = (self.broker.getvalue() * portion) / cost_unit_usd
        total_cost = size * cost_unit_usd
        
        # Manual accounting
        self.broker.setcash(self.broker.getcash() - total_cost)
        
        # --- PLOT ENTRY MARKER ---
        self.markers.lines.buy_entry[0] = current_spot

        pos = {
            'entry_dt': current_dt_utc, 'expiry_dt': target_expiry,
            'strike': target_strike, 'size': size, 'entry_spot': current_spot,
            'call_ask': call_ask, 'put_ask': put_ask
        }
        self.open_positions.append(pos)
        print(f"[EXECUTE] Strike {target_strike} | Size {size:.4f}")

    def stop(self):
        if self.trade_log:
            pd.DataFrame(self.trade_log).to_csv('straddle_output.csv', index=False)
            print("✅ Output saved to straddle_output.csv")

# ==========================================
# 5. MAIN EXECUTION
# ==========================================

import pyfolio as pf
import quantstats
import plotly.io
import quantstats as qs
from backtrader_plotting import Bokeh
from backtrader_plotting.schemes import Tradimo

def run_strategy():
    files_needed = get_required_filenames(TARGET_START_HKT, TARGET_END_HKT)
    df = load_and_merge_data(files_needed)
    if df is None or df.empty:
        print("Error: No data loaded.")
        return

    print(df.head().to_dict('records'))
    
    start_utc_slice = HKT.localize(TARGET_START_HKT).astimezone(pytz.utc)
    end_utc_slice = HKT.localize(TARGET_END_HKT).astimezone(pytz.utc)
    df = df[(df.index >= start_utc_slice) & (df.index <= end_utc_slice)]
    df['expiration_date'] = pd.to_datetime(df['expiration_date'])
    df_spot = df[~df.index.duplicated(keep='first')][['underlyer_spot']].rename(columns={'underlyer_spot': 'spot'})


    # --- SETUP CEREBRO ---
    # stdstats=False removes the default empty Cash/Value/Trades observers
    cerebro = bt.Cerebro(stdstats=False)
    
    cerebro.addstrategy(StraddleStrategy, df_market=df)
    cerebro.adddata(SpotClockData(dataname=df_spot, name='test'))
    cerebro.broker.setcash(INITIAL_CAPITAL)

    cerebro.addanalyzer(bt.analyzers.PyFolio, _name='pyfolio', timeframe=bt.TimeFrame.Minutes)
    
    print(f"--- Starting Backtest ---")
    thestrats = cerebro.run()
    
    print("\nGENERATING CHART...")
    # 'style=line' is often clearer than candlestick for high-freq spot data
    #cerebro.plot(style='line', volume=False, iplot=False)


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
    cerebro.plot(b, volume=False,)



    thestrat = thestrats[0]
    # print(thestrat.analyzers.treturn.get_analysis())
    # print(thestrat.analyzers.drawdown.get_analysis())
    # print(thestrat.analyzers.sharpe.get_analysis())


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

    quantstats.reports.html(returns, output="stats.html", 
                    title="策略报告", fontname='DejaVu Serif')

if __name__ == '__main__':
    run_strategy()