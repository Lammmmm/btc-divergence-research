# This source code is subject to the Mozilla Public License 2.0:
# https://mozilla.org/MPL/2.0/
# Original Pine divergence logic: copyright LonesomeTheBlue.
# Python research port and evaluation additions: 2026.
"""Research event backtest ported from the user's Pine v4 script, not TV execution.
Dependencies: numpy, pandas, requests (download script only).
No orders, accounts, API keys or trade permissions are used.
"""
import json
import math
from pathlib import Path
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parent
NAMES=['MACD','Hist','RSI','Stoch','CCI','MOM','OBV','VWMACD','CMF','MFI']
START=pd.Timestamp('2021-01-01',tz='UTC').value//10**6
SPLIT=pd.Timestamp('2025-01-01',tz='UTC').value//10**6
FEE=.0005
SLIP=.0002

def load(tf):
    a=json.loads((ROOT/f'binance_BTCUSDT_{tf}.json').read_text())
    df=pd.DataFrame(a,columns=['time','open','high','low','close','volume','close_time','quote_volume','trades','buy_base','buy_quote','ignore'])
    return df.astype(float).assign(time=lambda d:d.time.astype('int64'),close_time=lambda d:d.close_time.astype('int64'))

def rma(a,n):
    out=np.full(len(a),np.nan); state=np.nan; seed=[]
    for i,x in enumerate(a):
        if np.isnan(x): continue
        if np.isnan(state):
            seed.append(x)
            if len(seed)==n: state=float(np.mean(seed))
        else: state=(state*(n-1)+x)/n
        out[i]=state
    return out

def indicators(df):
    c,h,l,v=(df[k] for k in ['close','high','low','volume'])
    ema=lambda a,n:a.ewm(span=n,adjust=False).mean()
    macd=ema(c,12)-ema(c,26)
    change=c.diff()
    up=rma(change.clip(lower=0).to_numpy(),14)
    down=rma((-change).clip(lower=0).to_numpy(),14)
    with np.errstate(divide='ignore',invalid='ignore'):
        rsi=100-100/(1+up/down)
    mean=c.rolling(10).mean()
    dev=c.rolling(10).apply(lambda x:np.mean(np.abs(x-x.mean())),raw=True)
    # The user's source is CLOSE for CCI and MFI, not the usual HLC3.
    positive=(c*v).where(change>0,0.).rolling(14).sum()
    negative=(c*v).where(change<0,0.).rolling(14).sum()
    data={
        'MACD':macd, 'Hist':macd-ema(macd,9), 'RSI':rsi,
        'Stoch':(100*(c-l.rolling(14).min())/(h.rolling(14).max()-l.rolling(14).min())).rolling(3).mean(),
        'CCI':(c-mean)/(.015*dev), 'MOM':c-c.shift(10),
        'OBV':(np.sign(change)*v).cumsum(),
        'VWMACD':(c*v).rolling(12).sum()/v.rolling(12).sum()-(c*v).rolling(26).sum()/v.rolling(26).sum(),
        'CMF':(((c-l)-(h-c))/(h-l)*v).rolling(21).sum()/v.rolling(21).sum(),
        'MFI':100-100/(1+positive/negative)}
    return pd.DataFrame(data)

def signals(df, ind):
    """Close source, prd=5, maxpp=10, maxbars=100, regular only,
    dontconfirm=False. Pivot records enter only after right 5 bars exist.
    Arrays hold real pivot indices (equivalent to original confirmation index-prd).
    """
    n=len(df); c=df.close.to_numpy(); a=ind.to_numpy()
    sig=np.zeros((n,10,2),dtype=bool) # 0=bull, 1=bear
    lengths=np.zeros((n,10,2),dtype=np.int16)
    pivots=[[],[]]; tied=0
    for t in range(10,n):
        p=t-5
        # Rightmost-tie selection: equality is allowed on the left only.
        for side in [0,1]:
            window=c[p-5:p+6]
            is_extreme=c[p]==(window.min() if side==0 else window.max())
            unique_right=np.all(c[p]<c[p+1:t+1]) if side==0 else np.all(c[p]>c[p+1:t+1])
            if is_extreme and unique_right:
                tied+=int(np.sum(window==c[p])>1)
                pivots[side].insert(0,p)
                del pivots[side][20:]
        end=t-1
        for side in [0,1]:
            bull=side==0
            gate=(a[t]>a[t-1]) | (c[t]>c[t-1]) if bull else (a[t]<a[t-1]) | (c[t]<c[t-1])
            for p in pivots[side][:10]:
                length=t-p
                if length>100: break
                if length<=5: continue
                price_ok=c[end]<c[p] if bull else c[end]>c[p]
                if not price_ok: continue
                indicator_ok=a[end]>a[p] if bull else a[end]<a[p]
                candidates=np.flatnonzero(gate & indicator_ok & ~sig[t,:,side])
                if not len(candidates): continue
                # Pine y=2..len-1, interpolated from endpoint t-1 to pivot.
                ys=np.arange(2,length)
                price_line=c[end]-(c[end]-c[p])/(length-1)*(ys-1)
                cross=(c[t-ys]<price_line) if bull else (c[t-ys]>price_line)
                if cross.any(): continue
                for j in candidates:
                    line=a[end,j]-(a[end,j]-a[p,j])/(length-1)*(ys-1)
                    crossed=(a[t-ys,j]<line) if bull else (a[t-ys,j]>line)
                    if not crossed.any():
                        sig[t,j,side]=True; lengths[t,j,side]=length
    return sig,lengths,tied

