"""Causal replay and original-formal-rule regression for v4. No Pine interpreter."""
import hashlib,json
import numpy as np
from research import ROOT,load,atr,START,END,save,jsonlines
from reference_use import readlines
from verify_hist_lifecycle import Lifecycle,find_span
from hist_progress_v4 import Candidate,structure,touched

def replay(c,hist,high,low,aa,times,close_times,n=None):
    n=len(c) if n is None else n;pivots=[[],[]];cand=[Candidate(),Candidate()];life=Lifecycle();rows=[]
    for t in range(n):
        if t>=10:
            p=t-5
            if c[p]<=min(c[p-5:p]) and c[p]<min(c[p+1:t+1]):pivots[0].insert(0,p);pivots[0]=pivots[0][:20]
            if c[p]>=max(c[p-5:p]) and c[p]>max(c[p+1:t+1]):pivots[1].insert(0,p);pivots[1]=pivots[1][:20]
        lengths=[find_span(c,hist,t,pivots[i],i==0,1,True) for i in range(2)] if t else [0,0]
        before=life.active
        touch=bool(before and t>before['t'] and touched(before['direction'],low[t],high[t],before['invalid']))
        allowed=times[t]>=START and np.isfinite(aa[t]) and aa[t]>0
        span=max(lengths);p=t-span
        pulses=life.step(t,c[t],high[t],low[t],[bool(x and allowed) for x in lengths],float(max(high[p:t+1])),float(min(low[p:t+1])),aa[t])
        a=life.active
        enabled=not a and not pulses['success'] and not pulses['failure'] and allowed
        vp=float(np.std(hist[t-20:t],ddof=0)) if t>=20 else float('nan')
        candidates=[cand[i].step(c,hist,t,pivots[i],1 if i==0 else -1,aa[t-1] if t else float('nan'),vp,enabled) for i in range(2)]
        if times[t]<START or close_times[t]>=END:continue
        for i,r in enumerate(candidates):
            if r['ref']!=-1:
                assert r['ref'] in pivots[i][:10] and t-r['ref']>5
                assert r['score']<100 and r['score']<=min(r['price_pct'],r['hist_pct'])
                r['pivot_time']=int(times[r['ref']])
        rows.append(dict(time=int(times[t]),bull_length=lengths[0],bear_length=lengths[1],**pulses,
            active_direction=a['direction'] if a else 0,confirmation=a['target'] if a else None,invalidation=a['invalid'] if a else None,
            structure_progress=structure(c[t],a['invalid'],a['target']) if a else None,
            invalid_touch=touch,structure_red=bool(a and not pulses['start'] and touch),
            formal_pivot_time=int(times[p]) if pulses['start'] else None,
            bull=candidates[0],bear=candidates[1]))
    return rows

def main():
    old=(ROOT/'pine/Hist_Divergence_State_v3_1.pine').read_text(encoding='utf-8')
    new=(ROOT/'pine/Hist_Divergence_Progress_v4.pine').read_text(encoding='utf-8')
    core=lambda s:s[s.index('[macdValue, signalValue, hist]'):s.index('// A distance gauge') if '// A distance gauge' in s else s.index('// Formation scores')]
    expected=core(old).replace('label.new(bar_index, 50, lastResultText','label.new(bar_index, confirms ? 100 : 0, lastResultText').replace('label.new(bar_index, direction == 1 ? 0 : 100, "#"','label.new(bar_index, 100, "#"')
    extra='// Snapshot before close transitions; never test earlier wicks against a newly frozen boundary.\nbool priorInvalidTouch = active and bar_index > startedBar and (direction == 1 ? low <= invalidationPrice : high >= invalidationPrice)\n'
    assert core(new).replace(extra,'')==expected,'Formal core changed'
    assert new[new.index('alertcondition('):]==old[old.index('alertcondition('):]
    assert 'request.security(' not in new and 'varip ' not in new and 'offset=' not in new
    out=ROOT/'results/hist_progress_v4';out.mkdir(exist_ok=True)
    result=[]
    for tf in ['1d','4h']:
        df=load(tf);saved=readlines(ROOT/f'data/derived/indicators_signals_{tf}.jsonl.gz')
        hist=np.array([r['Hist_value'] for r in saved]);c=df.close.to_numpy();h=df.high.to_numpy();l=df.low.to_numpy();aa=atr(df)
        args=(c,hist,h,l,aa,df.time.to_numpy(),df.close_time.to_numpy())
        rows=replay(*args);baseline=readlines(ROOT/f'results/hist_lifecycle/timeline_{tf}.jsonl.gz')
        keys=['time','bull_length','bear_length','start','success','failure','active_direction','confirmation','invalidation']
        assert [{k:r[k] for k in keys} for r in rows]==[{k:r[k] for k in keys} for r in baseline]
        # Replay prefixes at unrelated cut points: later prices must not alter earlier rows.
        cuts=[len(c)//2,len(c)-113]
        for n in cuts:
            prefix=replay(*args,n=n)
            assert prefix==rows[:len(prefix)],'Future dependence'
        jsonlines(out/f'timeline_{tf}.jsonl.gz',rows)
        result.append(dict(tf=tf,bars=len(rows),formal_events=sum(r['start']!=0 for r in rows),formal_rules_and_lifecycle_match_v3=True,prefix_checks=cuts,
            pivot_resets=sum(r[s]['changed'] and r[s]['ref']!=-1 for r in rows for s in ['bull','bear']),
            structure_touch_bars=sum(r['invalid_touch'] for r in rows),formation_broken_bars=sum(r[s]['broken'] for r in rows for s in ['bull','bear'])))
    report=dict(status='PASS',source_sha256=hashlib.sha256((ROOT/'pine/Hist_Divergence_Progress_v4.pine').read_bytes()).hexdigest(),formal_pine_core_unchanged=True,alerts_unchanged=True,datasets=result,scope='Python causal specification and Pine source equivalence; TradingView full-history reconciliation not completed; intrabar formation tick paths cannot be reconstructed from OHLC.')
    save(out/'checks.json',report);print((out/'checks.json').read_text(encoding='utf-8'))

if __name__=='__main__':main()
