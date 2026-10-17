"""Frozen price-structure reversal events, with no duration expiry. MPL-2.0.
Signal derivation: original LonesomeTheBlue Pine logic, see signal_port.py.
"""
import hashlib,json,math
import numpy as np
from research import ROOT,load,atr,jsonlines,save,START,END,NAMES
from reference_use import readlines
OUT=ROOT/'results/structure_reversal'
PROTOCOL=ROOT/'config/structure_reversal_protocol.json'

def freeze_levels(high,low,t,length,d,scale):
    p=t-int(length)
    assert length>5 and p>=0 and p+5<=t and scale>0
    top=float(np.max(high[p:t+1]));bottom=float(np.min(low[p:t+1]))
    return dict(pivot_index=p,structure_high=top,structure_low=bottom,
                confirmation_level=top if d==1 else bottom,
                invalidation_level=bottom-.5*scale if d==1 else top+.5*scale)

def first_resolution(closes,start,stop,d,target,invalid,bad_indices=()):
    bad=set(bad_indices)
    for k in range(start,stop):
        if k in bad:return k,'data_interrupted'
        if d*(closes[k]-target)>0:return k,'success'
        if d*(closes[k]-invalid)<0:return k,'failure'
    return stop-1,'pending'

def stats(rows):
    success=[r for r in rows if r['status']=='success'];failure=[r for r in rows if r['status']=='failure']
    pending=[r for r in rows if r['status']=='pending'];interrupted=[r for r in rows if r['status']=='data_interrupted']
    n=len(rows);s=len(success);f=len(failure);u=len(pending);resolved=s+f;eligible=resolved+u
    rate=s/resolved if resolved else None;lo=hi=None
    if resolved:
        z=1.96;c=(rate+z*z/(2*resolved))/(1+z*z/resolved)
        half=z*math.sqrt(rate*(1-rate)/resolved+z*z/(4*resolved**2))/(1+z*z/resolved);lo=c-half;hi=c+half
    def q(items,field,quantile):return float(np.quantile([r[field] for r in items],quantile)) if items else None
    return dict(events=n,success=s,failure=f,pending=u,data_interrupted=len(interrupted),completed=resolved,
        completed_accuracy=rate,wilson_low=lo,wilson_high=hi,
        pending_fraction=u/eligible if eligible else None,completed_coverage=resolved/eligible if eligible else None,
        success_all_eligible=s/eligible if eligible else None,upper_if_pending_succeed=(s+u)/eligible if eligible else None,
        median_success_wait_days=q(success,'wait_days',.5),p90_success_wait_days=q(success,'wait_days',.9),
        median_success_mae_pct=q(success,'mae_pct',.5),p90_success_mae_pct=q(success,'mae_pct',.9),
        median_success_mae_atr=q(success,'mae_atr',.5),
        median_confirmation_distance_atr=q(rows,'confirmation_distance_atr',.5),
        median_failure_distance_atr=q(rows,'failure_distance_atr',.5),
        success_after_old_horizon=sum(r['after_old_horizon'] for r in success),
        pending_max_age_days=max((r['wait_days'] for r in pending),default=None))

