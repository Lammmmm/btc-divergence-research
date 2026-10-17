"""Offline streaming specification for the Pine pane; not a Pine interpreter.
Reconciles Hist signal lengths and event transitions with frozen research records.
MPL-2.0; divergence detection derived from LonesomeTheBlue.
"""
import json, math
from dataclasses import dataclass, field
import numpy as np
from research import ROOT, load, atr, START, END, save, jsonlines
from reference_use import readlines
from structure_reversal import observe

def progress(price, side, origin, target, invalid):
    move=side*(price-origin)
    distance=side*(target-origin) if move>=0 else side*(origin-invalid)
    return max(-100.,min(100.,100*move/distance)) if distance>0 else 0.

@dataclass
class Lifecycle:
    active: dict | None = None
    completed: list = field(default_factory=list)
    sequence: int = 0

    def step(self, t, close, high, low, signal, top=None, bottom=None, scale=None, confirmed=True):
        pulses={'start':0,'success':0,'failure':0}
        if not confirmed:return pulses
        if self.active and t>self.active['t']:
            a=self.active;d=a['direction']
            a['mae']=max(a['mae'],a['reference']-low if d==1 else high-a['reference'])
            status='success' if d*(close-a['target'])>0 else 'failure' if d*(close-a['invalid'])<0 else None
            if status:
                pulses[status]=d
                self.completed.append(dict(a,status=status,resolution=t))
                self.active=None
        if any(signal):
            if self.active:self.active['ignored']+=1
            elif not all(signal):
                d=1 if signal[0] else -1
                self.sequence+=1
                self.active=dict(t=t,direction=d,reference=close,top=top,bottom=bottom,
                    target=top if d==1 else bottom,invalid=bottom-.5*scale if d==1 else top+.5*scale,
                    scale=scale,mae=0.,ignored=0,seq=self.sequence)
                pulses['start']=d
        return pulses

def find_span(c,hist,t,pivots,bull,start,require_turn):
    if require_turn and not ((hist[t]>hist[t-1] or c[t]>c[t-1]) if bull else (hist[t]<hist[t-1] or c[t]<c[t-1])):return 0
    for p in pivots[:10]:
        span=t-p
        if span>100:break
        if span<=5:continue
        if not ((hist[t-start]>hist[p] and c[t-start]<c[p]) if bull else (hist[t-start]<hist[p] and c[t-start]>c[p])):continue
        slope_h=(hist[t-start]-hist[p])/(span-start)
        slope_c=(c[t-start]-c[p])/(span-start)
        vh=hist[t-start]-slope_h;vc=c[t-start]-slope_c
        clear=True
        for y in range(start+1,span):
            if ((hist[t-y]<vh or c[t-y]<vc) if bull else (hist[t-y]>vh or c[t-y]>vc)):
                clear=False;break
            vh-=slope_h;vc-=slope_c
        if clear:return span
    return 0

