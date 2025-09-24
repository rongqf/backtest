import pandas as pd
import backtrader as bt
from backtrader.feeds import PandasData

# Covered Call 策略
class CoveredCallStrategy(bt.Strategy):
    params = (
        ('opts', None),             # 期权合约信息
        ('etf_size', 10000),        # 每手期权对应的基金份数
    )
    
    def __init__(self):
        self.month = None
        self.num_of_day = 0 
    
    def prenext(self):
        self.next()         # 执行next()方法，实现买入/卖出逻辑
        
    def next(self):
        today = self.datetime.date()
        print('next', today)
        # 判断是否是调仓日
        if self.is_adjust_day():
        
            # 如果还没有买入ETF仓位，则买入。
            if not self.getposition(self.datas[0]) :
                order = self.buy(self.datas[0], size=self.params.etf_size)
                order.addinfo(ticker=self.datas[0]._name)   
                print('='*50)
            
            # 如果已经持有期权仓位，则平仓。
            for d in self.datas[1:]:
                if self.getposition(d):
                    # 平掉已持仓期权
                    order = self.buy(d, size=self.params.etf_size)
                    order.addinfo(ticker=d._name)
                    
            # 获取比现价高两档的认购期权
            opt = self.get_opt(otype='call', pos=2, when=1)
            if opt:
                # 卖出期权
                d = self.getdatabyname(opt)
                order = self.sell(d, size=self.params.etf_size)
                order.addinfo(ticker=opt)
            else:
                print('没有找到可以卖出的期权。')
            
        return

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
    
    
    def is_adjust_day(self, dom=1):
        '''
        判断是否是每月的调仓日。        
        :params int dom: 每月第几个交易日进行调仓，缺省是第1个交易日。
        :return: 如果是调仓日，返回True，否则返回False。
        '''
        
        ret = False
        today = self.datetime.date()
        
        if self.month is None or self.month != today.month:
            self.month = today.month
            self.num_of_days = 1
        else:
            self.num_of_days += 1
            
        if self.num_of_days == dom:
            ret = True
            
        return ret

    def get_opt(self, otype='call', pos=1, when=1):
        '''
        根据ETF当前价格获取期权。
        
        :params str otype: 期权类型，call或者put。
        :params int pos: 期权的位置，正数表示比当前标的价格高几档，负数表示比当前期权价格低几档。
        :params int when: 期权的到期日期，0/1/2/3分别表示当月/下月/当季/下季。
        :return: 期权代码，如果没有找到则返回None。
        '''
        
        etf_price = self.datas[0].close[0]
        
        # 获取期权的到期日期
        m = self.get_maturity(when=when)
        
        # 筛选这个到日期的期权并按照行权价由低到高排序
        d = self.params.opts
        d = d[ (d['maturity'] == m) & (d['type'] == otype) ]
        d = d.sort_values(by=['strike'])
        
        # 建立一个按照行权价由低到高排列的期权代码列表
        option_codes = []
        pos_etf = 0
        for _, row in d.iterrows():
            if row['strike'] >= etf_price :
                if pos_etf == 0 :
                    option_codes.append(None)
                    pos_etf = len(option_codes) - 1
                option_codes.append(row['code'])
        
        # 返回需要的期权代码
        idx = pos_etf + pos
        if idx >=0 and idx < len(option_codes) :
            return option_codes[idx]
        else:
            return None

    def get_maturity(self, when=1):
        '''
        获取期权的结束日期
        
        :param int when: 哪一个到期日期。0/1/2/3分别表示当月/下月/当季/下季的到期日期。
        :return: 期权的到期日期
        '''
        
        # 获取所有已经开始交易的期权代码
        trading_codes = []
        for d in self.datas:
            if len(d) > 0:
                trading_codes.append(d._name)

        # 选出到期日期大于等于今天的期权合约
        df = self.params.opts
        df = df[ df['maturity'] >= pd.to_datetime(self.datetime.date()) ]

        # 现在可以交易的期权的到期日期列表，按照从小到大排序
        m_list = sorted(list(set(df[df['code'].isin(trading_codes)]['maturity'])))

        # 如果给的参数不符合要求，返回最后一个日期
        if when >= len(m_list):
            when = len(m_list) - 1
        

        return m_list[when]


opts = pd.read_excel('300etf期权列表.xlsx')
opts['code'] = opts['code'].map(str)
opts['maturity'] = pd.to_datetime(opts['maturity'])
opts['settle_date'] = pd.to_datetime(opts['settle_date'])
opts = opts[opts['type'] == 'call']
print(opts.head())
df = pd.read_excel('300etf期权.xlsx')
df = df[df['type'] == 'call']
df['code'] = df['code'].map(str)
del df['trade_date']
del df['maturity']
del df['type']
del df['strike']
col = df.pop("code")
df.insert(loc=0, column="code", value=col)

ks = list(set(df['code']))
ks = ks[:]
opts = opts[opts['code'].isin(ks)]
df = df[df['code'].isin(ks)]

print(df.head())

etf = pd.read_excel('300etf.xlsx')
etf = etf[etf['date'] >= pd.to_datetime('2025/3/31')]
print(etf.head())

# 初始化回测引擎
cerebro = bt.Cerebro()

# 设置交易资金和交易费用
cerebro.broker.set_cash(500000)
cerebro.broker.setcommission(commission=0.002)

# 添加自己编写的策略，opts是第1小节“策略所需数据”中提到的期权合约信息
cerebro.addstrategy(CoveredCallStrategy, opts=opts)

# 添加ETF日线数据到回测引擎。ETF是159919。日线数据在策略中通过self.datas[0]来引用，
data = PandasData(dataname=etf, datetime='date')

cerebro.adddata(data, name='159919') 


# d = df[df['code']=='90005902'].iloc[:,1:]
# data = PandasData(dataname=d, datetime='date')
# cerebro.adddata(data, name='90005902') 

# 添加期权数据到回测引擎

print(ks)
for opt in ks[:]:
    d = df[df['code']==opt].iloc[:,1:]
    data = PandasData(dataname=d, datetime='date')
    cerebro.adddata(data, name=opt)
    
# 在执行策略之前添加分析器，我添加了3个，分别是：收益，回撤和夏普比率
cerebro.addanalyzer(bt.analyzers.Returns, _name='treturn')
cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')    
# 回测时需要添加 PyFolio 分析器
cerebro.addanalyzer(bt.analyzers.PyFolio, _name='pyfolio')
    
# 执行回测
thestrats = cerebro.run()


# 设置回测结果中不显示期权K线
# 设置回测结果中不显示期权K线
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


import pyfolio as pf


pyfolio = thestrat.analyzers.getbyname('pyfolio')
returns, positions, transactions, gross_lev = pyfolio.get_pf_items()

print(positions)
import quantstats
quantstats.reports.html(returns, output="stats.html", title="Strategy Report")
