"""Create an offline HTML report and GitHub-readable Markdown from saved results."""
import gzip,html,json
from pathlib import Path
import numpy as np
R=Path(__file__).resolve().parents[1];O=R/'results';P=R/'reports'
def load(n):return json.loads((O/n).read_text(encoding='utf-8'))
def pct(x):return '—' if x is None else f'{x*100:.2f}%'
def num(x):return '—' if x is None else f'{x:.3f}'
def table(headers,rows):
    return '<div class="scroll"><table><thead><tr>'+''.join(f'<th>{html.escape(str(h))}</th>' for h in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join(f'<td>{html.escape(str(v))}</td>' for v in row)+'</tr>' for row in rows)+'</tbody></table></div>'
def mdtable(headers,rows):
    return '\n'.join(['| '+' | '.join(headers)+' |','|'+'|'.join(['---']*len(headers))+'|']+['| '+' | '.join(map(str,r))+' |' for r in rows])
def equitychart(tf,base):
    w,h=1000,320;series=[];colors=['#1d4ed8','#db2777','#047857','#ea580c','#7c3aed','#0891b2','#64748b','#a16207','#be123c','#0f766e']
    for row in base:
        if row['tf']!=tf:continue
        with gzip.open(O/'equity'/f"{row['group']}.jsonl.gz",'rt') as f:a=[json.loads(s) for s in f]
        points=[(row['start'],10000.)]+[(v['time'],v['equity']) for v in a]+[(row['end'],row['ending_equity'])]
        series.append((row['indicator'],np.array(points)))
    low=min(a[:,1].min() for _,a in series)*.995;high=max(a[:,1].max() for _,a in series)*1.005
    start=min(a[0,0] for _,a in series);end=max(a[-1,0] for _,a in series)
    x=lambda t:70+(t-start)/(end-start)*900
    y=lambda v:270-(v-low)/(high-low)*230
    svg=[f'<svg role="img" aria-label="{tf} 账户净值" viewBox="0 0 {w} {h}">']
    for v in np.linspace(low,high,5):
        svg.append(f'<line x1="70" x2="970" y1="{y(v):.2f}" y2="{y(v):.2f}" stroke="#e2e8f0"/><text x="3" y="{y(v)+4:.2f}">{v:,.0f}</text>')
    for i,(name,a) in enumerate(series):
        # Chart only is decimated; full hourly records are retained separately.
        b=a[np.unique(np.r_[np.arange(0,len(a),max(1,len(a)//700)),len(a)-1])]
        pts=' '.join(f'{x(t):.2f},{y(v):.2f}' for t,v in b)
        svg.append(f'<polyline fill="none" stroke="{colors[i]}" stroke-width="1.7" points="{pts}"><title>{name}</title></polyline>')
        svg.append(f'<text x="{70+i*90}" y="20" fill="{colors[i]}">{name}</text>')
    svg.append('<text x="70" y="300">2021-01</text><text x="870" y="300">2026-10-15</text></svg>')
    return ''.join(svg)

def main():
    P.mkdir(exist_ok=True)
    a=load('summary.json');breaks=load('breakdowns.json');ci={x['group']:x for x in load('uncertainty.json')}
    base=[x for x in a if x['period']=='full' and x['scenario']=='risk_base']
    full={(x['tf'],x['indicator'],x['scenario']):x for x in a if x['period']=='full'}
    folds=load('rolling_windows.json');screens=[];mat=[]
    for x in base:
        ev=[z for z in a if z['tf']==x['tf'] and z['indicator']==x['indicator'] and z['period'].startswith('eval_')]
        complete=[z for z in ev if z['fold_complete']]
        positive=sum(z['total_return']>0 for z in complete)
        stress=full[x['tf'],x['indicator'],'cost_2x']
        passed=x['n']>=30 and x['mean_net_R']>0 and stress['mean_net_R']>0 and positive>len(complete)/2 and x['maxdd_hourly_close']<=.15
        item=dict(tf=x['tf'],indicator=x['indicator'],passes_historical_screen=passed,positive_complete_windows=positive,complete_windows=len(complete),cost_2x_return=stress['total_return'],mean_R_block_low=ci[x['group']]['low'],mean_R_block_high=ci[x['group']]['high'],status='历史筛选通过，仍待独立验证' if passed else '未通过本轮历史筛选')
        screens.append(item)
        mat.append([x['tf'].upper(),x['indicator']]+[f"{pct(z['total_return'])} / {z['n']}笔" for z in ev]+[f'{positive}/{len(complete)}'])
    (O/'screening.json').write_text(json.dumps(screens,ensure_ascii=False,indent=2),encoding='utf-8')
    heads=['周期','指标','交易数','净盈利胜率','净收益','最大小时回撤','每笔净 R','盈利因子']
    rows=[[x['tf'].upper(),x['indicator'],x['n'],pct(x['net_win']),pct(x['total_return']),pct(x['maxdd_hourly_close']),num(x['mean_net_R']),num(x['profit_factor'])] for x in sorted(base,key=lambda v:(v['tf'],-v['mean_net_R']))]
    checks=load('accounting_checks.json')
    intro='BINANCE BTCUSDT USDT 永续｜2021-01-01 至 2026-10-15（UTC）｜2020 年仅作指标预热。每组初始 10,000 USDT，独立账户，不叠加持仓。'
    caveat='研究状态：Python 历史模拟。TradingView 逐根对账尚未完成；真正未来的模拟交易验证尚未开始。现有历史已经看过，滚动评估不是未接触过的样本外证据。'
    rules='收盘确认，下一根开盘加不利滑点进场；ATR(14) × 1.5 止损、2R 止盈、最多 10 根本周期 K 线；计划风险为净值 0.5%，名义仓位不超过净值 1 倍（预留入场费）。单边手续费 0.05%、滑点 0.02%，计入历史资金费。基础测试不选择参数。'
    conclusions=[]
    for tf in ['4h','1d']:
        subset=[x for x in base if x['tf']==tf];ret=max(subset,key=lambda x:x['total_return']);win=max(subset,key=lambda x:x['net_win'])
        conclusions.append(f"{tf.upper()}：基础策略净收益最高为 {ret['indicator']}，{pct(ret['total_return'])}，{ret['n']} 笔；净盈利胜率最高为 {win['indicator']}，{pct(win['net_win'])}，{win['n']} 笔。")
    body=['<h1>BTCUSDT 聚合背离：单指标风险策略回测</h1>',f'<p>{intro}</p>',f'<div class="notice">{caveat}</div>',f'<p>{rules}</p>',
          '<p>全部 10 个指标各测 4H / 1D。20 组基础策略；7 组单因素敏感性 × 20；20 组固定持有基准；8 个滚动窗口 × 开发/评估 × 20，共 500 组。各组重新从 10,000 起算，不能把收益相加。</p>',
          '<h2>主要结果</h2>',''.join(f'<p>{x}</p>' for x in conclusions),table(heads,rows),
          '<p>收益为全区间累计净收益，不是年化收益。净盈利胜率 = 扣费后盈利笔数 / 已完成交易数；方向准确率另保存在 summary.json。最大回撤按小时收盘及退出时点的浮动权益计算，不包含小时内最坏波动。较低回撤与较小风险仓位有关。</p>',
          '<h2>账户净值</h2><h3>4H</h3>',equitychart('4h',base),'<h3>1D</h3>',equitychart('1d',base),
          '<p>图表为缩减采样展示，完整资金曲线保存在 results/equity/。空仓资金不计利息。</p>']
    bheads=['周期','指标','固定10根方向准确率','固定10根净胜率','平均 MFE','平均 MAE','平均 MFE 到达小时','平均 MAE 到达小时']
    brows=[]
    for x in [v for v in a if v['period']=='full' and v['scenario']=='fixed10_1x']:
        with gzip.open(O/'trades'/f"{x['group']}.jsonl.gz",'rt') as f:tr=[json.loads(s) for s in f]
        brows.append([x['tf'].upper(),x['indicator'],pct(x['direction_accuracy']),pct(x['net_win']),pct(x['fixed10_mean_mfe']),pct(x['fixed10_mean_mae']),f"{np.mean([r['mfe_hours'] for r in tr]):.1f}",f"{np.mean([r['mae_hours'] for r in tr]):.1f}"])
    body+=['<h2>信号质量：固定持有 10 根基准</h2>',table(bheads,brows),'<p>MFE/MAE 使用完整固定持有窗口的 1H 高低价，相对含滑点入场价，尚未扣除费用；到达时间仅精确到小时。该基准接近 1 倍仓位，与风险策略仓位不同。4H 的 10 根是 40 小时，日线为 240 小时。不要把止损策略的胜率与固定持有方向准确率混为一谈。</p>']
    body+=['<h2>单因素敏感性：全部结果保留</h2>']
    scen=['risk_base','cost_2x','atr_1p25','atr_1p75','target_1p5','target_2p5','hold_8','hold_12']
    body.append(table(['周期','指标']+scen,[[x['tf'].upper(),x['indicator']]+[pct(full[x['tf'],x['indicator'],s]['total_return']) for s in scen] for x in base]))
    body+=['<p>每格为全期净收益。cost_2x 同时加倍手续费与滑点，资金费率保持真实历史值；其余每次只改变一项参数。敏感性不是参数优化，不以其中最佳点替换基础策略。</p>',
          '<h2>滚动评估</h2>',table(['周期','指标']+[f['id']+('（未满半年）' if not f['complete'] else '') for f in folds]+['完整窗口盈利数'],mat),
          '<p>每格为该评估窗口独立账户的净收益 / 交易数；此前 24 个月开发窗口的全部结果也已保存。本轮不根据开发成绩挑选指标，所有指标均保留。跨边界按最大持仓期限剔除交易，最终 2026 下半年不足半年，单独标记。</p>']
    body+=['<h2>样本不确定性与历史筛选</h2>',table(['周期','指标','平均净 R 区间下限','上限','成本加倍收益','历史筛选'],[[x['tf'].upper(),x['indicator'],num(x['mean_R_block_low']),num(x['mean_R_block_high']),pct(x['cost_2x_return']),x['status']] for x in screens]),
          '<p>区间来自固定随机种子、连续 5 笔交易为块、2,000 次循环区块重采样，仅作描述；未校正多重比较，也不能证明真实独立优势。筛选门槛：≥30 笔、基础及加倍成本净期望为正、7 个完整评估窗口中过半盈利、小时回撤≤15%。门槛是预设研究规则，不是普适盈利标准。日线样本少，交易间仍可能相关；区间含零尤其需要谨慎。</p>']
    diag=[]
    for b in breaks:
        if '_risk_base_' in b['group']:
            diag.append([b['group'].replace('_risk_base_full',''),b['dimension'],b['value'],b['n'],pct(b.get('net_win')),num(b.get('mean_net_R')),num(b.get('net_pnl'))])
    body+=['<details><summary>多空、年度与行情状态明细</summary>',table(['组','维度','取值','交易数','净胜率','每笔净R','净盈亏 USDT'],diag),'</details>',
          '<p>这些是同一主账户交易的事后分组，不是单独做多/做空重新回测。年度按入场年份归属。行情状态使用信号确认时本周期 close 与 EMA200 的关系，不用于过滤；同一交易会在不同维度重复出现，不能跨维度求和。</p>']
    concentration=[[x['tf'].upper(),x['indicator'],pct(x['top3_share_of_gross_profits']),f"{x['pnl_excluding_top3']:.2f}",x['max_consecutive_losses'],f"{x['max_underwater_days']:.1f}"] for x in base]
    body+=['<h2>盈利集中度与恢复时间</h2>',table(['周期','指标','最大3笔/总盈利','去除最大3笔后的现金净盈亏','最长连亏','最长水下天数'],concentration),'<p>去除最大3笔只从原现金账本扣除这些盈利，不重新复利或替补交易。水下期使用小时记录，未恢复区间延伸至截止日。</p>']
    body+=['<h2>数据与执行限制</h2><ul>',
      '<li>原始行情全部保存。两根 4H 原生 OHLC 与 1H 汇总不一致，重新查询仍一致地返回差异；统一排除最大持仓窗口经过这些异常原生 K 线的入场。基础 4H 共排除 '+str(sum(x['price_inconsistency_purged'] for x in base if x['tf']=='4h'))+' 个信号窗口。1D 的原生 OHLC 与小时汇总一致。成交量差异逐条保存在校验文件，指标采用原生周期成交量。</li>',
      '<li>6,342 条资金费记录中 3,100 条缺少 API 标记价格，使用该资金费时段 4H 标记价格开盘值估算；每条记录有来源标记。资金费时间戳最多偏离整点 47 毫秒。</li>',
      '<li>1H 内同时触及止损止盈时按止损先到；跳空止损按开盘价，跳空止盈仍按目标价；所有退出再计不利滑点。小时内触发的退出保存时间区间，区间内资金费按先结算处理，无法恢复毫秒级成交顺序。新入场恰好同一时间戳的资金费不计，之后的资金费计入。</li>',
      '<li>按连续数量计算，未模拟交易所历史最小下单量、数量步长、订单簿容量、排队、精确强平或真实账户费率。计划风险不含手续费及跳空超额损失。没有使用未来的日线数据过滤 4H。</li>',
      '<li>未完成 TradingView 编译与逐根信号、逐笔成交核对。导出用 Pine 和比较程序已提供。当前历史结果已被查看，后续开发会受到选择偏差影响。</li></ul>',
      '<h2>验证和文件</h2>',f'<p>已独立复算 {checks["groups"]} 组、{checks["trade_rows_all_groups"]:,} 条交易的费用、现金、单仓限制、时间边界和回撤；基础策略共 {checks["primary_trade_rows"]:,} 笔。每周期 160 个标量信号比对、两次截断未来数据检查通过。合成用例验证资金费方向、跳空、止损先后、最大持仓边界和异常数据排除。</p>',
      '<p>README.md 提供重跑命令；config/ 为冻结方案；data/raw/ 为原始数据；data/derived/ 为逐根指标与信号；results/ 为所有逐笔记录及结果；tests/ 为合成测试；archive/ 为此前实验文件。不同场景和滚动窗口的重复记录不是新增独立样本。</p>',
      '<p>方法参考：<a href="https://www.tradingview.com/pine-script-docs/concepts/strategies/">TradingView 策略与成交模拟</a>；<a href="https://www.tradingview.com/pine-script-docs/concepts/repainting/">TradingView 重绘说明</a>；<a href="https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Get-Funding-Rate-History">Binance 资金费历史接口</a>。具体执行假设以本项目协议及说明为准。</p>']
    css='body{font:16px/1.65 system-ui,"Microsoft YaHei",sans-serif;color:#172033;max-width:1200px;margin:auto;padding:35px;background:#f8fafc}h1{font-size:30px}h2{margin-top:38px}table{border-collapse:collapse;width:100%;background:white;font-size:14px}th,td{padding:9px 12px;border-bottom:1px solid #e2e8f0;text-align:right;white-space:nowrap}th{background:#142b49;color:white}td:first-child,th:first-child{text-align:left}tr:nth-child(even){background:#f1f5f9}.scroll{overflow-x:auto}.notice{border-left:5px solid #d97706;background:#fff7ed;padding:18px}svg{width:100%;background:white;border:1px solid #e2e8f0}svg text{font:13px sans-serif}summary{cursor:pointer;font-weight:bold}a{color:#1d4ed8}li{margin:9px 0}'
    (P/'report.html').write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>BTCUSDT 背离研究报告</title><style>'+css+'</style><body>'+''.join(body)+'</body></html>',encoding='utf-8')
    md='# BTCUSDT 单指标背离风险策略回测\n\n'+intro+'\n\n**'+caveat+'**\n\n'+rules+'\n\n'+'\n\n'.join(conclusions)+'\n\n'+mdtable(heads,rows)+'\n\n'
    md+='完整报告：[report.html](report.html)（下载后浏览器打开）。历史筛选：[screening.json](../results/screening.json)。\n\n'
    md+='共 500 组、33,449 条交易账本记录，其中 20 组基础策略 2,735 笔。重叠时间段与敏感性测试不能合并为独立样本。\n\n'
    md+='数据异常处理、资金费代理、逐笔退出时间区间、置信区间局限与尚未完成的验证，详见 [方法说明](../docs/METHODOLOGY.md)。本报告收益均为全期累计，未年化。\n'
    (P/'SUMMARY.md').write_text(md,encoding='utf-8')
    print('Reports generated. Historical screens:',[(s['tf'],s['indicator']) for s in screens if s['passes_historical_screen']])

if __name__=='__main__':main()