def observe(df,signal,lengths,aa,bad_times,start,end,tf,name,period):
    tm=df.time.to_numpy();ct=df.close_time.to_numpy();h=df.high.to_numpy();l=df.low.to_numpy();c=df.close.to_numpy()
    stop=int(np.searchsorted(ct,end,side='left'));bad_indices=np.flatnonzero(np.isin(tm,bad_times)).tolist()
    blocked=-1;rows=[];ledger=[]
    for t in np.flatnonzero(signal.any(axis=1)):
        if tm[t]<start or ct[t]>=end:continue
        d=1 if signal[t,0] else -1;side=0 if d==1 else 1;length=int(lengths[t,side]);p=t-length
        why='observed'
        if t<blocked:why='active_structure'
        elif signal[t].all():why='conflicting_signal'
        elif not np.isfinite(aa[t]) or aa[t]<=0:why='invalid_atr'
        elif length<=5 or p<0:why='invalid_saved_pivot'
        elif any(p<=b<=t for b in bad_indices):why='tainted_structure_window'
        elif t+1>=stop:why='no_future_bar'
        ledger.append(dict(signal_time=int(tm[t]),confirm_time=int(ct[t]),direction=d,status=why))
        if why=='no_future_bar':
            # Count this still-valid newest signal as pending with zero observed future.
            why='observed';ledger[-1]['status']='observed'
        if why!='observed':continue
        levels=freeze_levels(h,l,t,length,d,float(aa[t]));ref=float(c[t]);scale=float(aa[t])
        k,status=first_resolution(c,t+1,stop,d,levels['confirmation_level'],levels['invalidation_level'],bad_indices)
        last=k-1 if status=='data_interrupted' else k
        # A signal on the final close has a zero-length future window.
        last=max(t,last)
        if last>t:
            fav=(h[t+1:last+1]-ref) if d==1 else (ref-l[t+1:last+1])
            adv=(ref-l[t+1:last+1]) if d==1 else (h[t+1:last+1]-ref)
            mfe=float(max(0,fav.max()));mae=float(max(0,adv.max()))
        else:mfe=mae=0.
        wait_ms=int(ct[last]-ct[t]);known_end=int(ct[k])
        row=dict(tf=tf,indicator=name,period=period,seq=len(rows)+1,direction=d,status=status,
            signal_time=int(tm[t]),confirm_time=int(ct[t]),pivot_time=int(tm[p]),pivot_confirm_time=int(ct[p+5]),
            divergence_length=length,structure_start=int(tm[p]),structure_end=int(ct[t]),
            **{key:value for key,value in levels.items() if key!='pivot_index'},
            reference_price=ref,atr_at_signal=scale,reference_index=int(t),resolution_index=int(k),
            status_time=known_end,path_last_time=int(ct[last]),resolution_close=float(c[k]) if status in ['success','failure'] else None,
            wait_days=wait_ms/86400000,wait_bars=int(last-t),
            confirmation_distance_atr=float(d*(levels['confirmation_level']-ref)/scale),
            failure_distance_atr=float(d*(ref-levels['invalidation_level'])/scale),
            mfe_pct=mfe/ref,mae_pct=mae/ref,mfe_atr=mfe/scale,mae_atr=mae/scale,
            after_old_horizon=bool(last-t>(10 if tf=='1d' else 18)))
        assert row['pivot_confirm_time']<=row['confirm_time']
        rows.append(row)
        blocked=stop if status=='pending' else k
    for a,b in zip(rows,rows[1:]):assert b['confirm_time']>=a['status_time']
    assert len(rows)==sum(r['status']=='observed' for r in ledger)
    return rows,ledger

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    for d in ['events','ledgers']: (OUT/d).mkdir(exist_ok=True)
    assert hashlib.sha256(PROTOCOL.read_bytes()).hexdigest()==PROTOCOL.with_suffix('.sha256').read_text().split()[0]
    original=json.loads((ROOT/'results/data_and_signal_checks.json').read_text())
    summaries=[];breakdown=[]
    for tf in ['1d','4h']:
        df=load(tf);aa=atr(df);records=readlines(ROOT/f'data/derived/indicators_signals_{tf}.jsonl.gz')
        assert [r['time'] for r in records]==df.time.tolist()
        for name in NAMES:
            signal=np.array([[r[name+'_bull'],r[name+'_bear']] for r in records],dtype=bool)
            lengths=np.array([[r[name+'_bull_length'],r[name+'_bear_length']] for r in records])
            for period,start,end in [('full',START,END),('earlier',START,1735689600000),('recent',1735689600000,END)]:
                group=f'{tf}_{name}_{period}'
                rows,ledger=observe(df,signal,lengths,aa,original['datasets'][tf]['bad_execution_bars'],start,end,tf,name,period)
                summary=dict(tf=tf,indicator=name,period=period,group=group,**stats(rows),
                  raw_signal_bars=len(ledger),status_counts={v:sum(r['status']==v for r in ledger) for v in sorted(set(r['status'] for r in ledger))})
                summaries.append(summary);jsonlines(OUT/'events'/f'{group}.jsonl.gz',rows);jsonlines(OUT/'ledgers'/f'{group}.jsonl.gz',ledger)
                for d in [1,-1]:breakdown.append(dict(group=group,direction=d,**stats([r for r in rows if r['direction']==d])))
                print(group,'S/F/U/D',summary['success'],summary['failure'],summary['pending'],summary['data_interrupted'],flush=True)
    save(OUT/'summary.json',summaries);save(OUT/'by_direction.json',breakdown)
    save(OUT/'checks.json',dict(primary_settings=20,period_runs=len(summaries),protocol_hash_verified=True,
        no_duration_expiry=True,frozen_boundaries=True,nonoverlap_verified=True,TradingView='PENDING'))

if __name__=='__main__':main()
