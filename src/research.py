"""Frozen single-indicator research protocol. No orders or credentials.

Derived signal logic is MPL-2.0, copyright LonesomeTheBlue; see signal_port.py.
All timestamps are UTC epoch milliseconds. JSONL exports retain all experiments.
"""
import gzip, hashlib, json, math, platform, sys
from pathlib import Path
import numpy as np
import pandas as pd
from signal_port import load, indicators, signals, rma, validate_data, scalar_signal, NAMES

ROOT=Path(__file__).resolve().parents[1]
RAW=ROOT/'data/raw'; OUT=ROOT/'results'; DER=ROOT/'data/derived'
CFG=json.loads((ROOT/'config/protocol.json').read_text(encoding='utf-8'))
HOUR=3600000
def stamp(s):return int(pd.Timestamp(s,tz='UTC').value//10**6)
START=stamp(CFG['test_start']); END=stamp(CFG['end_exclusive'])
def clean(x):
    if isinstance(x,dict):return {k:clean(v) for k,v in x.items()}
    if isinstance(x,(list,tuple)):return [clean(v) for v in x]
    if isinstance(x,np.ndarray):return clean(x.tolist())
    if isinstance(x,(np.integer,)):return int(x)
    if isinstance(x,(float,np.floating)):return float(x) if np.isfinite(x) else None
    if isinstance(x,np.bool_):return bool(x)
    return x
def save(path,obj):path.write_text(json.dumps(clean(obj),ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
def jsonlines(path,rows):
    # Stable gzip header allows byte-for-byte repeatability.
    with path.open('wb') as raw:
        with gzip.GzipFile(filename='',mode='wb',fileobj=raw,mtime=0) as out:
            for r in rows:out.write((json.dumps(clean(r),ensure_ascii=False,separators=(',',':'),allow_nan=False)+'\n').encode())
def load_rows(name):
    rows=json.loads((RAW/name).read_text())
    df=pd.DataFrame(rows,columns=['time','open','high','low','close','volume','close_time','quote_volume','trades','buy_base','buy_quote','ignore'])
    return df.astype(float).assign(time=lambda x:x.time.astype('int64'),close_time=lambda x:x.close_time.astype('int64'))
def atr(df):
    pc=df.close.shift(1)
    tr=pd.concat([df.high-df.low,(df.high-pc).abs(),(df.low-pc).abs()],axis=1).max(axis=1)
    return rma(tr.to_numpy(),14)

def funding(hour):
    rows=json.loads((RAW/'binance_BTCUSDT_funding.json').read_text())
    mark=load_rows('binance_BTCUSDT_4h_mark.json')
    times=np.array([r['fundingTime'] for r in rows],dtype=np.int64)
    assert np.all(np.diff(times)>0)
    resolved=[];values=[]
    for row in rows:
        t=int(row['fundingTime']);price=float(row.get('markPrice') or 0)
        kind='funding_api_mark'
        if price<=0:
            ix=np.searchsorted(mark.time,t,side='right')-1
            assert ix>=0 and t-int(mark.time.iloc[ix])<4000, 'Proxy must be at funding boundary'
            price=float(mark.open.iloc[ix]);kind='mark_kline_open_proxy'
        resolved.append(dict(time=t,rate=float(row['fundingRate']),mark_price=price,mark_source=kind))
        values.append(float(row['fundingRate'])*price)
    jsonlines(DER/'funding_resolved.jsonl.gz',resolved)
    return times,np.r_[0.,np.cumsum(values)],resolved

def exit_decision(o,h,l,stop,target,d):
    """Gap stops fill at open; gap targets at target (conservative)."""
    if (o<=stop if d==1 else o>=stop):return float(o),'stop_gap',False,True
    if (o>=target if d==1 else o<=target):return float(target),'target_gap',False,True
    sh=(l<=stop if d==1 else h>=stop)
    th=(h>=target if d==1 else l<=target)
    if sh:return float(stop),'stop',bool(th),False
    if th:return float(target),'target',False,False
    return None,None,False,False

def run(ctx,j,scenario,start,end,group):
    """One live position across both directions; current equity drives sizing."""
    df=ctx['df'];ss=ctx['sig'][:,j];hour=ctx['hour'];ft=ctx['ft'];fc=ctx['fc']
    tm=ctx['time'];ct=ctx['ct'];op=ctx['open'];aa=ctx['atr'];ema=ctx['ema']
    ho,hh,hl,hc,ht,hct=(ctx[k] for k in ['ho','hh','hl','hc','ht','hct'])
    fee=CFG['fee_per_side']*scenario.get('cost_multiplier',1)
    slip=CFG['slippage_per_side']*scenario.get('cost_multiplier',1)
    mult=scenario.get('atr_multiple',CFG['atr_multiple'])
    targetr=scenario.get('target_R',CFG['target_R'])
    hold=scenario.get('max_hold_bars',CFG['max_hold_bars'])
    fixed=scenario.get('fixed_hold',False)
    eq=10000.;peak=eq;dd=0.;available=-1;trades=[];curve=[];ledger=[]
    for t in np.flatnonzero(ss.any(axis=1)):
        if tm[t]<start or ct[t]>=end:continue
        status='entered'
        if t<available:status='ignored_position_open'
        elif ss[t].all():status='both_directions_skip'
        elif t+hold>=len(df) or ct[t+hold]>=end:status='purged_boundary'
        elif any(tm[t+1]<=b<=tm[t+hold] for b in ctx.get('bad_execution_bars',[])):status='purged_price_inconsistency'
        elif not np.isfinite(aa[t]) or aa[t]<=0:status='invalid_atr'
        ledger.append(dict(signal_open_time=int(tm[t]),signal_confirm_time=int(ct[t]),bull=bool(ss[t,0]),bear=bool(ss[t,1]),status=status))
        if status!='entered':continue
        e=t+1;last=t+hold;d=1 if ss[t,0] else -1
        entry=float(op[e]*(1+d*slip));dist=float(aa[t]*mult)
        stop=entry-d*dist;target=entry+d*targetr*dist
        before=eq
        curve.append(dict(time=int(tm[e])-1,equity=float(before),trade_seq=len(trades)+1))
        qty=before/(entry*(1+fee)) if fixed else min(before*CFG['risk_fraction']/dist,before/(entry*(1+fee)))
        notional=qty*entry;risk=qty*dist;entryfee=notional*fee
        ih0=int(np.searchsorted(ht,tm[e]));ihlast=int(np.searchsorted(hct,ct[last]))
        assert ht[ih0]==tm[e] and hct[ihlast]==ct[last]
        i0=np.searchsorted(ft,tm[e],side='right')
        reason='time';ambig=False;gap=False;exit_raw=None;exit_low=exit_high=None
        for k in range(ih0,ihlast+1):
            price,why,tie,isgap=(None,None,False,False) if fixed else exit_decision(ho[k],hh[k],hl[k],stop,target,d)
            if why or k==ihlast:
                reason=why or 'time';ambig=tie;gap=isgap
                exit_raw=float(price if why else hc[k]);exit_high=int(ht[k] if gap else hct[k]);exit_low=int(ht[k] if why else hct[k])
                if gap:exit_low=exit_high
                i1=np.searchsorted(ft,exit_high,side='right')
                fund=d*qty*(fc[i1]-fc[i0])
                ex=exit_raw*(1-d*slip);exitfee=qty*ex*fee
                pnl=d*qty*(ex-entry)-entryfee-exitfee-fund;eq=before+pnl
                mtm=eq
            else:
                ik=np.searchsorted(ft,hct[k],side='right')
                mtm=before+d*qty*(hc[k]-entry)-entryfee-d*qty*(fc[ik]-fc[i0])
            peak=max(peak,mtm);dd=max(dd,1-mtm/peak)
            assert mtm>0,'Equity exhausted, unsupported liquidation'
            curve.append(dict(time=int(ht[k] if gap else hct[k]),equity=float(mtm),trade_seq=len(trades)+1))
            if why or k==ihlast:break
        # Full-horizon excursions are exported ONLY for fixed-hold baseline.
        # Exit-hour extrema for stop trades are unknowable after a fill, so excluded.
        if fixed:
            favorable=hh[ih0:k+1] if d==1 else hl[ih0:k+1]
            adverse=hl[ih0:k+1] if d==1 else hh[ih0:k+1]
            fav=d*(favorable-entry)/entry;adv=-d*(adverse-entry)/entry
            mfe=float(max(0,fav.max()));mae=float(max(0,adv.max()))
            mfe_h=int(fav.argmax()+1);mae_h=int(adv.argmax()+1)
        else:mfe=mae=mfe_h=mae_h=None
        trades.append(dict(group=group,tf=ctx['tf'],indicator=NAMES[j],scenario=scenario['id'],seq=len(trades)+1,
            direction=d,signal_open_time=int(tm[t]),signal_confirm_time=int(ct[t]),entry_time=int(tm[e]),
            exit_time_lower=exit_low,exit_time_upper=exit_high,exit_reason=reason,ambiguous_hour=ambig,
            entry_raw=float(op[e]),exit_raw=exit_raw,entry_exec=entry,exit_exec=float(ex),atr_signal=float(aa[t]),
            stop=stop if not fixed else None,target=target if not fixed else None,quantity=float(qty),notional=float(notional),
            initial_risk=float(risk),planned_risk_fraction=float(risk/before) if not fixed else None,
            equity_before=float(before),gross_price_pnl=float(d*qty*(ex-entry)),fees=float(entryfee+exitfee),funding=float(fund),
            funding_events=int(i1-i0),pnl=float(pnl),equity_after=float(eq),net_R=float(pnl/risk),account_return=float(pnl/before),
            direction_hit=bool(d*(exit_raw-op[e])>0),regime='above_EMA200' if ctx['close'][t]>=ema[t] else 'below_EMA200',
            mfe_pct=mfe,mae_pct=mae,mfe_hours=mfe_h,mae_hours=mae_h,hours_held_upper=int(k-ih0+1)))
        available=int(np.searchsorted(ct,exit_high,side='left'))
    for a,b in zip(trades,trades[1:]):assert b['entry_time']>a['exit_time_upper']
    assert abs(sum(x['pnl'] for x in trades)-(eq-10000))<1e-7
    summary=summarize(trades)
    summary.update(group=group,tf=ctx['tf'],indicator=NAMES[j],scenario=scenario['id'],start=start,end=end,
        ending_equity=eq,total_return=eq/10000-1,maxdd_hourly_close=dd,
        raw_signal_bars=len(ledger),ignored=sum(x['status']=='ignored_position_open' for x in ledger),
        purged=sum(x['status']=='purged_boundary' for x in ledger),
        price_inconsistency_purged=sum(x['status']=='purged_price_inconsistency' for x in ledger),
        ambiguous_hours=sum(x['ambiguous_hour'] for x in trades))
    # Underwater duration uses calendar time (including flat intervals), sampled marks.
    peak=10000.;peak_time=start;longest=0;under=False
    for row in curve:
        if row['equity']>=peak:
            if under:longest=max(longest,row['time']-peak_time)
            peak=row['equity'];peak_time=row['time'];under=False
        else:
            under=True;longest=max(longest,row['time']-peak_time)
    if eq<peak:longest=max(longest,end-peak_time)
    summary['max_underwater_days']=longest/86400000
    return summary,trades,curve,ledger

def summarize(rows):
    n=len(rows)
    if not n:return dict(n=0,net_win=None,direction_accuracy=None,mean_net_R=None,profit_factor=None)
    p=np.array([r['pnl'] for r in rows]);rr=np.array([r['net_R'] for r in rows]);wins=float((p>0).mean())
    z=1.96;ctr=(wins+z*z/(2*n))/(1+z*z/n);half=z*np.sqrt(wins*(1-wins)/n+z*z/(4*n*n))/(1+z*z/n)
    streak=longest=0
    for x in p:
        streak=streak+1 if x<0 else 0;longest=max(longest,streak)
    positive=p[p>0].sum();negative=-p[p<0].sum()
    return dict(n=n,net_win=wins,direction_accuracy=float(np.mean([r['direction_hit'] for r in rows])),
        mean_net_R=float(rr.mean()),median_net_R=float(np.median(rr)),net_pnl=float(p.sum()),
        profit_factor=float(positive/negative) if negative else None,win_wilson_low=ctr-half,win_wilson_high=ctr+half,
        max_consecutive_losses=longest,long_n=sum(r['direction']==1 for r in rows),short_n=sum(r['direction']==-1 for r in rows),
        fees_total=float(sum(r['fees'] for r in rows)),funding_total=float(sum(r['funding'] for r in rows)),
        top3_share_of_gross_profits=float(np.sort(p[p>0])[-3:].sum()/positive) if positive else None,
        pnl_excluding_top3=float(p.sum()-np.sort(p[p>0])[-3:].sum()),
        fixed10_mean_mfe=float(np.mean([r['mfe_pct'] for r in rows])) if rows[0]['mfe_pct'] is not None else None,
        fixed10_mean_mae=float(np.mean([r['mae_pct'] for r in rows])) if rows[0]['mae_pct'] is not None else None)

def bootstrap(rows,seed):
    a=np.array([r['net_R'] for r in rows]);n=len(a)
    if n<5:return {'n':n,'low':None,'high':None}
    rng=np.random.default_rng(seed);starts=rng.integers(0,n,(2000,math.ceil(n/5)))
    ix=((starts[:,:,None]+np.arange(5))%n).reshape(2000,-1)[:,:n]
    samples=a[ix].mean(axis=1)
    return dict(n=n,low=float(np.quantile(samples,.025)),high=float(np.quantile(samples,.975)),block_trades=5,resamples=2000)

def audit(hour,dfs):
    validate_data(hour,HOUR)
    checks={'hourly_rows':len(hour),'TradingView_reconciliation':'PENDING_NO_EXPORT','future_forward_validation':'PENDING_FUTURE_DATA','datasets':{}}
    for tf,df in dfs.items():
        step=4*HOUR if tf=='4h' else 24*HOUR;validate_data(df,step)
        ag=hour.assign(bucket=hour.time//step).groupby('bucket').agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last'),volume=('volume','sum'))
        mismatches={}
        for c in ['open','high','low','close','volume']:
            ix=np.flatnonzero(~np.isclose(ag[c].to_numpy(),df[c].to_numpy(),rtol=1e-9,atol=.001))
            mismatches[c]=[dict(time=int(df.time.iloc[i]),native=float(df[c].iloc[i]),hourly_aggregate=float(ag[c].iloc[i])) for i in ix]
        bad=sorted(set(r['time'] for c in ['open','high','low','close'] for r in mismatches[c]))
        checks['datasets'][tf]={'rows':len(df),'hourly_aggregate_differences':mismatches,'bad_execution_bars':bad}
    return checks

def main():
    for d in [OUT,DER,OUT/'trades',OUT/'equity',OUT/'signal_ledger'] :d.mkdir(parents=True,exist_ok=True)
    expected=(ROOT/'config/protocol.sha256').read_text().split()[0]
    assert hashlib.sha256((ROOT/'config/protocol.json').read_bytes()).hexdigest()==expected
    hour=load_rows('binance_BTCUSDT_1h_trade.json');dfs={tf:load(tf) for tf in ['4h','1d']}
    checks=audit(hour,dfs);ft,fc,resolved=funding(hour)
    checks['funding']={'records':len(ft),'mark_kline_proxy':sum(r['mark_source']=='mark_kline_open_proxy' for r in resolved),'max_timestamp_hour_offset_ms':int((ft%HOUR).max())}
    assert checks['funding']['max_timestamp_hour_offset_ms']<4000
    summaries=[];breakdowns=[];uncertainty=[];folds=[]
    for tf,df in dfs.items():
        ind=indicators(df);ss,ll,ties=signals(df,ind);a=atr(df)
        rng=np.random.default_rng(20261016)
        picks=np.argwhere(ss);picks=picks[rng.choice(len(picks),min(80,len(picks)),replace=False)].tolist()
        picks += [[int(rng.integers(250,len(df))),int(rng.integers(10)),int(rng.integers(2))] for _ in range(80)]
        for t,j,d in picks:assert scalar_signal(df,ind,t,j,d)==ll[t,j,d]
        for cut in [len(df)//2,len(df)-37]:
            ii=indicators(df.iloc[:cut]);prefix,_,_=signals(df.iloc[:cut],ii)
            np.testing.assert_allclose(ind.iloc[:cut],ii,equal_nan=True);np.testing.assert_array_equal(ss[:cut],prefix)
            np.testing.assert_allclose(a[:cut],atr(df.iloc[:cut]),equal_nan=True)
        checks['datasets'][tf].update(scalar_signal_checks=len(picks),prefix_checks=2,pivot_ties=ties)
        jsonlines(DER/f'indicators_signals_{tf}.jsonl.gz',(
            dict(time=int(df.time.iloc[i]),confirm_time=int(df.close_time.iloc[i]),atr14=float(a[i]),
                **{f'{name}_value':float(ind.iloc[i,j]) for j,name in enumerate(NAMES)},
                **{f'{name}_{side}':int(ss[i,j,k]) for j,name in enumerate(NAMES) for k,side in enumerate(['bull','bear'])},
                **{f'{name}_{side}_length':int(ll[i,j,k]) for j,name in enumerate(NAMES) for k,side in enumerate(['bull','bear'])}) for i in range(len(df))))
        ctx=dict(df=df,sig=ss,hour=hour,ft=ft,fc=fc,tf=tf,time=df.time.to_numpy(),ct=df.close_time.to_numpy(),
            bad_execution_bars=checks['datasets'][tf]['bad_execution_bars'],
            open=df.open.to_numpy(),close=df.close.to_numpy(),atr=a,ema=df.close.ewm(span=200,adjust=False).mean().to_numpy(),
            ho=hour.open.to_numpy(),hh=hour.high.to_numpy(),hl=hour.low.to_numpy(),hc=hour.close.to_numpy(),ht=hour.time.to_numpy(),hct=hour.close_time.to_numpy())
        experiments=[(s,START,END,'full',None) for s in CFG['scenarios']]
        ev=pd.Timestamp('2023-01-01',tz='UTC')
        while ev.value//10**6<END:
            evend=ev+pd.DateOffset(months=6);dev=ev-pd.DateOffset(months=24)
            fid=ev.strftime('%Y%m');es=int(ev.value//10**6);ee=min(END,int(evend.value//10**6));ds=int(dev.value//10**6)
            fold=dict(id=fid,development_start=ds,evaluation_start=es,evaluation_end=ee,complete=ee==int(evend.value//10**6))
            if tf=='4h':folds.append(fold)
            experiments += [({'id':'risk_base'},ds,es,'dev_'+fid,fold),({'id':'risk_base'},es,ee,'eval_'+fid,fold)]
            ev=evend
        for scenario,start,end,period,fold in experiments:
            for j,name in enumerate(NAMES):
                group=f'{tf}_{name}_{scenario["id"]}_{period}'
                s,rows,curve,ledger=run(ctx,j,scenario,start,end,group)
                s.update(period=period,fold_complete=fold['complete'] if fold else None);summaries.append(s)
                jsonlines(OUT/'trades'/f'{group}.jsonl.gz',rows)
                jsonlines(OUT/'equity'/f'{group}.jsonl.gz',curve)
                jsonlines(OUT/'signal_ledger'/f'{group}.jsonl.gz',ledger)
                if period=='full' and scenario['id'] in ['risk_base','fixed10_1x']:
                    for field,values in [('direction',[1,-1]),('regime',['above_EMA200','below_EMA200']),('entry_year',list(range(2021,2027)))]:
                        for val in values:
                            subset=[r for r in rows if (pd.Timestamp(r['entry_time'],unit='ms',tz='UTC').year if field=='entry_year' else r[field])==val]
                            breakdowns.append(dict(group=group,dimension=field,value=val,**summarize(subset)))
                    uncertainty.append(dict(group=group,**bootstrap(rows,20261016+j+(0 if tf=='4h' else 100))))
            print(tf,period,scenario['id'],'complete',flush=True)
    save(OUT/'summary.json',summaries);save(OUT/'breakdowns.json',breakdowns);save(OUT/'uncertainty.json',uncertainty)
    save(OUT/'rolling_windows.json',folds)
    checks.update(protocol_sha256=expected,experiment_groups=len(summaries),single_position_and_cash_reconciliation=True,
        environment={'python':sys.version,'numpy':np.__version__,'pandas':pd.__version__,'platform':platform.platform()})
    save(OUT/'data_and_signal_checks.json',checks)
    print('saved',len(summaries),'groups',flush=True)

if __name__=='__main__':main()
