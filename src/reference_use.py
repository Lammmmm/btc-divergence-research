"""Twelve predeclared, practical alert configurations; no strategy optimization.
All code additions MPL-2.0. Signal inputs retain LonesomeTheBlue attribution.
"""
import gzip,hashlib,json,math
from pathlib import Path
import numpy as np
import pandas as pd
from research import ROOT,load_rows,load,atr,rma,jsonlines,save,NAMES,HOUR,START,END
R=ROOT/'results/reference_use';D=ROOT/'data/derived'
P=json.loads((ROOT/'config/reference_use_protocol.json').read_text(encoding='utf-8'))
def readlines(p):
    with gzip.open(p,'rt',encoding='utf-8') as f:return [json.loads(s) for s in f]

def adx14(df):
    up=df.high.diff().to_numpy();down=-df.low.diff().to_numpy()
    plus=np.where((up>down)&(up>0),up,0.);minus=np.where((down>up)&(down>0),down,0.)
    plus[0]=minus[0]=np.nan
    prev=df.close.shift(1)
    tr=pd.concat([df.high-df.low,(df.high-prev).abs(),(df.low-prev).abs()],axis=1).max(axis=1).to_numpy();tr[0]=np.nan
    smooth=rma(tr,14)
    with np.errstate(invalid='ignore',divide='ignore'):
        pdi=100*rma(plus,14)/smooth;mdi=100*rma(minus,14)/smooth
        den=pdi+mdi
        dx=np.where(np.isnan(den),np.nan,np.where(den>0,100*np.abs(pdi-mdi)/den,0.))
    return rma(dx,14),pdi,mdi

def daily_context(query,confirmed,signal,valid_ms=10*24*HOUR):
    """As-of join; events cannot influence queries before their confirmation."""
    state=np.zeros(len(confirmed),dtype=int);event_time=np.full(len(confirmed),-1,dtype=np.int64)
    direction=0;latest=-1
    for i,(bull,bear) in enumerate(signal):
        if bull or bear:
            direction=0 if bull and bear else (1 if bull else -1);latest=int(confirmed[i])
        state[i]=direction;event_time[i]=latest
    ix=np.searchsorted(confirmed,query,side='right')-1
    directions=np.zeros(len(query),dtype=int);times=np.full(len(query),-1,dtype=np.int64)
    valid=ix>=0
    directions[valid]=state[ix[valid]];times[valid]=event_time[ix[valid]]
    directions[(times<0)|(query-times>valid_ms)]=0
    assert np.all(times<=query)
    return directions,times,ix

def barrier_path(o,h,l,entry,scale,d):
    """Return first signed 1ATR boundary; same-hour ambiguity is adverse-first."""
    good=entry+d*scale;bad=entry-d*scale
    for k in range(len(o)):
        if (o[k]<=bad if d==1 else o[k]>=bad):return 'adverse_first',k+1
        if (o[k]>=good if d==1 else o[k]<=good):return 'favorable_first',k+1
        g=h[k]>=good if d==1 else l[k]<=good
        b=l[k]<=bad if d==1 else h[k]>=bad
        if b:return ('ambiguous_adverse_first' if g else 'adverse_first'),k+1
        if g:return 'favorable_first',k+1
    return 'neither',None

def summarize(rows,span_years=None):
    n=len(rows)
    if not n:return dict(n=0,primary_success=None,direction_accuracy=None,median_mae_atr=None,median_mfe_atr=None)
    successes=sum(x['first_barrier']=='favorable_first' for x in rows);p=successes/n;z=1.96
    center=(p+z*z/(2*n))/(1+z*z/n);half=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/(1+z*z/n)
    return dict(n=n,primary_success=p,primary_wilson_low=center-half,primary_wilson_high=center+half,
      favorable_first=successes,adverse_first=sum(x['first_barrier'] in ['adverse_first','ambiguous_adverse_first'] for x in rows),
      ambiguous=sum(x['first_barrier']=='ambiguous_adverse_first' for x in rows),neither=sum(x['first_barrier']=='neither' for x in rows),
      direction_accuracy=float(np.mean([x['end_direction_positive'] for x in rows])),
      median_mae_atr=float(np.median([x['mae_atr'] for x in rows])),median_mfe_atr=float(np.median([x['mfe_atr'] for x in rows])),
      median_mae_pct=float(np.median([x['mae_pct'] for x in rows])),median_mfe_pct=float(np.median([x['mfe_pct'] for x in rows])),
      median_end_atr=float(np.median([x['end_signed_atr'] for x in rows])),
      alerts_per_year=n/span_years if span_years else None,
      median_first_touch_hours=float(np.median([x['first_touch_hours'] for x in rows if x['first_touch_hours'] is not None])) if any(x['first_touch_hours'] is not None for x in rows) else None)

