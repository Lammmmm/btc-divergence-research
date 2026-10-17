import hashlib
import html
import json
from pathlib import Path
import zipfile
import pandas as pd

ROOT=Path(__file__).resolve().parent
OUT=ROOT.parent/'outputs'
OUT.mkdir(exist_ok=True)
d=pd.DataFrame(json.loads((ROOT/'results.json').read_text()))
t=pd.DataFrame(json.loads((ROOT/'trades.json').read_text()))
t['year']=pd.to_datetime(t.entry_time,unit='ms',utc=True).dt.year
NAMES=['MACD','Hist','RSI','Stoch','CCI','MOM','OBV','VWMACD','CMF','MFI']
labels={'Hist':'MACD Histogram','Stoch':'Stochastic','MOM':'Momentum','CMF':'Chaikin Money Flow','MFI':'Money Flow Index','VWMACD':'VWmacd','Current4_atleast1':'当前4项：至少1项','Current4_atleast2':'当前4项：至少2项','Current4_atleast3':'当前4项：至少3项','All10_atleast1':'全部10项：至少1项','All10_atleast2':'全部10项：至少2项','All10_atleast3':'全部10项：至少3项','Explore_OBV_Stoch_atleast1':'OBV + Stoch：至少1项（探索）','Explore_OBV_Stoch_atleast2':'OBV + Stoch：至少2项（探索）','Explore_Hist_RSI_atleast1':'Hist + RSI：至少1项（探索）','Explore_Hist_RSI_atleast2':'Hist + RSI：至少2项（探索）'}
side_labels={'bottom':'底背离/做多','top':'顶背离/做空','both':'多空事件汇总'}

def table(frame,columns):
    f=frame[columns].copy()
    for col in f.columns:
        if col=='name': f[col]=f[col].map(lambda x:labels.get(x,x))
        elif col=='side': f[col]=f[col].map(side_labels)
        elif col=='n': f[col]=f[col].astype(int)
        elif col.endswith('_pct'): f[col]=f[col].map(lambda x:f'{x:.2f}%')
        elif col=='profit_factor': f[col]=f[col].map(lambda x:f'{x:.2f}' if pd.notna(x) else '—')
    f=f.rename(columns={'name':'指标/组合','side':'方向','n':'已完成事件','hit_pct':'方向命中率','net_win_pct':'净盈利比例','mean_net_pct':'平均每笔净收益','mean_gross_pct':'平均方向收益','profit_factor':'盈利因子','ci_low_pct':'命中率下界*','ci_high_pct':'命中率上界*'})
    return '<div class="table-wrap">'+f.to_html(index=False,escape=True,border=0)+'</div>'

