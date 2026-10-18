"""Diagnose v4.1 and evaluate v4.2 display only. Formal rules remain frozen."""
import hashlib,json
import numpy as np
import pandas as pd
from research import ROOT,load,atr,rma,save,jsonlines,START,END
from reference_use import readlines
from hist_line_v42 import Candidate,Display,scale
from verify_hist_line_v41 import display as old_display

def replay(df,hist,baseline):
    c=df.close.to_numpy();h=df.high.to_numpy();l=df.low.to_numpy();aa=atr(df)
    pc=df.close.shift(1)
    tr=pd.concat([df.high-df.low,(df.high-pc).abs(),(df.low-pc).abs()],axis=1).max(axis=1)
    al=rma(tr.to_numpy(),100)
    v20=pd.Series(hist).rolling(20).std(ddof=0).to_numpy();v100=pd.Series(hist).rolling(100).std(ddof=0).to_numpy()
    piv=[[],[]];cand=[Candidate(),Candidate()];view=Display();out=[]
    lookup={r['time']:r for r in baseline}
    for t in range(len(c)):
        if t>=10:
            p=t-5
            if c[p]<=min(c[p-5:p]) and c[p]<min(c[p+1:t+1]):piv[0].insert(0,p);piv[0]=piv[0][:20]
            if c[p]>=max(c[p-5:p]) and c[p]>max(c[p+1:t+1]):piv[1].insert(0,p);piv[1]=piv[1][:20]
        time=int(df.time.iloc[t])
        if time not in lookup:continue
        old=lookup[time]
        enabled=not old['active_direction'] and not old['success'] and not old['failure']
        ps=scale(aa[t-1],al[t-1]);hs=scale(v20[t-1],v100[t-1])
        cc=[cand[i].step(c,hist,t,piv[i],1 if i==0 else -1,ps,hs,enabled) for i in range(2)]
        r={**old,'bull':cc[0],'bear':cc[1]}
        trace=view.step(r)
        for x in cc:
            if x['score'] is not None:
                assert x['score']<=min(x['price_pct'],x['hist_pct']) and 0<=x['score']<=99
        assert trace['value'] is None or 0<=trace['value']<=100
        if old['active_direction']:assert trace['value']==old['structure_progress']
        assert not old['invalid_touch'] or trace['warning']
        out.append({**r,'view':trace})
    return out

def metrics(trace,new):
    changes=[];inside=[];switch=[];jumps=0;forming_inside=[];structure_inside=[]
    for a,b in zip(trace,trace[1:]):
        if a['value'] is None or b['value'] is None:continue
        d=abs(b['value']-a['value']);changes.append(d)
        seam=b['seam'] if new else b['reset']
        (switch if seam else inside).append(d)
        if not seam and a['phase']==b['phase']==1:forming_inside.append(d)
        if not seam and a['phase']==b['phase']==2:structure_inside.append(d)
        if not seam and d>=30:jumps+=1
    forming=[x['value'] for x in trace if x['phase']==1 and x['value'] is not None]
    return dict(bars=len(trace),raw_jumps_ge30=sum(x>=30 for x in changes),context_jumps_ge30=sum(x>=30 for x in switch),within_context_jumps_ge30=jumps,
        drawn_jumps_ge30=jumps if new else sum(x>=30 for x in changes),
        within_context_delta_p95=float(np.percentile(inside,95)),context_changes=sum(x['seam' if new else 'reset'] for x in trace),
        formation_bars=len(forming),formation_at_extremes=sum(x<1 or x>98 for x in forming),missing_values=sum(x['value'] is None for x in trace),
        within_formation_jumps_ge30=sum(x>=30 for x in forming_inside),within_structure_jumps_ge30=sum(x>=30 for x in structure_inside),
        within_formation_delta_p95=float(np.percentile(forming_inside,95)))

def main():
    old=(ROOT/'pine/Hist_Divergence_Line_v4_1.pine').read_text(encoding='utf-8')
    new=(ROOT/'pine/Hist_Divergence_Line_v4_2.pine').read_text(encoding='utf-8')
    a='[macdValue, signalValue, hist]'
    assert old[old.index(a):old.index('// Formation scores')]==new[new.index(a):new.index('// Display-only scoring;')]
    assert old[old.index('alertcondition('):]==new[new.index('alertcondition('):]
    assert 'varip ' not in new and 'request.security(' not in new and 'offset=' not in new
    out=ROOT/'results/hist_line_v4_2';out.mkdir(exist_ok=True)
    report=[]
    for tf in ['1d','4h']:
        df=load(tf);saved=readlines(ROOT/f'data/derived/indicators_signals_{tf}.jsonl.gz');hist=np.array([r['Hist_value'] for r in saved])
        base=readlines(ROOT/f'results/hist_progress_v4/timeline_{tf}.jsonl.gz')
        rows=replay(df,hist,base);assert len(rows)==len(base)
        n=len(df)//2;prefix=replay(df.iloc[:n],hist[:n],base)
        assert prefix==rows[:len(prefix)],'Future dependence'
        oldview=old_display(base);newview=[r['view'] for r in rows]
        # Formal records are passed through, and exact Pine source equality protects
        # the live engine; this is not a new independent backtest of event accuracy.
        keys=['time','bull_length','bear_length','start','success','failure','active_direction','confirmation','invalidation']
        assert [{k:r[k] for k in keys} for r in rows]==[{k:r[k] for k in keys} for r in base]
        jsonlines(out/f'timeline_{tf}.jsonl.gz',rows)
        report.append(dict(tf=tf,events=sum(bool(r['start']) for r in rows),v41=metrics(oldview,False),v42=metrics(newview,True),prefix_stable=True,structure_exact=True,all_structure_touch_warnings_immediate=True))
    result=dict(status='PASS',source_sha256=hashlib.sha256((ROOT/'pine/Hist_Divergence_Line_v4_2.pine').read_bytes()).hexdigest(),formal_core_byte_equal_v41=True,alerts_byte_equal_v41=True,datasets=report,
        interpretation='Display diagnostics only. Different scoring semantics: v4.2 50=endpoint equality. Context jumps are intentionally not connected; raw jumps are reported separately. Genuine structural price moves are unfiltered. No claim of improved predictive accuracy or full Pine historical export reconciliation.')
    save(out/'checks.json',result);print((out/'checks.json').read_text(encoding='utf-8'))

if __name__=='__main__':main()