def observe(ctx,config,start,end):
    tm=ctx['tm'];ct=ctx['ct'];df=ctx['df'];hour=ctx['hour'];counts=ctx['counts'];horizon=ctx['horizon']
    ht=hour.time.to_numpy();hc=hour.close_time.to_numpy();o=hour.open.to_numpy();h=hour.high.to_numpy();l=hour.low.to_numpy();c=hour.close.to_numpy()
    raw=config['signal'];rows=[];ledger=[];available=-1
    for t in np.flatnonzero(raw.any(axis=1)):
        if tm[t]<start or ct[t]>=end:continue
        why='observed'
        d=1 if raw[t,0] else -1
        if t<available:why='overlapping_observation'
        elif raw[t].all():why='two_direction_conflict'
        elif t+horizon>=len(df) or ct[t+horizon]>=end:why='boundary'
        elif any(tm[t+1]<=b<=tm[t+horizon] for b in ctx['bad']):why='price_inconsistency'
        elif config.get('gate') and ctx['daily'+str(config['gate'])][t]!=d:why='daily_context_not_same'
        ledger.append(dict(signal_open_time=int(tm[t]),confirm_time=int(ct[t]),direction=d,status=why))
        if why!='observed':continue
        e=t+1;x=t+horizon;entry=float(df.open.iloc[e]);scale=float(ctx['atr'][t]);assert scale>0
        a=int(np.searchsorted(ht,tm[e]));b=int(np.searchsorted(hc,ct[x]));assert ht[a]==tm[e] and hc[b]==ct[x]
        outcome,hours=barrier_path(o[a:b+1],h[a:b+1],l[a:b+1],entry,scale,d)
        favorable=(h[a:b+1]-entry) if d==1 else (entry-l[a:b+1])
        adverse=(entry-l[a:b+1]) if d==1 else (h[a:b+1]-entry)
        mfe=float(max(0,favorable.max()));mae=float(max(0,adverse.max()))
        adx=ctx['daily_adx'][t];trend=ctx['daily_trend'][t]
        regime='trend' if adx>=25 else ('range' if adx<20 else 'transition')
        context=ctx['daily1'][t]
        row=dict(tf=ctx['tf'],config=config['id'],direction=d,signal_open_time=int(tm[t]),confirm_time=int(ct[t]),
          entry_time=int(tm[e]),window_end=int(ct[x]),entry=entry,atr=scale,horizon_bars=horizon,
          first_barrier=outcome,first_touch_hours=hours,end_close=float(c[b]),end_direction_positive=bool(d*(c[b]-entry)>0),
          end_signed_atr=float(d*(c[b]-entry)/scale),mfe_atr=mfe/scale,mae_atr=mae/scale,mfe_pct=mfe/entry,mae_pct=mae/entry,
          same_side_pool_count=int(counts[t,0 if d==1 else 1]),pool_multiplicity='multiple' if counts[t,0 if d==1 else 1]>=2 else 'one',
          daily_context='same' if context==d else ('opposite' if context==-d else 'none'),daily_context_direction=int(context),
          daily_context_event_time=int(ctx['daily1_time'][t]),daily2_context_direction=int(ctx['daily2'][t]),
          daily_regime_source_close=int(ctx['daily_source_close'][t]),daily_adx14=float(adx),daily_regime=regime,
          trend_relation=('with_trend' if d==trend else 'against_trend') if regime=='trend' else 'not_strong_trend')
        assert row['daily_regime_source_close']<=row['confirm_time']<row['entry_time']
        rows.append(row);available=x
    for a,b in zip(rows,rows[1:]):assert a['window_end']<b['entry_time']
    assert len(rows)==sum(x['status']=='observed' for x in ledger)
    return rows,ledger

