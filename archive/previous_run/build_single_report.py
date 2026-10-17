import json
from pathlib import Path
import pandas as pd

ROOT=Path(__file__).resolve().parent
OUT=ROOT.parent/'outputs'
d=json.loads((ROOT/'single_backtest.json').read_text(encoding='utf-8'))
s=pd.DataFrame(d['summary'])
label={'Hist':'MACD Histogram','Stoch':'Stochastic','MOM':'Momentum','VWMACD':'VWmacd','CMF':'Chaikin Money Flow','MFI':'Money Flow Index'}

def tbl(df,columns):
    a=df[columns].copy()
    for c in a.columns:
        if c=='name':a[c]=a[c].map(lambda x:label.get(x,x))
        elif c in ['hit','net_win','total_return','maxdd','mean_net','hit_low','hit_high']:a[c]=a[c].map(lambda x:f'{x*100:.2f}%')
        elif c=='ending':a[c]=a[c].map(lambda x:f'{x:,.2f}')
        elif c=='profit_factor':a[c]=a[c].map(lambda x:f'{x:.2f}' if pd.notna(x) else '—')
    a=a.rename(columns={'name':'唯一启用指标','tf':'周期','n':'交易数','hit':'方向准确率','net_win':'扣费胜率','total_return':'累计净收益','maxdd':'收盘权益最大回撤','mean_net':'每笔平均净收益','ending':'期末权益(USDT)','profit_factor':'盈利因子','raw':'原始信号','skipped':'持仓忽略','tail':'期末未完成排除','conflict':'同根多空冲突排除','long_count':'做多笔数','short_count':'做空笔数','hit_low':'准确率95%下界','hit_high':'准确率95%上界'})
    return '<div class="scroll">'+a.to_html(index=False,border=0)+'</div>'

parts=['''<header><p>BINANCE BTCUSDT USDT 永续合约</p><h1>20组单指标背离回测报告</h1><p>2026年10月16日制作 · 10个指标 × 4H / 1D · 固定持有10根 · 组内单仓不重叠</p></header>
<section><h2>范围与执行状态</h2><p>20组已全部完成。每组仅启用一个指标，底背离做多、顶背离做空，多空共用一个仓位。持仓期间忽略全部新信号，平仓后才接受下一笔。不同指标是独立实验，可覆盖相同历史时段，收益不得相加。</p><p>本轮仅报告单指标结果，不测试指标组合、不推荐额外操作，也不事后选择最优持有期。</p><p>全期：2021-01-01～2026-10-15（UTC）。2020年用于预热。前段2021～2024、后段2025～2026-10-15分别重新从10,000 USDT开始复核；后段数据已在上一轮看过，不是新的盲测样本。</p></section>
<section><h2>固定计划与规则</h2><table><tr><th>项目</th><th>统一规则</th></tr>
<tr><td>市场数据</td><td>Binance BTCUSDT USDT本位永续，标准成交价OHLCV；日线UTC 00:00，即北京时间08:00开始。</td></tr>
<tr><td>背离算法</td><td>按原始 Pine v4 代码本地复现：Regular、Close、Pivot Period=5、最大10个拐点、回看100根；最少背离数量=1。</td></tr>
<tr><td>信号确认</td><td>Don’t Wait for Confirmation不勾选，并只记录当前K线收盘仍有效的信号。按实际检测时间入场，不回填到历史拐点。</td></tr>
<tr><td>入场及退出</td><td>信号后的下一根开盘入场，第10根持仓K线收盘退出。4H=40小时，1D=10天。无止盈止损、反向提前平仓和加仓。</td></tr>
<tr><td>不重叠</td><td>同一组任意时刻最多一笔多仓或空仓。退出当根收盘可接受新信号，于下一根开盘成交。未能完成10根持有期的期末信号不入场。</td></tr>
<tr><td>资金规模</td><td>每组初始10,000 USDT；预留开仓手续费后，使用剩余权益作为开仓名义金额，约1倍敞口；逐笔复投。</td></tr>
<tr><td>成本</td><td>假设单边手续费0.05%、单边不利滑点0.02%，另计历史资金费支付/收入。不是账户实际费率。</td></tr>
<tr><td>参数口径</td><td>RSI(14)、MACD(12,26,9)、Stoch(14)平滑3、CCI(close,10)、Momentum(10)、OBV、VWMA(12)-VWMA(26)、CMF(21)、MFI(close,14)。</td></tr>
<tr><td>外部指标</td><td>Check External Indicator是外部输入接口，没有独立定义；不属于本轮10个内置指标。</td></tr>
</table></section>''']

parts.append('<section><h2>最高与最低：全期主比较</h2><table><tr><th>周期</th><th>比较项目</th><th>指标</th><th>结果</th><th>交易数</th></tr>')
for tf in ['4H','1D']:
    a=s[(s.tf==tf)&(s.period=='全期')]
    for metric,title in [('hit','方向准确率最高'),('hit','方向准确率最低'),('total_return','累计净收益最高'),('total_return','累计净收益最低')]:
        r=a.loc[a[metric].idxmax() if '最高' in title else a[metric].idxmin()]
        parts.append(f'<tr><td>{tf}</td><td>{title}</td><td>{label.get(r["name"],r["name"])}</td><td>{100*r[metric]:.2f}%</td><td>{r["n"]}</td></tr>')
parts.append('</table><p class="note">准确率衡量价格方向，累计净收益衡量带成本的复投账户。两种排名不相同。4H全期多数指标净亏损；日线结果不能直接外推到4H。</p></section>')

