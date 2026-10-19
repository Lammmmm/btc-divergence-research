"""Independent raw-price outcome, execution and accounting checks for v4.3.2."""
import json
import numpy as np
from research import ROOT, load, load_rows, atr, save
from reference_use import readlines
from backtest_hist_v432 import OUT, PERIODS

def main():
    dfs={tf:load(tf) for tf in ['4h','1d']};periods={p:(s,e) for p,s,e in PERIODS}
    quality=json.loads((ROOT/'results/data_and_signal_checks.json').read_text())
    structures=json.loads((OUT/'structure_summary.json').read_text())
    event_count=0
    for s in structures:
        df=dfs[s['tf']];aa=atr(df);start,end=periods[s['period']]
        rows=readlines(OUT/'events'/f"{s['group']}.jsonl.gz")
        stop=int(np.searchsorted(df.close_time,end));prev=-1
        bad=set(quality['datasets'][s['tf']]['bad_execution_bars']) if s['group'].endswith('_quality') else set()
        for r in rows:
            t=r['reference_index'];p=t-r['divergence_length'];d=r['direction'];ref=float(df.close.iloc[t])
            high=float(df.high.iloc[p:t+1].max());low=float(df.low.iloc[p:t+1].min())
            target=high if d==1 else low;invalid=low-.5*aa[t] if d==1 else high+.5*aa[t]
            assert r['confirm_time']>=prev and p+5<=t
            assert not any(x in bad for x in df.time.iloc[p:t+1])
            assert r['confirmation_level']==target and r['invalidation_level']==invalid
            k=stop-1;status='pending'
            for i in range(t+1,stop):
                if df.time.iloc[i] in bad:k=i;status='data_interrupted';break
                if d*(df.close.iloc[i]-target)>0:k=i;status='success';break
                if d*(df.close.iloc[i]-invalid)<0:k=i;status='failure';break
            assert (k,status)==(r['resolution_index'],r['status'])
            last=max(t,k-1 if status=='data_interrupted' else k);part=df.iloc[t+1:last+1]
            mae=mfe=0.
            if len(part):
                mae=max(0,ref-part.low.min()) if d==1 else max(0,part.high.max()-ref)
                mfe=max(0,part.high.max()-ref) if d==1 else max(0,ref-part.low.min())
            assert abs(mae/ref-r['mae_pct'])<1e-12 and abs(mfe/ref-r['mfe_pct'])<1e-12
            prev=r['status_time'];event_count+=1
        assert len(rows)==s['events']
        for key in ['success','failure','pending','data_interrupted']:assert sum(r['status']==key for r in rows)==s[key]
        assert s['completed']==s['success']+s['failure']
        assert s['completed_accuracy']==s['success']/s['completed']

    hour=load_rows('binance_BTCUSDT_1h_trade.json');ht=hour.time.to_numpy();hc=hour.close_time.to_numpy()
    funds=readlines(ROOT/'data/derived/funding_resolved.jsonl.gz');ft=np.array([r['time'] for r in funds]);fv=np.array([r['rate']*r['mark_price'] for r in funds])
    trade_summaries=json.loads((OUT/'trade_summary.json').read_text());trade_count=0;max_error=0.
    old=json.loads((ROOT/'results/summary.json').read_text())
    for s in trade_summaries:
        trades=readlines(OUT/'trades'/f"{s['group']}.jsonl.gz");curve=readlines(OUT/'equity'/f"{s['group']}.jsonl.gz")
        ledger=readlines(OUT/'trade_ledgers'/f"{s['group']}.jsonl.gz")
        assert len(trades)==s['n']==sum(r['status']=='entered' for r in ledger)
        df=dfs[s['tf']];aa=atr(df);times=df.time.to_numpy();ct=df.close_time.to_numpy()
        mult=2 if s['scenario']=='cost_2x' else 1;fee=.0005*mult;slip=.0002*mult;equity=10000.;last_exit=-1
        events=readlines(OUT/'events'/f"{s['tf']}_{s['period']}.jsonl.gz")
        starts={r['signal_time']:r['direction'] for r in events}
        for tr in trades:
            t=int(np.searchsorted(times,tr['signal_open_time']));d=tr['direction'];entry_index=t+1;last=t+10
            if s['signal_stream']=='current_starts':assert starts[tr['signal_open_time']]==d
            assert tr['entry_time']==times[entry_index]>tr['signal_confirm_time'] and tr['entry_time']>last_exit
            assert ct[last]<s['end']
            assert not any(times[entry_index]<=b<=times[last] for b in quality['datasets'][s['tf']]['bad_execution_bars'])
            entry=float(df.open.iloc[entry_index])*(1+d*slip);dist=1.5*aa[t]
            qty=min(equity*.005/dist,equity/(entry*(1+fee)))
            target=entry+d*2*dist;stop=entry-d*dist
            assert abs(qty-tr['quantity'])<1e-8 and abs(entry-tr['entry_exec'])<1e-8
            lo=int(np.searchsorted(ht,times[entry_index]));hi=int(np.searchsorted(hc,ct[last]));exit_price=None
            for k in range(lo,hi+1):
                bar=hour.iloc[k];why=None;gap=False;ambiguous=False
                if d*(bar.open-stop)<=0:exit_price=float(bar.open);why='stop_gap';gap=True
                elif d*(bar.open-target)>=0:exit_price=float(bar.open);why='target_gap';gap=True
                else:
                    stop_hit=bar.low<=stop if d==1 else bar.high>=stop
                    target_hit=bar.high>=target if d==1 else bar.low<=target
                    if stop_hit:exit_price=stop;why='stop';ambiguous=bool(target_hit)
                    elif target_hit:exit_price=target;why='target'
                if why or k==hi:
                    lower=int(ht[k] if why else hc[k]);upper=int(ht[k] if gap else hc[k])
                    why=why or 'time';exit_price=float(bar.close) if exit_price is None else exit_price
                    break
            assert why==tr['exit_reason'] and lower==tr['exit_time_lower'] and upper==tr['exit_time_upper']
            assert ambiguous==tr['ambiguous_hour'] and abs(exit_price-tr['exit_raw'])<1e-8
            ex=exit_price*(1-d*slip);fees=qty*(entry+ex)*fee
            funding=d*qty*float(fv[(ft>times[entry_index])&(ft<=upper)].sum())
            pnl=d*qty*(ex-entry)-fees-funding
            assert abs(fees-tr['fees'])<1e-8 and abs(funding-tr['funding'])<1e-7 and abs(pnl-tr['pnl'])<1e-7
            assert abs(equity-tr['equity_before'])<1e-7
            # Independently verify every hourly equity mark, including floating P&L.
            points=[x for x in curve if x['trade_seq']==tr['seq']]
            assert len(points)==k-lo+2 and points[0]['equity']==tr['equity_before']
            for offset,j in enumerate(range(lo,k+1),1):
                if j==k:expected=equity+pnl;tm=upper
                else:
                    funding_so_far=d*qty*float(fv[(ft>times[entry_index])&(ft<=hc[j])].sum())
                    expected=equity+d*qty*(hour.close.iloc[j]-entry)-qty*entry*fee-funding_so_far;tm=int(hc[j])
                assert points[offset]['time']==tm and abs(expected-points[offset]['equity'])<1e-7
            equity+=pnl;last_exit=upper;max_error=max(max_error,abs(equity-tr['equity_after']));trade_count+=1
        assert abs(equity-s['ending_equity'])<1e-7
        peak=10000.;dd=0.
        for p in curve:peak=max(peak,p['equity']);dd=max(dd,1-p['equity']/peak)
        assert abs(dd-s['maxdd_hourly_close'])<1e-12
        assert abs(sum(r['pnl']>0 for r in trades)/len(trades)-s['net_win'])<1e-12
        if s['signal_stream']=='raw_hist':
            ref=next(x for x in old if x['tf']==s['tf'] and x['indicator']=='Hist' and x['period']=='full' and x['scenario']==s['scenario'])
            for key in ['n','net_win','total_return','maxdd_hourly_close','ending_equity']:assert abs(ref[key]-s[key])<1e-10
    save(OUT/'independent_checks.json',dict(status='PASS',structure_rows_all_runs=event_count,trade_rows_all_runs=trade_count,
        first_close_outcomes=True,levels_and_excursions=True,next_open_entries=True,independent_hourly_exit_replay=True,
        individual_funding_and_fees=True,hourly_equity_marks_replayed=True,drawdown=True,max_cash_error=max_error,
        old_raw_hist_baselines_reproduced=True,notes='Includes repeated histories across periods and cost scenarios; not independent sample counts.'))
    print('Independent replay PASS:',event_count,'structure rows,',trade_count,'trade rows; cash error',max_error)

if __name__=='__main__':main()