parts=['''<header><p class="eyebrow">BINANCE BTCUSDT USDT 永续 · 4H / 1D</p><h1>背离指标选择：实际历史回测</h1><p>计算日期：2026-10-16（北京时间）｜本地 Python 复现用户 Pine v4 算法，非 TradingView 策略测试器实跑。</p></header>
<section><h2>先看结论</h2><div class="cards"><article><h3>4H：OBV 保留，Stochastic 候选</h3><p>近期 Stochastic 方向命中率 70.0%，平均净收益 +0.202%；OBV 为 57.3%、+0.074%。但 Stoch 前段平均净收益为负，OBV 的优势也很小，尚不足以认定长期有效。</p><p>CCI、VWmacd、CMF 在后段的 5/10/20 根持有期全部为负，可以降低优先级。RSI 在本次 4H 口径下没有显示优势。</p></article><article><h3>1D：优先观察 Hist，RSI 用于同向筛选</h3><p>MACD Histogram 的 10 根持有期在前段、后段均为正，而且逐年平均净收益均为正；MACD 主线后段表现明显较差。</p><p>Hist + RSI 同向同时出现的探索组合，后段仅 10 笔：命中率 70.0%、平均净收益 +2.055%。样本少，组合是在看过单项结果后提出的，需用后续新数据验证。</p></article></div>
<p class="note">用于下一轮模拟观察的勾选方案：4H 勾 Stochastic + OBV，Minimum Number of Divergence = 1；1D 勾 MACD Histogram + RSI，Minimum Number of Divergence = 2。这是探索性筛选方案，不是已经证实的最优交易策略。4H 两项同时出现并不更好：后段 17 笔，平均净收益 −0.257%。</p></section>
<section><h2>统一回测口径</h2><ul>
<li>原始数据：币安 USDⓈ-M BTCUSDT 永续合约成交价 OHLCV，2020-01-01 至 2026-10-15（UTC），只取完整 K 线。2020 年仅用于指标预热。</li>
<li>正式评估：2021-01-01 至 2026-10-15。前段：2021–2024；后段：2025-01-01 至 2026-10-15。日线按 UTC 00:00 划分，即北京时间 08:00。</li>
<li>沿用原脚本：普通背离 Regular、Close 价格源、Pivot Period = 5、最多 10 个拐点、最多回看 100 根，Don't Wait for Confirmation 关闭。未回测隐藏背离；外部指标未启用。截图未展示的参数采用原脚本默认值。</li>
<li>保留 RSI(14)、MACD(12,26,9)、Stoch(14) 平滑3、CCI(close,10)、Momentum(10)、OBV、VWMA(12)-VWMA(26)、CMF(21)、MFI(close,14)。尤其 CCI 与 MFI 均使用原脚本指定的 close。</li>
<li>在实际检测到信号的那根收盘后，下一根开盘入场；固定持有 5、10、20 根，最后一根收盘退出。主比较为 10 根：4H=40小时，1D=10天。不是回填到历史拐点买卖。</li>
<li>底背离按做多收益，顶背离按做空收益；无止盈止损、无杠杆。每个指标/组合、每个方向独立计数，该方向持有期间忽略新信号，退出当根收盘的新信号可下一根开盘进入。未完成持有期的事件不计；跨越前后段边界的事件排除。</li>
<li>手续费假设单边 0.05%，滑点单边 0.02%，按成交额计算；不是账户实际费率。另按真实历史资金费率计入支付/收取。6,342 条资金记录中 3,100 条没有标记价，用当时 4H 开盘价代理，所以资金费用属于估算。</li>
<li>命中率=退出价相对入场原始开盘价方向正确的比例，尚未扣成本；净盈利比例与平均净收益包含手续费、滑点和资金费。持平计入分母但不算命中。</li>
<li>多空汇总是独立事件的平均结果，不是单账户组合权益曲线。不同指标可能使用同一段行情，不能相加为独立获利次数，也不能由平均每笔收益推算年化或最大回撤。</li>
</ul><p>原脚本会删换历史标签，本统计直接记录当时已经确认的条件，不按最终留下的标签挑样本；组合要求同一根、同方向达到数量。检查到本样本普通背离没有同根多空混合，数量口径与原脚本设置相符。</p></section>''']

cols=['name','n','hit_pct','net_win_pct','mean_net_pct','profit_factor']
for tf,title in [('4h','4H'),('1d','1D')]:
    base=d[(d.tf==tf)&d.name.isin(NAMES)&(d.h==10)&(d.side=='both')]
    parts.append(f'<section><h2>{title} · 单指标排行（持有10根）</h2><p>按平均每笔净收益降序排列，不是按命中率排序。后段只是时间切分检验；从这些结果挑选新方案仍有选择偏差。</p><h3>后段：2025–2026-10-15</h3>')
    parts.append(table(base[base.split=='validation'].sort_values('mean_net_pct',ascending=False),cols))
    parts.append('<h3>全期：2021–2026-10-15</h3>')
    parts.append(table(base[base.split=='all'].sort_values('mean_net_pct',ascending=False),cols))
    parts.append('<h3>前段：2021–2024</h3>')
    parts.append(table(base[base.split=='development'].sort_values('mean_net_pct',ascending=False),cols))
    parts.append('</section>')

parts.append('<section><h2>当前勾选与候选组合</h2><p>当前4项=MACD、RSI、OBV、MFI。探索组合在单项结果出炉后补测，不是独立的样本外发现；不把组合的高胜率当成确定优势。</p>')
for tf in ['4h','1d']:
    rows=d[(d.tf==tf)&~d.name.isin(NAMES+['AlwaysDirection'])&(d.h==10)&(d.side=='both')&(d.split=='validation')]
    parts.append(f'<h3>{tf.upper()} · 后段、持有10根</h3>'+table(rows,cols))