for tf in ['4H','1D']:
    a=s[(s.tf==tf)&(s.period=='全期')].sort_values('total_return',ascending=False)
    parts.append(f'<section><h2>{tf}：全部10项独立结果</h2><p>2021-01-01～2026-10-15，按累计净收益降序。每项独立从10,000 USDT开始。</p>')
    parts.append(tbl(a,['name','n','hit','net_win','total_return','ending','maxdd','mean_net','profit_factor']))
    parts.append('</section>')

parts.append('<section><h2>前后段复核</h2><p>规则没有变化。每段独立启动单仓模拟；跨越区间终点、未完成10根持有的交易不进入该段。全期连续账户不在2025年人为重置，所以两个分段不能简单相加。</p>')
for period,title in [('前段','2021～2024'),('后段','2025～2026-10-15')]:
    for tf in ['4H','1D']:
        a=s[(s.tf==tf)&(s.period==period)].sort_values('total_return',ascending=False)
        parts.append(f'<h3>{tf} {title}</h3>'+tbl(a,['name','n','hit','net_win','total_return','maxdd']))
parts.append('</section>')

parts.append('<section><h2>20组计划执行与信号去重记录</h2><p>每行均已完成。原始信号=完成交易+持仓期间忽略+期末未完成排除+同根多空冲突排除。</p>')
parts.append(tbl(s[s.period=='全期'],['tf','name','raw','n','skipped','tail','conflict','long_count','short_count']))
parts.append('</section>')

parts.append('''<section><h2>指标定义</h2><ul>
<li>方向准确率：做多退出原始价格高于入场原始价格，或做空退出原始价格低于入场原始价格的笔数/总笔数。持平不算命中。</li>
<li>扣费胜率：扣除手续费、滑点和资金费后，净收益大于0的笔数/总笔数。资金费收入可能使方向未命中的交易净盈利。</li>
<li>累计净收益：期末权益/初始权益−1；按实际逐笔资金规模复投，已扣成本。不是所有每笔收益率简单相加。</li>
<li>每笔平均净收益：每笔净损益/该笔开仓名义金额的算术平均，不代表年化收益。</li>
<li>盈利因子：所有盈利交易的USDT净收益之和/所有亏损交易的USDT亏损绝对值之和。</li>
<li>最大回撤：根据持仓期间每根K线收盘权益计算，含浮盈亏、手续费及截至当时的资金费；不等同于盘中最高回撤。</li>
</ul></section>
<section><h2>校验与边界</h2><ul>
<li>20组主实验全部完成，主实验共2349笔。前后段独立复核包含在Excel逐笔明细中，不得把重合区间累加。</li>
<li>已重新计算所有指标与背离信号，并核对先前通过逐行检查的信号数组；验证同组所有多空交易均不重叠、入场与持有时长正确、资金变化逐笔勾稽。</li>
<li>使用交替多空的合成序列测试，验证反向信号也会在持仓期间被忽略。原始数据连续无重复，日线OHLC与六根4H聚合一致。</li>
<li>日线成交量在2023-08-16和2023-11-10与4H聚合不同，API复查值一致。本次保留币安各周期原始数据。</li>
<li>资金费6342条，其中3100条无标记价，使用该时点4H开盘价代理。资金费用是估算，特别是早期数据。</li>
<li>这是本地Python复现，不是TradingView策略测试器实跑，也未和TradingView逐根导出交叉核验。未模拟杠杆、强平、盘中止损及真实订单成交约束。</li>
<li>本轮只测试固定10根持有规则。排名最高不等于其他持有时间、行情阶段也最高；日线交易数少，后段部分指标只有个位数交易。</li>
</ul><p>数据源：<a href="https://fapi.binance.com/fapi/v1/klines?symbol=BTCUSDT&amp;interval=4h&amp;limit=1">Binance合约K线接口</a>、<a href="https://fapi.binance.com/fapi/v1/fundingRate?symbol=BTCUSDT&amp;limit=1">历史资金费率接口</a>。策略时序参考：<a href="https://www.tradingview.com/pine-script-docs/concepts/strategies/">TradingView官方策略文档</a>。</p></section>''')

css='''body{margin:0;background:#f1f5f9;color:#193044;font:16px/1.65 "Microsoft YaHei",Arial,sans-serif}main{max-width:1350px;margin:auto;padding:28px}header{padding:26px 30px;background:#183b56;color:white;border-radius:14px}h1{font-size:30px;margin:8px 0}h2{font-size:23px}h3{font-size:19px}section{padding:24px;background:white;border:1px solid #dbe3eb;border-radius:12px;margin:20px 0}.scroll{overflow:auto}table{border-collapse:collapse;width:100%;font-size:14px}th,td{padding:10px 12px;border-bottom:1px solid #dfe7ed;text-align:right}th{background:#edf3f8;color:#173850}th:first-child,td:first-child{text-align:left}.scroll td,.scroll th{white-space:nowrap}tr:nth-child(even){background:#f8fafc}.note{background:#fff5db;border-left:4px solid #e3aa2c;padding:12px}a{color:#075c99}li{margin:8px 0}@media(max-width:700px){main{padding:10px}section{padding:15px}h1{font-size:24px}}'''
target=OUT/'BTCUSDT_20组单指标准确率与收益报告.html'
target.write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>20组单指标回测报告</title><style>'+css+'</style><main>'+''.join(parts)+'</main></html>',encoding='utf-8')
print(target)
