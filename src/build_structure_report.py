import json,html
from research import ROOT
from reference_use import readlines
from build_report import table,mdtable,pct,num
R=ROOT/'results/structure_reversal';P=ROOT/'reports'

def main():
    data=json.loads((R/'summary.json').read_text());sides=json.loads((R/'by_direction.json').read_text())
    full=[x for x in data if x['period']=='full'];recent={(x['tf'],x['indicator']):x for x in data if x['period']=='recent'}
    headers=['指标','成功/失败','待定','数据中断','已完成成功率','近期成功/完成','近期成功率','成功等待中位天数','成功前逆向中位数','成功前逆向P90']
    tables={}
    for tf in ['1d','4h']:
        rows=[]
        for x in sorted([x for x in full if x['tf']==tf],key=lambda x:x['completed_accuracy'],reverse=True):
            z=recent[tf,x['indicator']]
            rows.append([x['indicator'],f"{x['success']}/{x['failure']}",x['pending'],x['data_interrupted'],pct(x['completed_accuracy']),f"{z['success']}/{z['completed']}",pct(z['completed_accuracy']),f"{x['median_success_wait_days']:.1f}",pct(x['median_success_mae_pct']),pct(x['p90_success_mae_pct'])])
        tables[tf]=rows
    method='每次提示确认时，用背离起点到确认K线的最高价、最低价固定结构区间。底背离以后收盘突破上沿算确认成功；收盘跌破下沿减0.5个当时ATR算失效。顶背离反向。边界冻结、影线不单独判错、没有等待根数上限；样本结束仍未触发的事件保留待定。'
    limitation='这是一种事先固定的结构突破定义，不保证形成持续新趋势。历史已经查看，TradingView逐根对账仍待完成。成功率按已完成事件统计，不是收益率或入场胜率；待定和数据中断单独展示。'
    conclusion=[
      '日线观察范围可以适度扩大：Hist在本轮为27/38=71.05%，MOM为18/30=60.00%，RSI为24/41=58.54%。若你愿意等待结构形成，Hist可重新列为日线优先观察项，MOM保留为另一项参考；RSI可作为底背离的补充观察候选。这里没有测试它们同时开启或同时触发的组合优势。',
      '日线Hist的27个成功事件中，17个在10天以后才完成确认；等待中位数15天，P90约56.8天。成功前最大逆向波动的中位数3.21%、P90约9.42%。这些回撤不是账户回撤，也不包括失败事件；不能看到71%就认为等待没有代价。',
      '4H没有出现值得明显扩大勾选范围的结果。CMF为65/156=41.67%，Hist为83/201=41.29%，两者仅差约0.37个百分点，不能据此认定CMF优于Hist。其余单项约32.88%至39.32%。这套结构规则对4H要求较远的确认突破，也影响了比例。',
      '本轮同时取消了时间上限，并把失效改为结构边界加收盘确认；事件去重方式也随事件持续期改变。因此新旧百分比不能当成只改变“等待时间”的对照试验。'
    ]
    side_rows=[]
    for x in sides:
        if x['group'] in ['1d_Hist_full','1d_RSI_full','1d_MOM_full','4h_Hist_full','4h_CMF_full']:
            side_rows.append([x['group'].replace('_full',''),'底背离' if x['direction']==1 else '顶背离',f"{x['success']}/{x['completed']}",x['pending'],pct(x['completed_accuracy']),f"{x['median_success_wait_days']:.1f}",pct(x['median_success_mae_pct'])])
    geometry=[]
    for x in full:
        geometry.append([x['tf'].upper(),x['indicator'],num(x['median_confirmation_distance_atr']),num(x['median_failure_distance_atr']),pct(x['wilson_low'])+'–'+pct(x['wilson_high']),pct(x['success_all_eligible']),pct(x['upper_if_pending_succeed']),x['success_after_old_horizon']])
    cases=[]
    for group in ['1d_Hist_full','1d_RSI_full','4h_Hist_full']:
        rows=readlines(R/'events'/f'{group}.jsonl.gz')
        for status in ['success','failure','pending']:
            candidates=[x for x in rows if x['status']==status and (x['after_old_horizon'] or status=='pending')]
            if not candidates:continue
            x=candidates[0]
            from datetime import datetime,timezone
            date=lambda ms:datetime.fromtimestamp(ms/1000,timezone.utc).strftime('%Y-%m-%d %H:%M')
            cases.append([group.replace('_full',''),date(x['confirm_time']),'底' if x['direction']==1 else '顶',status,f"{x['wait_days']:.1f}",f"{x['reference_price']:.2f}",f"{x['confirmation_level']:.2f}",f"{x['invalidation_level']:.2f}",pct(x['mae_pct'])])
    body=['<h1>允许横盘等待：结构反转参考测试</h1><p>BINANCE BTCUSDT USDT永续｜10个单指标 × 日线/4H｜2021-01-01至2026-10-15 UTC。没有新增组合或参数搜索。</p>',f'<div class="notice">{limitation}</div>',
      '<h2>这次怎样认定反转</h2>',f'<p>{method}</p>',
      '<p>一个指标一次只跟踪一个结构，未结束时的后续多空提示只记录、不另计一次成功机会。失败之后即使最终涨回/跌回，也不能翻改原判定。前段和近期各自从空事件状态重放，指标预热仍只用过去数据。</p>',
      '<h2>可直接参考的结论</h2>',''.join(f'<p>{html.escape(x)}</p>' for x in conclusion),
      '<h2>日线：全部10项</h2>',table(headers,tables['1d']),
      '<h2>4H：全部10项</h2>',table(headers,tables['4h']),
      '<p>近期区间为2025-01-01至2026-10-15。已完成成功率=成功/(成功+失败)。等待及逆向波动列仅统计成功事件；P90表示约90%的成功事件不超过该数值，并不表示最大值。原始失败与待定事件的等待、波动也全部保存。收盘才判定失效，盘中影线的逆向幅度可能更大。</p>',
      '<h2>顶底分别看</h2>',table(['设置','方向','成功/已完成','待定','已完成成功率','成功等待中位天数','成功前逆向中位数'],side_rows),
      '<p>日线Hist底背离为12/15=80%，RSI底背离11/15=73.33%，样本各只有15次；不能把这些比例视为稳定可复现的命中率。是否同时开启多个指标也未在本轮验证。日线Hist顶背离15/23=65.22%，MOM顶背离13/21=61.90%。</p>',
      '<h2>待定、区间宽度与不确定性</h2>',table(['周期','指标','确认距离中位ATR','失效距离中位ATR','已完成Wilson描述区间','已成功/所有可评价事件','若待定全成功的上界','超过旧窗口才成功次数'],geometry),
      '<p>“所有可评价事件”包含待定，排除数据中断；上下界只描述把待定全算失败/成功的边界，不是置信区间。Wilson区间仅作描述，未校正多重筛选或市场相关性，完成与否也可能具有选择性。各指标形成的结构宽度和上下距离不同，不可把50%直接当作随机胜率基准。</p>',
      '<h2>可追溯案例</h2>',table(['设置','确认时间UTC','方向','结果','等待天数','参考价','确认位','失效位','期间最大逆向'],cases),
      '<p>案例取各组按时间排序的首个超过旧窗口的成功、失败及待定事件，仅作核查示例，不作为额外统计样本。等待较久不等于全过程完全横盘，也可能包含缓慢趋势和反复试探。</p>',
      '<h2>设置与文件</h2><p>信号设置保持：Pivot5、Close、Regular、最近10个拐点、最多100根、不勾选Don’t Wait for Confirmation、最低背离数1。日线优先观察Hist，MOM作为另一项单独参考，RSI底背离为待积累样本的候选；4H保留Hist即可，尚无证据支持因本轮结果增加一批项目。</p>',
      '<p>这轮的结构区间是离线评估规则，尚未写进你现用Pine脚本；原图上的背离标签不等于已经突破确认位。最新待定记录也只是截至2026-10-15的数据状态，不能当作今天的实时信号。</p>',
      '<p>全部事件和跳过原因：results/structure_reversal/；方案：config/structure_reversal_protocol.json；独立复核和合成测试已保存。单独重跑：python run_structure.py。旧报告、数据和ZIP快照保留。</p>',
      '<p>方法参考：<a href="https://www.tradingview.com/pine-script-docs/concepts/repainting/">TradingView实时确认与历史回绘说明</a>。本研究严格从信号确认后开始评价，不回到标注拐点成交。</p>']
    css='body{font:16px/1.7 system-ui,"Microsoft YaHei",sans-serif;max-width:1320px;margin:auto;padding:32px;color:#172033;background:#f8fafc}h1{font-size:30px}h2{margin-top:34px}.notice{padding:18px;background:#fff7ed;border-left:5px solid #d97706}.scroll{overflow-x:auto}table{border-collapse:collapse;width:100%;background:white;font-size:14px}th,td{padding:8px 10px;border-bottom:1px solid #e2e8f0;text-align:right;white-space:nowrap}th{background:#142b49;color:white}td:first-child{text-align:left}tr:nth-child(even){background:#f1f5f9}'
    (P/'structure_reversal.html').write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>结构反转参考测试</title><style>'+css+'</style><body>'+''.join(body)+'</body></html>',encoding='utf-8')
    md='# 允许横盘等待的结构反转测试\n\n'+method+'\n\n**'+limitation+'**\n\n'+'\n\n'.join(conclusion)+'\n\n## 日线\n\n'+mdtable(headers,tables['1d'])+'\n\n## 4H\n\n'+mdtable(headers,tables['4h'])+'\n\n## 方向差异\n\n'+mdtable(['设置','方向','成功/已完成','待定','已完成成功率','成功等待中位天数','成功前逆向中位数'],side_rows)+'\n\n[完整报告](structure_reversal.html)。这轮不是交易收益回测；旧样本已查看，TradingView对账仍待完成，不能把更换评价规则后的排名变化当作独立验证。\n'
    (P/'STRUCTURE_REVERSAL.md').write_text(md,encoding='utf-8')
    print('Structure reports saved')

if __name__=='__main__':main()