parts.append('</section>')

parts.append('<section><h2>持有时间敏感性</h2><p>下表为后段平均每笔净收益。5、10、20 根会产生不同的去重及已完成样本集合，不是同一批信号的简单延长。</p>')
for tf in ['4h','1d']:
    a=d[(d.tf==tf)&d.name.isin(NAMES)&(d.side=='both')&(d.split=='validation')]
    pivot=a.pivot(index='name',columns='h',values='mean_net_pct').reindex(NAMES)
    pivot.index=[labels.get(x,x) for x in pivot.index]
    pivot.columns=['持有5根','持有10根','持有20根']
    pivot=pivot.map(lambda x:f'{x:+.3f}%')
    parts.append(f'<h3>{tf.upper()}</h3><div class="table-wrap">'+pivot.to_html(border=0)+'</div>')
parts.append('</section>')

parts.append('<section><h2>顶、底背离分开看</h2><p>同一指标的顶背离与底背离可能表现相反；尤其日线分方向后每组样本更少。</p>')
for tf in ['4h','1d']:
    a=d[(d.tf==tf)&d.name.isin(NAMES)&(d.h==10)&(d.side!='both')&(d.split=='validation')]
    parts.append(f'<h3>{tf.upper()} · 后段、持有10根</h3>'+table(a,['name','side','n','hit_pct','mean_net_pct']))
parts.append('</section>')

parts.append('<section><h2>逐年检查</h2><p>每格为“平均净收益 / 事件数”，按入场年份划分，持有10根。2026 年截至10月15日。均为正也不等于统计显著，日线每年往往只有几笔。</p>')
for tf in ['4h','1d']:
    a=t[(t.tf==tf)&t.name.isin(NAMES)&(t.h==10)]
    g=a.groupby(['name','year']).net.agg(['mean','count'])
    g['display']=g.apply(lambda r:f"{100*r['mean']:+.2f}% / {int(r['count'])}",axis=1)
    p=g.display.unstack().reindex(NAMES)
    parts.append(f'<h3>{tf.upper()}</h3><div class="table-wrap">'+p.to_html(border=0)+'</div>')
parts.append('</section>')

parts.append('''<section><h2>结论的边界与校验</h2><ul>
<li>1D 后段各单项只有 4–14 笔（10根口径）；CCI 75% 命中率只有4笔，不能据此认定它最好。4H Stoch 近期70%是50笔，全期命中率约55.9%，平均净收益仍为负。</li>
<li>4H OBV 的全期平均净收益约+0.055%，后段约+0.074%，优势很薄；更高实际成本可以抹掉这一优势。不能把这个排名当作无需风控的开仓规则。</li>
<li>已检查：全部 K 线连续且无重复；日线 OHLC 与6根4H聚合一致；裁掉未来数据不会改变过去指标/信号；每周期120个事件/非事件用独立逐行算法核对；验证入场时间、持有期、同方向不重叠、跨分段泄露与多空成本符号。</li>
<li>日线成交量有两天与4H聚合不同：2023-08-16（272,023.138 对 280,542.952 BTC）、2023-11-10（299,373.892 对 287,320.597 BTC）。复查日线 API 返回一致；保留原生周期数据，未擅自修改。</li>
<li>未与 TradingView 同时逐根导出结果进行交叉核验；这是经过内部校验的本地复现，不宣称与 TradingView 撮合器完全一致。历史价格与成交量供应差异、初始化、真实费用、资金费时间和滑点均可能影响结果。</li>
<li>这是固定持有时间的事件回测，不包含止盈止损、杠杆、爆仓模拟，也不提供完整资金曲线。后段已被查看，后续再调参应使用新的前向样本验证。</li>
</ul><p>数据接口：<a href="https://fapi.binance.com/fapi/v1/klines?symbol=BTCUSDT&amp;interval=4h&amp;limit=1">Binance 合约 K 线</a> · <a href="https://fapi.binance.com/fapi/v1/fundingRate?symbol=BTCUSDT&amp;limit=1">历史资金费率</a>。已下载的原始响应、逐笔事件、统计结果与复现代码均在随附 ZIP 中。</p></section>''')

