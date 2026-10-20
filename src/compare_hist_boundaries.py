"""Focused boundary experiment; all signals and confirmation targets are frozen."""
from pathlib import Path
import hashlib, json
import numpy as np
from research import load, atr, START, END, jsonlines, save
from reference_use import readlines

R = Path(__file__).resolve().parents[1]
OUT = R/'results/hist_boundary_comparison'
ARMS = ['original', 'local6', 'local2']
SPLIT = 1735689600000


def levels(h, l, t, span, d, scale, arm):
    p = t-span
    target = float(max(h[p:t+1]) if d == 1 else min(l[p:t+1]))
    q = p if arm == 'original' else t-(5 if arm == 'local6' else 1)
    invalid = float(min(l[q:t+1])-.5*scale if d == 1 else max(h[q:t+1])+.5*scale)
    return target, invalid


def outcome(close, d, target, invalid):
    return 'success' if d*(close-target)>0 else 'failure' if d*(close-invalid)<0 else None


def replay(df, aa, lengths, start, end, arm):
    h,l,c = [df[x].to_numpy() for x in ['high','low','close']]
    tm,ct = df.time.to_numpy(), df.close_time.to_numpy()
    indices = np.flatnonzero((tm>=start)&(ct<end))
    active = None
    events,trace,ledger = [],[],[]
    sequence=0
    for t in indices:
        pulses = dict(start=0,success=0,failure=0)
        if active and t>active['start_index']:
            status=outcome(c[t],active['direction'],active['target'],active['invalid'])
            if status:
                active.update(status=status,end_index=int(t),end_time=int(ct[t]),wait_bars=int(t-active['start_index']))
                events.append(active)
                pulses[status]=active['direction']
                active=None
        bull,bear = map(int,lengths[t])
        if bull or bear:
            reason='accepted'
            if active:reason='active_structure'
            elif bull and bear:reason='conflict'
            elif not np.isfinite(aa[t]) or aa[t]<=0:reason='invalid_atr'
            ledger.append(dict(index=int(t),time=int(tm[t]),bull_length=bull,bear_length=bear,reason=reason))
            if reason=='accepted':
                d=1 if bull else -1;span=bull or bear
                target,invalid=levels(h,l,t,span,d,aa[t],arm)
                assert d*(c[t]-invalid)>0
                sequence+=1
                active=dict(seq=sequence,direction=d,start_index=int(t),start_time=int(tm[t]),
                            pivot_index=int(t-span),reference=float(c[t]),target=target,invalid=invalid,
                            atr=float(aa[t]),status='pending')
                pulses['start']=d
        trace.append(dict(index=int(t),time=int(tm[t]),**pulses,event_id=sequence,
                          active_direction=active['direction'] if active else 0,
                          confirmation=active['target'] if active else None,
                          invalidation=active['invalid'] if active else None))
    if active:
        t=int(indices[-1]);active.update(end_index=t,end_time=int(ct[t]),wait_bars=t-active['start_index'])
        events.append(active)
    return events,trace,ledger


def first(c,t,last,d,target,invalid):
    # Independent vectorized first crossing, used for paired and stream checks.
    future=c[t+1:last+1]
    good=np.flatnonzero(d*(future-target)>0)
    bad=np.flatnonzero(d*(future-invalid)<0)
    g=int(good[0])+t+1 if len(good) else last+1
    b=int(bad[0])+t+1 if len(bad) else last+1
    if g==b==last+1:return last,'pending'
    return (g,'success') if g<=b else (b,'failure')


def summary(events,trace,ledger):
    completed=[e for e in events if e['status']!='pending']
    success=sum(e['status']=='success' for e in events)
    return dict(events=len(events),success=success,failure=sum(e['status']=='failure' for e in events),
                pending=sum(e['status']=='pending' for e in events),
                completed_accuracy=success/len(completed) if completed else None,
                occupied_bars=sum(bool(r['active_direction']) for r in trace),
                total_bars=len(trace),ignored_signal_bars=sum(r['reason']=='active_structure' for r in ledger),
                median_completed_wait_bars=float(np.median([e['wait_bars'] for e in completed])) if completed else None,
                p90_completed_wait_bars=float(np.quantile([e['wait_bars'] for e in completed],.9)) if completed else None,
                max_observed_wait_bars=max(e['wait_bars'] for e in events))


