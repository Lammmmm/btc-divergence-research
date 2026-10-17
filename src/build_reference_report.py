"""Focused user-facing answer, with all 13 practical settings retained."""
import json,html
from pathlib import Path
from research import ROOT
from build_report import table,mdtable,pct,num
R=ROOT/'results/reference_use';P=ROOT/'reports'
LABEL={'Hist':'Hist 单项','RSI':'RSI 单项','MOM':'MOM 单项','OBV':'OBV 单项','any1':'候选池任意1项','atleast2':'候选池至少2项',
       'any1_daily1':'4H任意1项＋日线至少1项同向','atleast2_daily1':'4H两项＋日线至少1项同向',
       'any1_daily2':'4H任意1项＋日线至少2项同向','Hist_or_MOM':'Hist或MOM（追加探索）'}
def main():
    a=json.loads((R/'summary.json').read_text());co=json.loads((R/'cohorts.json').read_text());decision=json.loads((R/'filter_decisions.json').read_text())
    lookup={(x['tf'],x['config'],x['period']):x for x in a}
    rows=[]
    for x in [v for v in a if v['period']=='full']:
        recent=lookup[x['tf'],x['config'],'recent']
        rows.append([x['tf'].upper(),LABEL[x['config']],x['n'],pct(x['primary_success']),pct(x['direction_accuracy']),num(x['median_mae_atr']),num(x['median_mfe_atr']),recent['n'],pct(recent['primary_success']),f"{x['alerts_per_year']:.1f}"])
    heads=['周期','设置','全期次数','先顺向1ATR','到期方向正确','逆向中位ATR','顺向中位ATR','近期次数','近期先顺向1ATR','去重事件/年']
    settings=[['开启指标','Momentum（MOM）','MACD Histogram（Hist）'],['最低背离数量','1','1'],['Pivot Period','5','5'],['Source','Close','Close'],['Divergence Type','Regular','Regular'],['Maximum Pivot Points','10','10'],['Maximum Bars','100','100'],["Don’t Wait for Confirmation",'不勾选','不勾选'],['信号观察/报警','已收盘/收盘一次','已收盘/收盘一次'],['显示','保留名称和历史标签；关闭连线竖线','保留名称和历史标签；关闭连线竖线']]
    intro='本轮只回答日常如何精简聚合背离设置。12 种预先固定的设置，加 1 种明确标记为探索性的 Hist＋MOM 精简检查；没有搜索拐点、止损或指标周期。'
    method='从信号确认后的下一根开盘开始观察：日线看后续10天，4H看后续3天。主要比例指先顺向走出1个信号时ATR、而不是先逆向1ATR；并非交易胜率。使用1H路径，同小时双触及按逆向先到；未触及两侧也计入总样本。资金费、手续费和仓位不属于本轮信号质量指标。'
    limitation='所有历史已经看过，TradingView逐根对账仍未完成。日线样本小，当前配置只是减少提示噪音的观察方案，不能认定为最优参数，也不能认定具有独立交易优势。'
    findings=[
      '我会把暂用设置收紧为：日线只看 MOM，4H 只看 Hist，最低背离数量均为1。它们是本轮候选中的精简选择，不代表约50%的先后顺序命中已经具备稳定优势。',
      '日线 MOM：35次，先顺向1ATR为54.29%，10天后方向正确为68.57%；近期只有10次。Hist 为43次、53.49%；RSI 为51次、47.06%。Hist＋MOM追加组合为55次、47.27%，没有证明组合比单项更好。',
      '4H Hist：212次，先顺向1ATR为49.06%，3天后方向正确为60.85%。OBV 为215次、46.05%。这表示几天后方向可能正确，但不能据此认为能及时指出拐点。',
      '4H 两项共振：70次、44.29%，低于任意一项321次、49.22%；近期共振21次仅28.57%。不把最低背离数量设为2。',
      '日线同向过滤：至少1项时，4H先顺向比例由49.22%升到50.75%，但只留下67次。日线至少2项时达到57.14%，全期35次、近期12次，提示保留约10.9%。它可能适合稀疏的特别关注列表，但现有证据不足以设为所有4H提示的强制门槛。',
      '趋势/震荡没有形成稳定统一结论。4H候选池在日线ADX≥25时全期55.49%、震荡41.03%，近期分别52.27%与51.52%，差距明显缩小；不据此增加ADX自动过滤。'
    ]
    directions=[]
    for x in co:
        if x['group'] in ['1d_MOM_full','1d_Hist_full','4h_Hist_full'] and x['dimension']=='direction':
            directions.append([x['group'].replace('_full',''),'底背离' if x['value']==1 else '顶背离',x['n'],pct(x['primary_success']),pct(x['direction_accuracy']),num(x['median_mae_atr'])])
    cohortrows=[]
    for x in co:
        if x['group'] in ['1d_any1_full','4h_any1_full','4h_any1_recent'] and x['dimension'] in ['pool_multiplicity','daily_context','daily_regime','trend_relation']:
            if x['group'].startswith('1d') and x['dimension']=='daily_context':continue
            cohortrows.append([x['group'],x['dimension'],x['value'],x['n'],pct(x['primary_success']),num(x['median_mae_atr'])])
    uncertainty=[]
    for tf,name in [('1d','MOM'),('1d','Hist'),('4h','Hist'),('4h','any1_daily2')]:
        x=lookup[tf,name,'full'];uncertainty.append([tf.upper(),LABEL[name],x['n'],pct(x['primary_success']),pct(x['primary_wilson_low'])+'–'+pct(x['primary_wilson_high'])])
    decrows=[[x['tf'].upper(),LABEL[x['filtered']],f"{x['primary_lift']*100:+.2f}个百分点",pct(x['retention']),x['recent_n'],'通过' if x['supports_filter'] else '证据不足/未达到预设标准'] for x in decision]
    body=['<h1>日线与4H：聚合背离怎样设置才实用</h1>',f'<p>{intro}</p>',f'<div class="notice">{limitation}</div>',
      '<h2>暂用配置</h2>',table(['参数','日线','4H'],settings),'<p>如果同时显示多个指标，必须看清提示来自哪一项；不能把背离数量当作置信度。这次进一步检查没有支持此前日线三项、4H两项全部开启的精简建议。</p>',
      '<h2>直接回答三个问题</h2>',''.join(f'<p>{html.escape(s)}</p>' for s in findings),
      '<h2>全部设置的结果</h2>',f'<p>{method}</p>',table(heads,rows),
      '<p>候选池：日线 Hist/RSI/MOM；4H Hist/OBV。全期2021-01-01至2026-10-15，近期2025-01-01至2026-10-15（UTC）。年频率是每个观察窗口只保留首次提示后的事件频率，不是屏幕实际标签数量。不同配置各自去重，因此合并后的比例不是单项比例的加权平均。</p>',
      '<h2>顶、底背离不能混为一谈</h2>',table(['设置','方向','次数','先顺向1ATR','到期方向正确','逆向中位ATR'],directions),
      '<p>日线 MOM 的较好结果主要来自顶背离：22次中63.64%先向下1ATR；底背离仅13次、38.46%。因此它更适合暂作上涨动能转弱的观察提示，不能用总体68.57%的到期准确率支持见底抄底。4H Hist 底背离102次、54.90%，顶背离110次、43.64%，同样存在方向差异；这些仍是已观察历史上的描述，未证明可靠实盘优势。</p>',
      '<h2>过滤条件是否值得设为硬门槛</h2>',table(['周期','过滤设置','全期先顺向改善','保留事件比例','近期次数','预设检查'],decrows),
      '<p>实际筛选要求全期提升至少5个百分点、逆向波动中位数不增加、保留至少35%提示、近期也改善，且全期至少30次、近期至少15次。没有一项通过全部要求。35%的频率门槛是本轮“日常参考”的预设取舍，不表示更稀疏的提醒毫无价值。</p>',
      '<h2>样本不确定性</h2>',table(['周期','设置','次数','先顺向1ATR','Wilson描述区间'],uncertainty),
      '<p>区间未校正跨策略选择、多重比较和市场相关性。不存在“68%到期方向正确，所以有68%的可交易反转成功率”的推论；约50%的先后顺序比例也不能直接解释为优于随机基准。</p>',
      '<details><summary>同一批事件的数量、日线背景与行情分类诊断</summary>',table(['事件池','维度','分组','次数','先顺向1ATR','逆向中位ATR'],cohortrows),'</details>',
      '<p>此处固定任意1项提示的原始去重事件，再按条件分组；与独立重放过滤设置的事件数量不同，不能混用。日线背景取最近已确认的合格背离，最多有效10天；反向同等级事件替换，同日双向冲突清空。新日线未收盘前完全不可见。日线至少2项的背景仍用原三项候选池，不能套用于只启用MOM后的图表。</p>',
      '<h2>保存与复现</h2><p>方案：config/reference_use_protocol.json；唯一追加方案：config/reference_use_amendment.json；全部观察事件、未采用信号、分组与校验：results/reference_use/；代码：src/reference_use.py、src/verify_reference_use.py；单独重跑：python run_reference.py。旧交易研究保留不变。</p>',
      '<p>沿用原始行情、1H执行数据和原价格异常剔除政策；未产生新的真实未来样本。对更高周期仅使用已确认信息，参考 <a href="https://www.tradingview.com/pine-script-docs/concepts/other-timeframes-and-data/">TradingView 多周期数据说明</a>。</p>']
    css='body{font:16px/1.7 system-ui,"Microsoft YaHei",sans-serif;max-width:1200px;margin:auto;padding:32px;background:#f8fafc;color:#172033}h1{font-size:30px}h2{margin-top:35px}.notice{padding:18px;background:#fff7ed;border-left:5px solid #d97706}.scroll{overflow-x:auto}table{border-collapse:collapse;width:100%;background:white;font-size:14px}th,td{padding:9px 12px;border-bottom:1px solid #e2e8f0;text-align:right;white-space:nowrap}th{background:#142b49;color:white}td:first-child{text-align:left}tr:nth-child(even){background:#f1f5f9}summary{cursor:pointer;font-weight:bold}'
    (P/'reference_use.html').write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>日线与4H实用设置检验</title><style>'+css+'</style><body>'+''.join(body)+'</body></html>',encoding='utf-8')
    md='# 日线与4H实用设置检验\n\n'+intro+'\n\n**'+limitation+'**\n\n'+mdtable(['参数','日线','4H'],settings)+'\n\n'+'\n\n'.join(findings)+'\n\n## 全部设置\n\n'+method+'\n\n'+mdtable(heads,rows)+'\n\n## 方向差异\n\n'+mdtable(['设置','方向','次数','先顺向1ATR','到期方向正确','逆向中位ATR'],directions)+'\n\n[完整报告](reference_use.html)。所有结果为历史描述；数据、阈值、原始事件、样本不确定性及未完成验证均在完整报告列出。\n'
    (P/'REFERENCE_USE.md').write_text(md,encoding='utf-8')
    print('Focused reference-use reports saved')

if __name__=='__main__':main()