css='''body{font:16px/1.65 "Microsoft YaHei",Arial,sans-serif;background:#f3f5f8;color:#182333;margin:0}main{max-width:1180px;margin:auto;padding:28px}header{background:#102b44;color:white;padding:32px;border-radius:16px}h1{font-size:32px;margin:5px 0}h2{font-size:24px;color:#12324e}h3{font-size:19px}.eyebrow{letter-spacing:1px;color:#a7dbff}section{background:white;padding:24px 28px;margin:20px 0;border-radius:12px;border:1px solid #dce3eb}.cards{display:grid;grid-template-columns:1fr 1fr;gap:18px}article{padding:12px 20px;background:#f3f7fb;border-radius:10px}.note{padding:15px;border-left:4px solid #dd9a21;background:#fff8e8}.table-wrap{overflow-x:auto;margin:16px 0}table{width:100%;border-collapse:collapse;font-size:14px;white-space:nowrap}th{background:#e9f0f6;text-align:right}td,th{padding:9px 11px;border-bottom:1px solid #e0e5eb}td:first-child,th:first-child{text-align:left}td{text-align:right}tr:nth-child(even){background:#f8fafc}li{margin:8px 0}a{color:#0062ad}@media(max-width:700px){main{padding:10px}.cards{grid-template-columns:1fr}section{padding:16px}h1{font-size:26px}}'''
doc='<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>BTCUSDT 永续背离回测报告</title><style>'+css+'</style><main>'+''.join(parts)+'</main></html>'
report=OUT/'BTCUSDT_Divergence_Backtest.html'
report.write_text(doc,encoding='utf-8')

readme='''BTCUSDT perpetual divergence research backtest
==============================================
Analysis date: 2026-10-16 Asia/Shanghai.
Read BTCUSDT_Divergence_Backtest.html for assumptions, limitations and tables.
Data frozen at 2026-10-16 00:00 UTC (exclusive); 2020 is warmup only.

Reproduce from this directory (Python 3, numpy, pandas, requests):
  python backtest_divergence.py
  python verify_backtest.py
Raw JSON is included. fetch_market.py optionally downloads only missing caches.
No authentication, account access, keys, orders or trading APIs are used.

results.json contains summaries for 5/10/20-bar holding periods, timeframes,
individual indicators, current4/all10 combinations, directions and time splits.
trades.json contains every completed event for these scenarios; do not pool
different scenarios as independent trades or sum into a portfolio equity curve.
signals_*.npz contains computed indicators, signals and divergence lengths.
checks.json documents data consistency checks and remaining discrepancies.

Current4 = MACD, RSI, OBV, MFI.
Explore_* candidates were chosen after looking at single-indicator results:
these are post-hoc exploration, not independently held-out discoveries.
Pine source detection logic copyright LonesomeTheBlue; see original Pine header
for MPL 2.0 notice. Python port reproduces that detection logic for research.
No comparison against TradingView's compiler or per-bar export was performed.
'''
(ROOT/'README.txt').write_text(readme,encoding='utf-8')
files=[ROOT/x for x in ['README.txt','fetch_market.py','backtest_divergence.py','verify_backtest.py','data_manifest.json','checks.json','results.json','trades.json','binance_BTCUSDT_4h.json','binance_BTCUSDT_1d.json','binance_BTCUSDT_funding.json','signals_4h.npz','signals_1d.npz']]
files+=[report,OUT/'Divergence_Candles_Labels_v4.pine']
hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
(ROOT/'SHA256.json').write_text(json.dumps(hashes,indent=2))
with zipfile.ZipFile(OUT/'BTCUSDT_Backtest_Reproducible.zip','w',zipfile.ZIP_DEFLATED) as z:
    for p in files+[ROOT/'SHA256.json']:z.write(p,p.name)
print('Report:',report)
print('ZIP:',OUT/'BTCUSDT_Backtest_Reproducible.zip')
print('HTML bytes:',report.stat().st_size)