def main():
    OUT.mkdir(exist_ok=True)
    report=[]; paired_summary=[]; evidence=[]; longest=[]
    # Strict boundary, gaps and pending behavior.
    assert outcome(90,1,110,90) is None
    assert outcome(110,-1,90,110) is None
    assert first(np.array([100.,90.,89.]),0,2,1,110,90)==(2,'failure')
    for tf in ['4h','1d']:
        df=load(tf);aa=atr(df)
        saved=readlines(R/f'data/derived/indicators_signals_{tf}.jsonl.gz')
        assert df.time.tolist()==[r['time'] for r in saved]
        lengths=np.array([[r['Hist_bull_length'],r['Hist_bear_length']] for r in saved],dtype=int)
        c,h,l=[df[x].to_numpy() for x in ['close','high','low']]
        for period,start,end in [('full',START,END),('earlier',START,SPLIT),('recent',SPLIT,END)]:
            base,bt,bl=replay(df,aa,lengths,start,end,'original')
            if period=='full':
                for e in sorted(base,key=lambda x:x['wait_bars'],reverse=True)[:3]:
                    t=e['start_index'];span=int(max(lengths[t]))
                    _,local_invalid=levels(h,l,t,span,e['direction'],aa[t],'local2')
                    longest.append(dict(timeframe=tf,**e,local2_invalid=local_invalid,
                                        unchanged_invalid=local_invalid==e['invalid']))
            prior=readlines(R/f'results/hist_v432_backtest/timeline/{tf}_{period}.jsonl.gz')
            assert len(prior)==len(bt)
            for x,y in zip(bt,prior):
                for key in x:assert x[key]==y[key],(tf,period,key,x,y)
            last=bt[-1]['index'];occupied={r['index'] for r in bt if r['active_direction']}
            base_keys={(e['start_index'],e['direction']) for e in base}
            old_groups={(e['direction'],e['pivot_index']) for e in base}
            for arm in ARMS:
                ev,tr,le=(base,bt,bl) if arm=='original' else replay(df,aa,lengths,start,end,arm)
                for e in ev:
                    k,status=first(c,e['start_index'],last,e['direction'],e['target'],e['invalid'])
                    assert (k,status)==(e['end_index'],e['status'])
                stats=summary(ev,tr,le)
                added=[e for e in ev if (e['start_index'],e['direction']) not in base_keys]
                stats.update(timeframe=tf,period=period,arm=arm,
                    added_starts=len(added),added_while_baseline_active=sum(e['start_index'] in occupied for e in added),
                    new_reference_groups=len({(e['direction'],e['pivot_index']) for e in added}-old_groups),
                    occupied_reduction=1-stats['occupied_bars']/sum(bool(r['active_direction']) for r in bt))
                report.append(stats)
                prefix=replay(df,aa,lengths,start,int(df.close_time.iloc[bt[len(bt)//2]['index']])+1,arm)[1]
                assert tr[:len(prefix)]==prefix
                jsonlines(OUT/f'{tf}_{period}_{arm}_events.jsonl.gz',ev)
                jsonlines(OUT/f'{tf}_{period}_{arm}_timeline.jsonl.gz',tr)
                jsonlines(OUT/f'{tf}_{period}_{arm}_ledger.jsonl.gz',le)
                if arm=='original':continue
                pairs=[]
                for e in base:
                    t=e['start_index'];d=e['direction'];span=int(max(lengths[t]))
                    target,invalid=levels(h,l,t,span,d,aa[t],arm)
                    assert target==e['target'] and d*(invalid-e['invalid'])>=-1e-10
                    k,status=first(c,t,last,d,target,invalid)
                    assert k<=e['end_index']
                    pairs.append(dict(start_index=t,start_time=e['start_time'],direction=d,
                        baseline_status=e['status'],baseline_wait=e['wait_bars'],
                        baseline_invalid=e['invalid'],target=target,alternative_invalid=invalid,
                        alternative_status=status,alternative_wait=k-t,bars_saved=e['end_index']-k,
                        sacrificed_success=e['status']=='success' and status=='failure'))
                wins=sum(e['status']=='success' for e in base)
                lost=sum(p['sacrificed_success'] for p in pairs)
                paired_summary.append(dict(timeframe=tf,period=period,arm=arm,baseline_events=len(base),
                    baseline_successes=wins,sacrificed_successes=lost,sacrifice_fraction=lost/wins if wins else None,
                    changed_boundaries=sum(p['baseline_invalid']!=p['alternative_invalid'] for p in pairs),
                    earlier_ends=sum(p['bars_saved']>0 for p in pairs),
                    mean_observed_wait_saved=float(np.mean([p['bars_saved'] for p in pairs])),
                    max_bars_saved=max(p['bars_saved'] for p in pairs)))
                jsonlines(OUT/f'{tf}_{period}_{arm}_paired.jsonl.gz',pairs)
                if period=='full':
                    evidence.extend(dict(timeframe=tf,arm=arm,**p) for p in sorted(pairs,key=lambda x:x['bars_saved'],reverse=True)[:5])
    eligible=[]
    for arm in ARMS[1:]:
        groups=[r for r in report if r['arm']==arm and r['period'] in ['full','recent']]
        pairs=[p for p in paired_summary if p['arm']==arm and p['period'] in ['full','recent']]
        if all(r['occupied_reduction']>=.2 for r in groups) and all(p['sacrifice_fraction'] is not None and p['sacrifice_fraction']<=.05 for p in pairs):eligible.append(arm)
    save(OUT/'summary.json',report);save(OUT/'paired_summary.json',paired_summary);save(OUT/'largest_changes.json',evidence)
    save(OUT/'longest_baseline_cases.json',longest)
    save(OUT/'checks.json',dict(status='PASS',baseline_matches_saved_timelines_all_periods=True,
        stream_matches_independent_first_crossing=True,prefix_stability=True,
        targets_unchanged_and_invalidations_only_tighter=True,eligible_default_arms=eligible,
        protocol_sha256=hashlib.sha256((R/'config/hist_boundary_comparison.json').read_bytes()).hexdigest()))
    print(json.dumps({'full':[r for r in report if r['period']=='full'],
                      'paired_full':[p for p in paired_summary if p['period']=='full'],
                      'eligible':eligible},indent=2))


if __name__=='__main__':main()
