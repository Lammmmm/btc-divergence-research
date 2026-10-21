"""Verify original lifecycle and label-free Hist bar view; not a Pine interpreter."""
from pathlib import Path
import hashlib,json,re
import numpy as np
from research import ROOT,load,atr,START,END,jsonlines,save
from reference_use import readlines
from verify_hist_lifecycle import Lifecycle

def without_labels(text):
    lines=text.splitlines(keepends=True);out=[];i=0
    while i<len(lines):
        line=lines[i]
        if line.strip()=='if showLabels':
            indent=len(line)-len(line.lstrip());i+=1
            while i<len(lines) and lines[i].strip() and len(lines[i])-len(lines[i].lstrip())>indent:i+=1
        else:out.append(line);i+=1
    return ''.join(out)

def synthetic():
    m=Lifecycle()
    assert m.step(0,100,101,99,(1,0),110,90,10)['start']==1
    assert not any(m.step(1,84,101,80,(0,0),confirmed=False).values()) and m.active
    assert not any(m.step(1,85,101,80,(0,0)).values()) and m.active  # equality is not failure
    p=m.step(2,84,101,83,(0,1),120,80,10)
    assert p['failure']==1 and p['start']==-1 and m.active['direction']==-1
    p=m.step(3,80,90,79,(0,0))
    assert not p['success'] and m.active  # equality is not reversal confirmation
    p=m.step(4,79,81,78,(0,0))
    assert p['success']==-1 and not m.active
    m=Lifecycle();assert not any(m.step(0,100,101,99,(1,1),110,90,10).values())
    m.step(0,100,101,99,(1,0),110,90,10)
    assert not m.step(1,102,104,100,(0,1),120,80,10)['start'] and m.active['direction']==1
    return 7

def main():
    p=ROOT/'pine/Hist_Divergence_Bars_v1_3.pine'
    new=p.read_text(encoding='utf-8')
    old=(ROOT/'pine/Hist_Divergence_Line_v4_6_1.pine').read_text(encoding='utf-8')
    core=without_labels(old[old.index('[macdValue, signalValue, hist] ='):old.index('// BEGIN v4.6.1 notice aggregation')])
    assert core in new,'Formal/lifecycle source differs'
    assert not re.search(r'\blabel\.|\bplotshape\(|\bplotchar\(|plot\.style_circles',new),'Visual labels/markers remain'
    assert 'showPanel = input.bool(false' in new
    out=ROOT/'results/hist_bars_v1_3';out.mkdir(parents=True,exist_ok=True)
    summaries=[]
    for tf in ['4h','1d']:
        df=load(tf);aa=atr(df)
        saved=readlines(ROOT/f'data/derived/indicators_signals_{tf}.jsonl.gz')
        expected=readlines(ROOT/f'results/hist_lifecycle/timeline_{tf}.jsonl.gz')
        m=Lifecycle();rows=[]
        for t in range(len(df)):
            if int(df.time.iloc[t])<START or int(df.close_time.iloc[t])>=END:continue
            row=saved[t];span=max(row['Hist_bull_length'],row['Hist_bear_length']);a=t-span
            pulses=m.step(t,float(df.close.iloc[t]),float(df.high.iloc[t]),float(df.low.iloc[t]),
                (row['Hist_bull_length']>0,row['Hist_bear_length']>0),
                float(df.high.iloc[a:t+1].max()),float(df.low.iloc[a:t+1].min()),float(aa[t]))
            active=m.active
            color=('bull' if pulses['start']==1 else 'bear') if pulses['start'] else 'failed' if pulses['failure'] else 'confirmed' if pulses['success'] else ('bull' if active['direction']==1 else 'bear') if active else 'ordinary'
            rows.append(dict(time=int(df.time.iloc[t]),hist=float(row['Hist_value']),start=pulses['start'],success=pulses['success'],failure=pulses['failure'],
                active_direction=active['direction'] if active else 0,confirmation=active['target'] if active else None,invalidation=active['invalid'] if active else None,
                column_state=color,old_result_in_base_quarter=bool(pulses['start'] and (pulses['failure'] or pulses['success']))))
        keys=['time','start','success','failure','active_direction','confirmation','invalidation']
        assert len(rows)==len(expected)
        assert all(all(x[k]==y[k] for k in keys) for x,y in zip(rows,expected)),tf+' lifecycle mismatch'
        jsonlines(out/f'columns_{tf}.jsonl.gz',rows)
        summaries.append(dict(tf=tf,bars=len(rows),exact_saved_lifecycle=True,starts=sum(bool(x['start']) for x in rows),failed=sum(bool(x['failure']) for x in rows),confirmed=sum(bool(x['success']) for x in rows),same_bar_restarts=sum(x['old_result_in_base_quarter'] for x in rows)))
    save(out/'checks.json',dict(status='PASS',source_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),exact_original_core_and_lifecycle=True,no_label_or_shape_or_circle_calls=True,default_panel_hidden=True,synthetic_checks=synthetic(),datasets=summaries,scope='Source equivalence and Python closed-bar replay against the original saved lifecycle. Not a new profitability backtest or Pine interpreter.',full_TradingView_export_reconciliation='NOT_PERFORMED'))
    print(json.dumps(summaries,indent=2))

if __name__=='__main__':main()