def main():
    R.mkdir(parents=True,exist_ok=True);(R/'events').mkdir(exist_ok=True);(R/'ledgers').mkdir(exist_ok=True)
    assert hashlib.sha256((ROOT/'config/reference_use_protocol.json').read_bytes()).hexdigest()==(ROOT/'config/reference_use_protocol.sha256').read_text().split()[0]
    dfs={tf:load(tf) for tf in ['1d','4h']};hour=load_rows('binance_BTCUSDT_1h_trade.json')
    sig={};ats={}
    for tf in dfs:
        records=readlines(D/f'indicators_signals_{tf}.jsonl.gz')
        assert [r['time'] for r in records]==dfs[tf].time.tolist()
        sig[tf]=np.array([[[r[n+'_bull'],r[n+'_bear']] for n in NAMES] for r in records],dtype=bool)
        ats[tf]=atr(dfs[tf])
    daily_pool=[NAMES.index(n) for n in P['daily_pool']]
    dc=sig['1d'][:,daily_pool].sum(axis=1);dct=dfs['1d'].close_time.to_numpy()
    adx,plus,minus=adx14(dfs['1d']);trend=np.where(plus>=minus,1,-1)
    jsonlines(R/'daily_context_inputs.jsonl.gz',(dict(time=int(dfs['1d'].time.iloc[i]),confirm_time=int(dct[i]),adx14=float(adx[i]),plus_di=float(plus[i]),minus_di=float(minus[i]),bull_count=int(dc[i,0]),bear_count=int(dc[i,1])) for i in range(len(dct))))
    periods=[('full',START,END),('earlier',START,1735689600000),('recent',1735689600000,END)]
    checks=json.loads((ROOT/'results/data_and_signal_checks.json').read_text());summaries=[];cohorts=[]
    for tf,df in dfs.items():
        tm=df.time.to_numpy();ct=df.close_time.to_numpy();pool=P['daily_pool'] if tf=='1d' else P['four_hour_pool']
        count=sig[tf][:,[NAMES.index(n) for n in pool]].sum(axis=1)
        d1,t1,ix=daily_context(ct,dct,dc>=1);d2,t2,_=daily_context(ct,dct,dc>=2)
        known=ix>=0
        da=np.full(len(df),np.nan);dt=np.zeros(len(df),dtype=int);ds=np.full(len(df),-1,dtype=np.int64)
        da[known]=adx[ix[known]];dt[known]=trend[ix[known]];ds[known]=dct[ix[known]]
        ctx=dict(tf=tf,df=df,hour=hour,tm=tm,ct=ct,counts=count,horizon=10 if tf=='1d' else 18,
                 atr=ats[tf],bad=checks['datasets'][tf]['bad_execution_bars'],daily1=d1,daily2=d2,daily1_time=t1,
                 daily_adx=da,daily_trend=dt,daily_source_close=ds)
        configs=[dict(id=n,signal=sig[tf][:,NAMES.index(n)]) for n in pool]
        configs += [dict(id='any1',signal=count>=1),dict(id='atleast2',signal=count>=2)]
        if tf=='1d':configs.append(dict(id='Hist_or_MOM',signal=sig[tf][:,[NAMES.index('Hist'),NAMES.index('MOM')]].any(axis=1)))
        if tf=='4h':configs += [dict(id='any1_daily1',signal=count>=1,gate=1),dict(id='atleast2_daily1',signal=count>=2,gate=1),dict(id='any1_daily2',signal=count>=1,gate=2)]
        for period,start,end in periods:
            for config in configs:
                group=f'{tf}_{config["id"]}_{period}'
                rows,ledger=observe(ctx,config,start,end)
                s=dict(tf=tf,config=config['id'],period=period,group=group,**summarize(rows,(end-start)/86400000/365.25))
                s['raw_signal_bars']=len(ledger);s['status_counts']={k:sum(x['status']==k for x in ledger) for k in sorted(set(x['status'] for x in ledger))}
                summaries.append(s);jsonlines(R/'events'/f'{group}.jsonl.gz',rows);jsonlines(R/'ledgers'/f'{group}.jsonl.gz',ledger)
                for dim,vals in [('direction',[1,-1]),('daily_regime',['range','transition','trend']),('trend_relation',['with_trend','against_trend'])]:
                    for val in vals:cohorts.append(dict(group=group,dimension=dim,value=val,**summarize([x for x in rows if x[dim]==val])))
                if config['id']=='any1':
                    for dim,vals in [('pool_multiplicity',['one','multiple']),('daily_context',['same','opposite','none'])]:
                        for val in vals:cohorts.append(dict(group=group,dimension=dim,value=val,**summarize([x for x in rows if x[dim]==val])))
                print(group,'n',len(rows),'success',s['primary_success'],flush=True)
    save(R/'summary.json',summaries);save(R/'cohorts.json',cohorts)
    lookup={(x['tf'],x['config'],x['period']):x for x in summaries}
    comparisons=[('1d','atleast2','any1'),('4h','atleast2','any1'),('4h','any1_daily1','any1'),('4h','atleast2_daily1','atleast2'),('4h','any1_daily2','any1')]
    decisions=[]
    for tf,filtered,baseline in comparisons:
        a=lookup[tf,filtered,'full'];b=lookup[tf,baseline,'full'];ar=lookup[tf,filtered,'recent'];br=lookup[tf,baseline,'recent']
        lift=a['primary_success']-b['primary_success'] if a['n'] and b['n'] else None
        recent_lift=ar['primary_success']-br['primary_success'] if ar['n'] and br['n'] else None
        retention=a['n']/b['n'] if b['n'] else 0
        passes=a['n']>=30 and ar['n']>=15 and lift>=.05 and a['median_mae_atr']<=b['median_mae_atr'] and retention>=.35 and recent_lift>0
        decisions.append(dict(tf=tf,filtered=filtered,baseline=baseline,full_n=a['n'],recent_n=ar['n'],primary_lift=lift,recent_lift=recent_lift,retention=retention,median_mae_change=a['median_mae_atr']-b['median_mae_atr'] if a['n'] else None,supports_filter=passes))
    save(R/'filter_decisions.json',decisions)
    save(R/'checks.json',dict(configurations=13,predeclared_configurations=12,exploratory_added=1,period_runs=len(summaries),all_events_nonoverlap=True,asof_daily_join=True,protocol_hash_verified=True,source='previous audited frozen snapshots',TradingView='PENDING'))

if __name__=='__main__':main()