def funding_arrays(df4):
    records=json.loads((ROOT/'binance_BTCUSDT_funding.json').read_text())
    times=np.array([int(r['fundingTime']) for r in records],dtype=np.int64)
    rates=np.array([float(r['fundingRate']) for r in records])
    marks=np.array([float(r.get('markPrice') or 'nan') for r in records])
    missing=np.isnan(marks) | (marks<=0)
    ix=np.searchsorted(df4.time.to_numpy(),times,side='right')-1
    assert (ix>=0).all()
    marks[missing]=df4.open.to_numpy()[ix[missing]]
    return times,np.r_[0,np.cumsum(rates*marks)],int(missing.sum())

def run_events(df,sig,h,ft,fc,name,tf,side):
    times=df.time.to_numpy(); closes=df.close.to_numpy(); opens=df.open.to_numpy()
    endtimes=df.close_time.to_numpy(); direction=1 if side==0 else -1
    blocked_until=-1; trades=[]
    for t in np.flatnonzero(sig):
        if times[t]<START or t<blocked_until: continue
        e=t+1; x=t+h
        if x>=len(df): continue # Unfinished outcomes excluded.
        # Prevent development trades from using validation outcomes.
        if times[e]<SPLIT<=endtimes[x]: continue
        entry=opens[e]*(1+direction*SLIP)
        exit_=closes[x]*(1-direction*SLIP)
        i0=np.searchsorted(ft,times[e],side='right')
        i1=np.searchsorted(ft,endtimes[x],side='right')
        funding=direction*(fc[i1]-fc[i0])/entry
        gross=direction*(closes[x]/opens[e]-1)
        net=direction*(exit_/entry-1)-FEE*(1+exit_/entry)-funding
        trades.append(dict(tf=tf,name=name,side='bottom' if side==0 else 'top',h=h,signal_time=int(times[t]),entry_time=int(times[e]),exit_time=int(endtimes[x]),entry=entry,exit=exit_,gross=gross,net=net,funding=funding,split='development' if times[e]<SPLIT else 'validation'))
        blocked_until=x
    return trades

def stats(trades):
    if not trades: return {'n':0}
    net=np.array([r['net'] for r in trades]); gross=np.array([r['gross'] for r in trades]); n=len(net)
    p=float((gross>0).mean()); z=1.96
    center=(p+z*z/(2*n))/(1+z*z/n)
    half=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/(1+z*z/n)
    loss=-net[net<0].sum(); profit=net[net>0].sum()
    return dict(n=n,hit_pct=100*p,net_win_pct=100*float((net>0).mean()),mean_gross_pct=100*float(gross.mean()),mean_net_pct=100*float(net.mean()),median_net_pct=100*float(np.median(net)),profit_factor=float(profit/loss) if loss else None,ci_low_pct=100*(center-half),ci_high_pct=100*(center+half),mean_funding_pct=100*float(np.mean([r['funding'] for r in trades])))

def validate_data(df,step):
    assert df.time.is_unique and df.time.is_monotonic_increasing
    assert (np.diff(df.time)==step).all(), 'Missing candle'
    assert (df.close_time-df.time==step-1).all()
    assert (df.high>=df[['open','close','low']].max(axis=1)).all()
    assert (df.low<=df[['open','close','high']].min(axis=1)).all()
    assert (df.volume>=0).all()

def scalar_signal(df,ind,t,j,side):
    """Independent direct translation for selected bar checks."""
    c=df.close.to_numpy(); a=ind.iloc[:,j].to_numpy(); bull=side==0
    if not ((a[t]>a[t-1] or c[t]>c[t-1]) if bull else (a[t]<a[t-1] or c[t]<c[t-1])): return 0
    confirmed=[]
    for p in range(5,t-4):
        w=c[p-5:p+6]
        ok=(c[p]==min(w) and all(c[p]<c[p+1:p+6])) if bull else (c[p]==max(w) and all(c[p]>c[p+1:p+6]))
        if ok: confirmed.append(p)
    for p in confirmed[-10:][::-1]:
        length=t-p
        if length>100: break
        if length<=5: continue
        ok=(a[t-1]>a[t-length] and c[t-1]<c[p]) if bull else (a[t-1]<a[t-length] and c[t-1]>c[p])
        if not ok: continue
        slope1=(a[t-1]-a[t-length])/(length-1)
        slope2=(c[t-1]-c[t-length])/(length-1)
        v1=a[t-1]-slope1; v2=c[t-1]-slope2
        arrived=True
        for y in range(2,length):
            crossed=(a[t-y]<v1 or c[t-y]<v2) if bull else (a[t-y]>v1 or c[t-y]>v2)
            if crossed: arrived=False; break
            v1-=slope1; v2-=slope2
        if arrived: return length
    return 0

