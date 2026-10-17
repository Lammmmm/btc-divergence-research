"""Independent path and as-of data checks for every reference-study event."""
import json
import numpy as np
from research import ROOT,load_rows,load,save
from reference_use import readlines,R,summarize

def main():
    hour=load_rows('binance_BTCUSDT_1h_trade.json')
    ht=hour.time.to_numpy();hc=hour.close_time.to_numpy()
    native={tf:load(tf) for tf in ['1d','4h']}
    ds=readlines(R/'daily_context_inputs.jsonl.gz')
    dct=np.array([x['confirm_time'] for x in ds])
    summaries=json.loads((R/'summary.json').read_text());count=0;maxerr=0
    for s in summaries:
        rows=readlines(R/'events'/f"{s['group']}.jsonl.gz")
        ledger=readlines(R/'ledgers'/f"{s['group']}.jsonl.gz")
        assert s['n']==len(rows)==sum(x['status']=='observed' for x in ledger)
        last=-1
        for row in rows:
            assert row['confirm_time']<row['entry_time'] and row['entry_time']>last
            last=row['window_end']
            d=row['direction'];price=row['entry'];scale=row['atr']
            lo=int(np.searchsorted(ht,row['entry_time']));hi=int(np.searchsorted(hc,row['window_end']))
            assert ht[lo]==row['entry_time'] and hc[hi]==row['window_end']
            arr=hour.iloc[lo:hi+1]
            fav=(arr.high.to_numpy()-price) if d==1 else (price-arr.low.to_numpy())
            adv=(price-arr.low.to_numpy()) if d==1 else (arr.high.to_numpy()-price)
            assert abs(max(0,fav.max())/scale-row['mfe_atr'])<1e-10
            assert abs(max(0,adv.max())/scale-row['mae_atr'])<1e-10
            assert bool(d*(arr.close.iloc[-1]-price)>0)==row['end_direction_positive']
            # Independently classify open, then adverse/favorable extrema.
            result='neither';touch=None
            for i,bar in enumerate(arr.itertuples()):
                opening=d*(bar.open-price)/scale
                upper=d*((bar.high if d==1 else bar.low)-price)/scale
                lower=d*((bar.low if d==1 else bar.high)-price)/scale
                if opening<=-1:result='adverse_first'
                elif opening>=1:result='favorable_first'
                elif lower<=-1:result='ambiguous_adverse_first' if upper>=1 else 'adverse_first'
                elif upper>=1:result='favorable_first'
                else:continue
                touch=i+1;break
            assert result==row['first_barrier'],(row,result)
            assert touch==row['first_touch_hours']
            # Independent last-confirmed daily row and latest qualifying event.
            k=np.searchsorted(dct,row['confirm_time'],side='right')-1
            assert row['daily_regime_source_close']==int(dct[k])
            state=0;event=-1
            for z in ds[:k+1][::-1]:
                bull=z['bull_count']>=1;bear=z['bear_count']>=1
                if bull or bear:
                    state=0 if bull and bear else (1 if bull else -1);event=z['confirm_time'];break
            if event<0 or row['confirm_time']-event>10*86400000:state=0
            assert row['daily_context_direction']==state
            assert row['daily_context_event_time']==event
            if row['config'].endswith('daily1'):assert state==d
            if row['config'].endswith('daily2'):
                state2=0;event2=-1
                for z in ds[:k+1][::-1]:
                    bull=z['bull_count']>=2;bear=z['bear_count']>=2
                    if bull or bear:
                        state2=0 if bull and bear else (1 if bull else -1);event2=z['confirm_time'];break
                if event2<0 or row['confirm_time']-event2>10*86400000:state2=0
                assert state2==d==row['daily2_context_direction']
        actual=summarize(rows)
        for key in ['primary_success','direction_accuracy','median_mae_atr','median_mfe_atr']:
            if rows:
                err=abs(actual[key]-s[key]);maxerr=max(maxerr,err);assert err<1e-12
        count+=len(rows)
    save(R/'independent_checks.json',dict(status='PASS',configuration_period_runs=len(summaries),event_rows=count,
         independent_barrier_replay=True,independent_daily_context_replay=True,nonoverlap_verified=True,
         mfe_mae_verified=True,max_summary_error=maxerr,notes='Event rows repeat across settings/periods; not independent sample count.'))
    print('Reference replay PASS:',len(summaries),'runs,',count,'event rows')

if __name__=='__main__':main()
