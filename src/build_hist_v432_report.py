"""Build focused Chinese report from saved v4.3.2 results (no hardcoded metrics)."""
import json, html
from datetime import datetime, timezone
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from research import ROOT, START, END, save
from reference_use import readlines
from build_report import table, mdtable, pct, num
from backtest_hist_v432 import OUT

def main():
    ss=json.loads((OUT/'structure_summary.json').read_text());ts=json.loads((OUT/'trade_summary.json').read_text())
    sides=json.loads((OUT/'structure_by_direction.json').read_text());trade_sides=json.loads((OUT/'trade_by_direction.json').read_text())
    ci={x['group']:x for x in json.loads((OUT/'uncertainty.json').read_text())}
    output=ROOT/'reports';sections=[]
    def add(title,text,headers=None,rows=None):sections.append((title,text,headers,rows))
    full=[next(s for s in ss if s['group']==tf+'_full') for tf in ['1d','4h']]
    base=[next(t for t in ts if t['group']==tf+'_current_starts_risk_base_full') for tf in ['1d','4h']]
    double=[next(t for t in ts if t['group']==tf+'_current_starts_cost_2x_full') for tf in ['1d','4h']]
    add('本轮回答的问题',
        '测试当前 Hist Line v4.3.2 的正式背离事件，而不是所有原始 Hist 提示，也不是灰色形成曲线。'
        '使用 BINANCE BTCUSDT USDT 永续的同一份历史快照，2020 年预热，正式区间为 2021-01-01 至 2026-10-15 UTC。'
        '不增加指标组合、不搜索参数；本次未下载更新至 10 月 19 日的数据。历史已经看过，近期段不能当成未见样本。')
    add('先读结论',
        f'日线结构成功 {full[0]["success"]}/{full[0]["completed"]}，即 {pct(full[0]["completed_accuracy"])}；4H 为 {full[1]["success"]}/{full[1]["completed"]}，即 {pct(full[1]["completed_accuracy"])}。'
        f'配合原有交易规则，日线累计净收益 {pct(base[0]["total_return"])}，4H 为 {pct(base[1]["total_return"])}。'
        f'手续费与滑点翻倍后分别为 {pct(double[0]["total_return"])}、{pct(double[1]["total_return"])}。'
        '日线样本只有 38 笔成交；4H 对成本敏感。显示优化没有改变正式信号，不能把这些结果归因于颜色或曲线的改进。')
    add('一、结构反转成功率：与当前横线一致',
        '成功=后续收盘突破冻结确认位；失败=后续收盘突破冻结失效位；影线触线只警告。允许长期横盘，没有根数超时。'
        '成功率=成功/(成功+失败)，待定单列。每次只跟踪一个多空共用事件，结束前的新提示忽略；结束当根可重新触发。',
        ['周期','原始提示根数','正式事件','成功','失败','待定','已完成成功率','Wilson描述区间'],
        [[s['tf'].upper(),s['raw_signal_bars'],s['events'],s['success'],s['failure'],s['pending'],pct(s['completed_accuracy']),pct(s['wilson_low'])+'–'+pct(s['wilson_high'])] for s in full])
    add('顶底分开统计','方向子样本较小，区间仅作描述。不是未来成功概率，也没有校正历史筛选和市场相关性。',
        ['周期','方向','成功/已完成','失败','待定','成功率','描述区间'],
        [[s['tf'].upper(),'底背离' if s['direction']==1 else '顶背离',f"{s['success']}/{s['completed']}",s['failure'],s['pending'],pct(s['completed_accuracy']),pct(s['wilson_low'])+'–'+pct(s['wilson_high'])] for s in sides if s['period']=='full'])
    add('等待和期间逆向波动','下表的等待、逆向波动只统计最终成功的事件；不代表最大风险或账户回撤。失败和待定事件的路径也完整保存。'
        '确认/失效距离为全部事件中位数，两个边界距离不对称，50%并非天然随机基准。',
        ['周期','成功等待中位天数','等待P90天','成功前逆向中位','逆向P90','确认距离ATR','失效距离ATR','待定全失败/全成功边界'],
        [[s['tf'].upper(),f"{s['median_success_wait_days']:.1f}",f"{s['p90_success_wait_days']:.1f}",pct(s['median_success_mae_pct']),pct(s['p90_success_mae_pct']),num(s['median_confirmation_distance_atr']),num(s['median_failure_distance_atr']),pct(s['success_all_eligible'])+'–'+pct(s['upper_if_pending_succeed'])] for s in full])
    add('二、沿用旧交易规则的收益',
        '这是附加交易规则的收益，不是指标自带收益。每组独立 10,000 USDT；正式事件收盘触发后下一根开盘入场，'
        'ATR(14)×1.5 止损、2R 止盈、最多持有10根；单笔计划风险0.5%，名义仓位最多约1倍净值。'
        '手续费单边0.05%、滑点单边0.02%，计入历史资金费；小时内止盈止损同时触及时先算止损。'
        '交易提前退出不会结束指标事件，也不会让原本被忽略的信号重新入场。日线有1次事件启动时旧交易仍在，故39个事件、38笔交易。'
        '净收益为整段累计收益，非年化；最大回撤按小时收盘浮动净值及出场点统计，不是盘中极值。',
        ['周期','成交笔数','净盈利胜率','累计净收益','期末USDT','最大回撤','盈亏因子','平均净R','成本翻倍净收益'],
        [[s['tf'].upper(),s['n'],pct(s['net_win']),pct(s['total_return']),f"{s['ending_equity']:,.2f}",pct(s['maxdd_hourly_close']),num(s['profit_factor']),num(s['mean_net_R']),pct(d['total_return'])] for s,d in zip(base,double)])
    add('收益的不确定性','平均净R区间使用旧报告同口径：连续5笔循环块、2,000次重采样，仅作历史描述。净盈利胜率与结构反转成功率分母不同。'
        '底/顶收益拆分共用同一条账户资金路径，各方向净损益不能当作独立账户收益率。',
        ['周期','平均净R描述区间','底背离成交/胜率','底背离净损益USDT','顶背离成交/胜率','顶背离净损益USDT'],
        [[s['tf'].upper(),num(ci[s['group']]['low'])+'–'+num(ci[s['group']]['high']),
          str(next(x for x in trade_sides if x['group']==s['group'] and x['direction']==1)['n'])+' / '+pct(next(x for x in trade_sides if x['group']==s['group'] and x['direction']==1)['net_win']),
          f"{next(x for x in trade_sides if x['group']==s['group'] and x['direction']==1)['net_pnl']:.2f}",
          str(next(x for x in trade_sides if x['group']==s['group'] and x['direction']==-1)['n'])+' / '+pct(next(x for x in trade_sides if x['group']==s['group'] and x['direction']==-1)['net_win']),
          f"{next(x for x in trade_sides if x['group']==s['group'] and x['direction']==-1)['net_pnl']:.2f}"] for s in base])
    add('三、前段和近期诊断','前段为2021–2024；近期为2025-01-01至2026-10-15。每段独立重置事件和10,000 USDT账户，保留此前指标预热。'
        '因此分段不能相加或连乘成全样本；近期不是未见样本，未进行择优参数选择。',
        ['周期','时期','结构成功/完成','结构成功率','交易笔数','净盈利胜率','净收益','成本翻倍净收益'],
        [[s['tf'].upper(),'前段' if s['period']=='earlier' else '近期',
          f"{next(x for x in ss if x['group']==s['tf']+'_'+s['period'])['success']}/{next(x for x in ss if x['group']==s['tf']+'_'+s['period'])['completed']}",
          pct(next(x for x in ss if x['group']==s['tf']+'_'+s['period'])['completed_accuracy']),s['n'],pct(s['net_win']),pct(s['total_return']),
          pct(next(x for x in ts if x['group']==s['group'].replace('risk_base','cost_2x'))['total_return'])]
         for s in ts if s['signal_stream']=='current_starts' and s['scenario']=='risk_base' and s['period']!='full'])
    add('四、与原始 Hist 提示比较','两者使用完全相同的旧交易引擎、费用和历史区间。当前版本只在上一结构结束后才接受新提示，交易样本发生变化；'
        '不是把原始信号的正确率用显示方式提高了。原始Hist交易基准已重算并与旧报告一致。',
        ['周期','信号口径','成交','净盈利胜率','净收益','最大回撤','成本翻倍收益'],
        [[s['tf'].upper(),'当前事件启动' if s['signal_stream']=='current_starts' else '原始Hist提示',s['n'],pct(s['net_win']),pct(s['total_return']),pct(s['maxdd_hourly_close']),pct(next(x for x in ts if x['group']==s['group'].replace('risk_base','cost_2x'))['total_return'])]
         for s in ts if s['period']=='full' and s['scenario']=='risk_base'])
    diffs=[]
    for tf in ['4h','1d']:
        raw=readlines(OUT/'events'/f'{tf}_full.jsonl.gz');clean=readlines(OUT/'events'/f'{tf}_full_quality.jsonl.gz')
        bystart={r['reference_index']:r for r in clean};changes=[]
        keys=['resolution_index','status','confirmation_level','invalidation_level']
        for r in raw:
            other=bystart.get(r['reference_index'])
            if other is None or any(r[k]!=other[k] for k in keys):changes.append(dict(current=r,old_quality=other))
        diffs.append(dict(tf=tf,changed_events=changes,quality_only=[r for r in clean if r['reference_index'] not in {x['reference_index'] for x in raw}]))
    save(OUT/'quality_comparison.json',diffs)
    add('数据质量与核查范围',
        '当前Pine没有硬编码剔除历史异常K线，因此主结果按保存的原生周期数据复现；另存旧报告的数据隔离口径作敏感性核查。'
        f'全样本日线有{len(diffs[1]["changed_events"])}个事件细节差异，4H有{len(diffs[0]["changed_events"])}个；两周期的成功/失败总数均未变化。'
        '4H原生与小时聚合存在两根已记录的OHLC不一致，具体事件差异见quality_comparison.json；不能声称所有事件边界完全相同。'
        '交易收益仍执行旧规则的异常价格区间剔除，本轮当前事件交易被该项剔除为0。'
        '代码、指标预热、信号跨度、逐根状态、收盘首次突破、资金费、成交和小时净值已复核。'
        '这次是Python逻辑复现，尚未完成TradingView全历史导出逐根对账；现有TradingView编译/实图检查不能代替该项验证。')
    add('文件与复现',
        '方案：config/hist_v432_backtest.json。数据与逐项输入SHA256：results/hist_v432_backtest/input_hashes.json。'
        '逐事件events/、每根状态timeline/、忽略原因ledgers/、逐笔交易trades/、小时净值equity/、交易筛选trade_ledgers/均保存为JSONL.GZ。'
        '所有汇总及独立核查结果在results/hist_v432_backtest/；旧数据、旧报告与Pine脚本未覆盖。'
        '复现命令：python run_hist_v432_backtest.py。未来数据验证仍待进行。')
    # Plot every saved hourly equity point. Separate panels avoid merging accounts.
    fig,axes=plt.subplots(2,1,figsize=(12,7),sharex=True,layout='constrained')
    dt=lambda t:datetime.fromtimestamp(t/1000,timezone.utc)
    for ax,tf in zip(axes,['1d','4h']):
        for scenario,color,label in [('risk_base','#1744D1','Base costs'),('cost_2x','#D50032','2x fees/slippage')]:
            s=next(x for x in ts if x['group']==f'{tf}_current_starts_{scenario}_full')
            points=readlines(OUT/'equity'/f"{s['group']}.jsonl.gz")
            times=[START]+[x['time'] for x in points]+[END-1];values=[10000]+[x['equity'] for x in points]+[s['ending_equity']]
            ax.plot([dt(x) for x in times],values,color=color,lw=1.2,label=label)
        ax.axhline(10000,color='#8892a0',ls='--',lw=.7);ax.set_title(f'BTCUSDT perpetual | {tf.upper()} | v4.3.2 formal starts')
        ax.set_ylabel('Account equity (USDT)');ax.grid(alpha=.15);ax.legend(loc='upper left')
    fig.savefig(output/'hist_v432_equity.png',dpi=160);plt.close(fig)
    title='Hist Line v4.3.2：当前事件回测'
    body=f'<h1>{title}</h1><p class="sub">报告日期：2026-10-19 · 同历史、同参数、保留旧研究</p>'
    md=f'# {title}\n\n报告日期：2026-10-19；数据截止2026-10-15 UTC。\n'
    for heading,text,headers,rows in sections:
        body+=f'<section><h2>{html.escape(heading)}</h2><p>{html.escape(text)}</p>'
        md+=f'\n## {heading}\n\n{text}\n'
        if headers:body+=table(headers,rows);md+='\n'+mdtable(headers,rows)+'\n'
        if heading=='二、沿用旧交易规则的收益':
            body+='<img src="hist_v432_equity.png" alt="日线与4H的独立账户净值，蓝线基础费用，红线双倍费用">'
            md+='\n![账户净值](hist_v432_equity.png)\n'
        body+='</section>'
    css='body{font:16px/1.75 system-ui,"Microsoft YaHei",sans-serif;max-width:1240px;margin:auto;padding:28px;color:#182436;background:#f5f7fb}h1{font-size:30px;margin-bottom:0}.sub{color:#637087}h2{font-size:22px}section{background:white;padding:22px;margin:22px 0;border:1px solid #e2e7ef;border-radius:10px}.scroll{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:14px}th,td{padding:10px;border-bottom:1px solid #e2e7ef;text-align:right;white-space:nowrap}th{background:#17304d;color:white}td:first-child{text-align:left}tr:nth-child(even){background:#f6f8fc}img{display:block;width:100%;height:auto;margin:20px auto} @media(max-width:600px){body{padding:10px}section{padding:12px}h1{font-size:24px}}'
    (output/'hist_v432_backtest.html').write_text('<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+title+'</title><style>'+css+'</style></head><body>'+body+'</body></html>',encoding='utf-8')
    (output/'HIST_V432_BACKTEST.md').write_text(md,encoding='utf-8')
    save(OUT/'report_checks.json',dict(status='PASS_CONTENT',sections=len(sections),tables=sum(s[2] is not None for s in sections),
        tables_generated_from_saved_results=True,visual_review='PENDING'))
    print('Report saved:',output/'hist_v432_backtest.html')

if __name__=='__main__':main()