def main():
    dfs={tf:load(tf) for tf in ['4h','1d']}
    for tf,df in dfs.items(): validate_data(df,14400000 if tf=='4h' else 86400000)
    ag=dfs['4h'].assign(day=dfs['4h'].time//86400000).groupby('day').agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last'),volume=('volume','sum'))
    for key in ['open','high','low','close']:
        np.testing.assert_allclose(ag[key],dfs['1d'][key],rtol=1e-8,atol=.001)
    bad_volume=np.flatnonzero(~np.isclose(ag.volume.to_numpy(),dfs['1d'].volume.to_numpy(),rtol=1e-8,atol=.001))
    ft,fc,missing=funding_arrays(dfs['4h'])
    checks={'continuous_candles':True,'daily_OHLC_matches_six_4h_candles':True,'daily_volume_discrepancies':[dict(day=str(pd.to_datetime(dfs['1d'].time.iloc[i],unit='ms',utc=True)),daily=float(dfs['1d'].volume.iloc[i]),aggregated=float(ag.volume.iloc[i])) for i in bad_volume],'funding_mark_price_proxy_records':missing,'funding_total':len(ft),'prefix_checks':{},'scalar_checks':{},'pivot_ties':{}}
    all_trades=[]; all_summary=[]
    for tf,df in dfs.items():
        ind=indicators(df); sig,lengths,ties=signals(df,ind)
        checks['pivot_ties'][tf]=ties
        np.savez_compressed(ROOT/f'signals_{tf}.npz',signals=sig,lengths=lengths,indicators=ind.to_numpy())
        # Truncating future data must not change past indicator or signal values.
        cut=len(df)//2
        pref_ind=indicators(df.iloc[:cut]); pref_sig,_,_=signals(df.iloc[:cut],pref_ind)
        np.testing.assert_allclose(ind.iloc[:cut],pref_ind,equal_nan=True)
        assert np.array_equal(sig[:cut],pref_sig)
        checks['prefix_checks'][tf]=cut
        rng=np.random.default_rng(20261016)
        positives=np.argwhere(sig)
        chosen=positives[rng.choice(len(positives),min(60,len(positives)),replace=False)].tolist()
        chosen+= [[int(rng.integers(200,len(df))),int(rng.integers(10)),int(rng.integers(2))] for _ in range(60)]
        for t,j,side in chosen:
            assert scalar_signal(df,ind,t,j,side)==lengths[t,j,side],(tf,t,j,side)
        checks['scalar_checks'][tf]=len(chosen)
        candidates={name:sig[:,j,:] for j,name in enumerate(NAMES)}
        current=[0,2,6,9]
        for label,indices in [('Current4',current),('All10',list(range(10)))]:
            for threshold in [1,2,3]:
                candidates[f'{label}_atleast{threshold}']=sig[:,indices,:].sum(axis=1)>=threshold
        # Post-hoc candidates motivated by single-indicator results. These are
        # EXPLORATORY, not independently validated selections.
        for label,indices in [('Explore_OBV_Stoch',[6,3]),('Explore_Hist_RSI',[1,2])]:
            for threshold in [1,2]:
                candidates[f'{label}_atleast{threshold}']=sig[:,indices,:].sum(axis=1)>=threshold
        # Predeclared baseline, not a tuned strategy; same non-overlap mechanics.
        candidates['AlwaysDirection']=np.ones((len(df),2),dtype=bool)
        for name,cs in candidates.items():
            for h in [5,10,20]:
                for side in [0,1]:
                    trades=run_events(df,cs[:,side],h,ft,fc,name,tf,side)
                    all_trades.extend(trades)
                    for split in ['all','development','validation']:
                        subset=trades if split=='all' else [r for r in trades if r['split']==split]
                        all_summary.append(dict(tf=tf,name=name,h=h,side='bottom' if side==0 else 'top',split=split,**stats(subset)))
                for split in ['all','development','validation']:
                    subset=[r for r in all_trades if r['tf']==tf and r['name']==name and r['h']==h and (split=='all' or r['split']==split)]
                    all_summary.append(dict(tf=tf,name=name,h=h,side='both',split=split,**stats(subset)))
        print(tf,'signals',sig.sum(axis=(0,2)).tolist(),flush=True)
    (ROOT/'checks.json').write_text(json.dumps(checks,indent=2))
    (ROOT/'results.json').write_text(json.dumps(all_summary,indent=2))
    (ROOT/'trades.json').write_text(json.dumps(all_trades))
    result=pd.DataFrame(all_summary)
    for tf in ['4h','1d']:
        print('\n',tf,'VALIDATION H10')
        print(result.query('tf==@tf and h==10 and split=="validation" and side=="both"').sort_values('mean_net_pct',ascending=False)[['name','n','hit_pct','net_win_pct','mean_net_pct','profit_factor']].to_string(index=False))
    print(json.dumps(checks,indent=2))

if __name__=='__main__': main()