def main():
    out=ROOT/'results/hist_lifecycle';out.mkdir(parents=True,exist_ok=True)
    result=[]
    for tf in ['1d','4h']:
        df=load(tf);saved=readlines(ROOT/f'data/derived/indicators_signals_{tf}.jsonl.gz')
        c=df.close.to_numpy();h=df.high.to_numpy();l=df.low.to_numpy();aa=atr(df)
        hist=np.array([r['Hist_value'] for r in saved],dtype=float)
        spans=np.zeros((len(c),2),dtype=int);previews=np.zeros_like(spans)
        pivots=[[],[]]
        for t in range(10,len(c)):
            p=t-5
            for side in [0,1]:
                bull=side==0
                ok=(c[p]<=min(c[p-5:p]) and c[p]<min(c[p+1:t+1])) if bull else (c[p]>=max(c[p-5:p]) and c[p]>max(c[p+1:t+1]))
                if ok:pivots[side].insert(0,p);pivots[side]=pivots[side][:20]
                spans[t,side]=find_span(c,hist,t,pivots[side],bull,1,True)
                previews[t,side]=find_span(c,hist,t,pivots[side],bull,0,False)
        expected=np.array([[r['Hist_bull_length'],r['Hist_bear_length']] for r in saved])
        assert np.array_equal(spans,expected),f'{tf}: signal span mismatch'
        model=Lifecycle();timeline=[]
        for t in range(len(c)):
            if int(df.time.iloc[t])<START or int(df.close_time.iloc[t])>=END:continue
            span=int(max(spans[t]));p=t-span
            pulses=model.step(t,float(c[t]),float(h[t]),float(l[t]),spans[t]>0,
                              float(max(h[p:t+1])),float(min(l[p:t+1])),float(aa[t]))
            a=model.active
            timeline.append(dict(time=int(df.time.iloc[t]),hist=float(hist[t]),bull_length=int(spans[t,0]),bear_length=int(spans[t,1]),
                potential_bull=int(previews[t,0]),potential_bear=int(previews[t,1]),**pulses,
                active_direction=a['direction'] if a else 0,confirmation=a['target'] if a else None,
                invalidation=a['invalid'] if a else None,
                progress=progress(c[t],a['direction'],a['reference'],a['target'],a['invalid']) if a else None))
        # Product uses the TradingView chart feed, so no Binance-download quarantine is hardcoded.
        reference,_=observe(df,spans>0,spans,aa,[],START,END,tf,'Hist','full')
        completed=[r for r in reference if r['status']!='pending']
        assert len(completed)==len(model.completed)
        for actual,expected in zip(model.completed,completed):
            assert actual['t']==expected['reference_index'] and actual['resolution']==expected['resolution_index']
            assert actual['status']==expected['status'] and actual['direction']==expected['direction']
            assert actual['target']==expected['confirmation_level'] and actual['invalid']==expected['invalidation_level']
            assert abs(actual['mae']/actual['reference']-expected['mae_pct'])<1e-12
        pending=[r for r in reference if r['status']=='pending']
        assert bool(model.active)==bool(pending)
        if pending:assert model.active['t']==pending[0]['reference_index']
        published=readlines(ROOT/f'results/structure_reversal/events/{tf}_Hist_full.jsonl.gz')
        key=lambda r:(r['reference_index'],r['resolution_index'],r['status'],r['confirmation_level'],r['invalidation_level'])
        identical=[key(r) for r in reference]==[key(r) for r in published]
        pub_by_start={r['reference_index']:r for r in published}
        changes=[dict(signal_time=r['signal_time'],product_event={k:r[k] for k in ['reference_index','resolution_index','status','confirmation_level','invalidation_level']},
            published_event={k:pub_by_start[r['reference_index']][k] for k in ['reference_index','resolution_index','status','confirmation_level','invalidation_level']} if r['reference_index'] in pub_by_start else None)
            for r in reference if r['reference_index'] not in pub_by_start or key(r)!=key(pub_by_start[r['reference_index']])]
        save(out/f'quarantine_comparison_{tf}.json',dict(identical=identical,changes=changes,
            published_only_starts=[r['signal_time'] for r in published if r['reference_index'] not in {x['reference_index'] for x in reference}],
            reason='TradingView pane uses its chart feed; it does not hardcode exclusions for the separate Binance download snapshot.'))
        jsonlines(out/f'timeline_{tf}.jsonl.gz',timeline)
        result.append(dict(tf=tf,source_bars=len(c),signal_lengths_match=True,completed=len(completed),pending=len(pending),
            successful=sum(r['status']=='success' for r in completed),failed=sum(r['status']=='failure' for r in completed),
            streaming_matches_batch=True,identical_to_published_Hist_events=identical))
    save(out/'offline_checks.json',dict(status='PASS',datasets=result,
        scope='Python streaming specification vs saved research; not execution of Pine by Python.',
        TradingView_full_export_reconciliation='PENDING',preview_accuracy='NOT_TESTED'))
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
