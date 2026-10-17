"""20 independent single-position experiments. No indicator combinations."""
import json
import math
from pathlib import Path
import numpy as np
import pandas as pd
from backtest_divergence import load, indicators, signals, funding_arrays, validate_data, NAMES, FEE, SLIP

ROOT=Path(__file__).resolve().parent
START=1609459200000
SPLIT=1735689600000
END=1792108800000
INITIAL=10000.
HOLD=10
PERIODS=[('全期',START,END),('前段',START,SPLIT),('后段',SPLIT,END)]

def experiment(df,signal,ft,fc,tf,name,period,start,end):
    times=df.time.to_numpy(); ct=df.close_time.to_numpy()
    opens=df.open.to_numpy(); closes=df.close.to_numpy()
    eq=INITIAL; next_available=-1; trades=[]; peak=INITIAL; maxdd=0.
    curve=[]; raw=skipped=conflict=tail=0
    group=f'{tf.upper()}-{name}-{period}'
    for t in range(len(df)):
        if times[t]<start or ct[t]>=end: continue
        n=int(signal[t].sum())
        if not n: continue
        raw+=1
        if t<next_available:
            skipped+=1; continue
        if n==2:
            conflict+=1; continue
        e=t+1; x=t+HOLD
        if x>=len(df) or ct[x]>=end:
            tail+=1; continue
        direction=1 if signal[t,0] else -1
        entry=opens[e]*(1+direction*SLIP)
        exit_=closes[x]*(1-direction*SLIP)
        i0=np.searchsorted(ft,times[e],side='right')
        i1=np.searchsorted(ft,ct[x],side='right')
        signed_fund=direction*(fc[i1]-fc[i0])
        gross=direction*(closes[x]/opens[e]-1)
        price_return=direction*(exit_/entry-1)
        fees=FEE*(1+exit_/entry)
        funding=signed_fund/entry
        net=price_return-fees-funding
        # Reserve the entry commission; entry notional + commission = equity.
        before=eq; notional=before/(1+FEE); qty=notional/entry
        pnl=notional*net; eq=before+pnl
        for k in range(e,x+1):
            ik=np.searchsorted(ft,ct[k],side='right')
            fund_cash=direction*qty*(fc[ik]-fc[i0])
            mtm=before+direction*qty*(closes[k]-entry)-notional*FEE-fund_cash
            if k==x: mtm=eq
            peak=max(peak,mtm); maxdd=max(maxdd,1-mtm/peak)
            assert mtm>0, 'Equity depleted; liquidation model would be required.'
            curve.append([int(ct[k]),float(mtm)])
        trades.append(dict(group=group,tf=tf.upper(),name=name,period=period,seq=len(trades)+1,side='多' if direction==1 else '空',direction=direction,signal_time=int(times[t]),entry_time=int(times[e]),exit_time=int(ct[x]),entry_raw=float(opens[e]),exit_raw=float(closes[x]),entry=float(entry),exit=float(exit_),signed_funding_price_sum=float(signed_fund),gross=float(gross),price_return=float(price_return),fees=float(fees),funding=float(funding),net=float(net),equity_before=float(before),notional=float(notional),pnl=float(pnl),equity_after=float(eq)))
        next_available=x
    n=len(trades)
    assert n+skipped+conflict+tail==raw
    for a,b in zip(trades,trades[1:]): assert b['entry_time']>a['exit_time']
    gross=np.array([r['gross'] for r in trades]); net=np.array([r['net'] for r in trades]); cash=np.array([r['pnl'] for r in trades])
    p=float((gross>0).mean()) if n else 0; z=1.96
    ci_center=(p+z*z/(2*n))/(1+z*z/n) if n else 0
    ci_half=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/(1+z*z/n) if n else 0
    summary=dict(group=group,tf=tf.upper(),name=name,period=period,start=start,end=end,n=n,raw=raw,skipped=skipped,conflict=conflict,tail=tail,hit=p,net_win=float((net>0).mean()) if n else None,mean_net=float(net.mean()) if n else None,total_return=eq/INITIAL-1,ending=eq,maxdd=maxdd,profit_factor=float(cash[cash>0].sum()/-cash[cash<0].sum()) if (cash<0).any() else None,hit_low=ci_center-ci_half,hit_high=ci_center+ci_half,long_count=sum(r['direction']==1 for r in trades),short_count=sum(r['direction']==-1 for r in trades))
    return summary,trades,curve

def main():
    dfs={tf:load(tf) for tf in ['4h','1d']}
    ft,fc,missing=funding_arrays(dfs['4h'])
    summaries=[]; trades=[]; curves={}; checks={}
    for tf,df in dfs.items():
        step=14400000 if tf=='4h' else 86400000
        validate_data(df,step)
        ind=indicators(df); s,_,_=signals(df,ind)
        np.testing.assert_array_equal(s,np.load(ROOT/f'signals_{tf}.npz')['signals'])
        checks[tf]={'signals_match_previous_verified_port':True,'bars':len(df)}
        for period,start,end in PERIODS:
            for j,name in enumerate(NAMES):
                summary,rows,curve=experiment(df,s[:,j,:],ft,fc,tf,name,period,start,end)
                for r in rows:
                    assert r['entry_time']-r['signal_time']==step
                    assert r['exit_time']-r['entry_time']==HOLD*step-1
                    assert r['entry_time']>=start and r['exit_time']<end
                assert abs(sum(r['pnl'] for r in rows)-(summary['ending']-INITIAL))<1e-7
                summaries.append(summary); trades.extend(rows); curves[summary['group']]=curve
    # Synthetic alternating directions ensure that opposite signals are blocked too.
    base=START; step=14400000
    fixture=pd.DataFrame({'time':base+np.arange(40)*step,'close_time':base+(np.arange(40)+1)*step-1,'open':np.full(40,100.),'close':np.full(40,101.)})
    sig=np.zeros((40,2),dtype=bool); sig[np.arange(40),np.arange(40)%2]=True
    test,rows,_=experiment(fixture,sig,np.array([],dtype=np.int64),np.array([0.]),'4h','unit','全期',START,END)
    assert [r['signal_time'] for r in rows]==[base,base+10*step,base+20*step]
    assert test['skipped']==27
    checks.update({'20_unique_primary_tests':len([r for r in summaries if r['period']=='全期'])==20,'single_position_both_directions':True,'synthetic_alternating_signal_test':True,'trade_timing_checks':True,'cash_reconciles':True,'funding_price_proxy_records':missing,'full_period_trade_count':sum(r['n'] for r in summaries if r['period']=='全期'),'all_period_trade_count':len(trades)})
    payload={'settings':{'initial':INITIAL,'hold':HOLD,'fee':FEE,'slip':SLIP,'start':START,'end':END,'split':SPLIT,'regular_only':True,'prd':5,'maxpp':10,'maxbars':100,'price_source':'Close','dontconfirm':False},'summary':summaries,'trades':trades,'checks':checks}
    (ROOT/'single_backtest.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
    (ROOT/'single_curves.json').write_text(json.dumps(curves),encoding='utf-8')
    d=pd.DataFrame(summaries)
    for tf in ['4H','1D']:
        for period in ['全期','后段']:
            print(tf,period)
            print(d[(d.tf==tf)&(d.period==period)].sort_values('total_return',ascending=False)[['name','n','hit','net_win','total_return','maxdd','mean_net']].round(4).to_string(index=False))
    print(json.dumps(checks,ensure_ascii=False,indent=2))

if __name__=='__main__': main()
