"""Focused replay of current Pine formal starts, preserving all prior studies."""
import hashlib, json
import numpy as np
from research import ROOT, START, END, load, load_rows, atr, run, summarize, bootstrap, save, jsonlines
from signal_port import indicators
from reference_use import readlines
from verify_hist_lifecycle import Lifecycle, find_span
from structure_reversal import observe, stats

OUT = ROOT/'results/hist_v432_backtest'
SPLIT = 1735689600000
PERIODS = [('full',START,END),('earlier',START,SPLIT),('recent',SPLIT,END)]

def raw_lengths(df, hist):
    c=df.close.to_numpy(); piv=[[],[]]; lengths=np.zeros((len(c),2),dtype=int)
    for t in range(10,len(c)):
        p=t-5
        for side in [0,1]:
            bull=side==0
            ok=(c[p]<=min(c[p-5:p]) and c[p]<min(c[p+1:t+1])) if bull else (c[p]>=max(c[p-5:p]) and c[p]>max(c[p+1:t+1]))
            if ok:piv[side]=([p]+piv[side])[:20]
            lengths[t,side]=find_span(c,hist,t,piv[side],bull,1,True)
    return lengths

def stream(df, lengths, aa, start, end):
    model=Lifecycle(); trace=[]; starts=np.zeros((len(df),2),dtype=bool)
    for t,bar in enumerate(df.itertuples()):
        if bar.time<start or bar.close_time>=end:continue
        span=int(max(lengths[t]));p=t-span
        allowed=np.isfinite(aa[t]) and aa[t]>0
        signal=(lengths[t]>0) if allowed else [False,False]
        pulses=model.step(t,bar.close,bar.high,bar.low,signal,
            float(df.high.iloc[p:t+1].max()),float(df.low.iloc[p:t+1].min()),float(aa[t]))
        if pulses['start']:starts[t,0 if pulses['start']==1 else 1]=True
        a=model.active
        trace.append(dict(index=t,time=int(bar.time),confirm_time=int(bar.close_time),
            bull_length=int(lengths[t,0]),bear_length=int(lengths[t,1]),**pulses,
            active_direction=a['direction'] if a else 0,event_id=model.sequence,
            confirmation=a['target'] if a else None,invalidation=a['invalid'] if a else None))
    return starts,trace

def main():
    OUT.mkdir(exist_ok=True)
    for sub in ['events','ledgers','timeline','trades','equity','trade_ledgers']:(OUT/sub).mkdir(exist_ok=True)
    protocol=ROOT/'config/hist_v432_backtest.json'
    cfg=json.loads(protocol.read_text(encoding='utf-8'))
    source=ROOT/cfg['source'];assert hashlib.sha256(source.read_bytes()).hexdigest()==cfg['source_sha256']
    cur=source.read_text(encoding='utf-8');old=(ROOT/'pine/Hist_Divergence_Line_v4_1.pine').read_text(encoding='utf-8')
    assert cur[cur.index('[macdValue, signalValue, hist]'):cur.index('// Display-only scoring;')]==old[old.index('[macdValue, signalValue, hist]'):old.index('// Formation scores')]
    hour=load_rows('binance_BTCUSDT_1h_trade.json')
    funds=readlines(ROOT/'data/derived/funding_resolved.jsonl.gz')
    ft=np.array([x['time'] for x in funds]);fc=np.r_[0.,np.cumsum([x['rate']*x['mark_price'] for x in funds])]
    quality=json.loads((ROOT/'results/data_and_signal_checks.json').read_text())
    structures=[];sides=[];trading=[];trade_sides=[];uncertainty=[];checks=[]
    for tf in cfg['timeframes']:
        df=load(tf);aa=atr(df);hist=indicators(df).Hist.to_numpy();lengths=raw_lengths(df,hist)
        saved=readlines(ROOT/f'data/derived/indicators_signals_{tf}.jsonl.gz')
        assert df.time.tolist()==[r['time'] for r in saved]
        np.testing.assert_allclose(hist,np.array([r['Hist_value'] for r in saved],dtype=float),equal_nan=True)
        np.testing.assert_array_equal(lengths,[[r['Hist_bull_length'],r['Hist_bear_length']] for r in saved])
        cut=len(df)//2
        prefix_hist=indicators(df.iloc[:cut]).Hist.to_numpy()
        np.testing.assert_allclose(hist[:cut],prefix_hist,equal_nan=True)
        np.testing.assert_array_equal(lengths[:cut],raw_lengths(df.iloc[:cut],prefix_hist))
        ctx=dict(df=df,hour=hour,ft=ft,fc=fc,tf=tf,time=df.time.to_numpy(),ct=df.close_time.to_numpy(),
            bad_execution_bars=quality['datasets'][tf]['bad_execution_bars'],open=df.open.to_numpy(),close=df.close.to_numpy(),
            atr=aa,ema=df.close.ewm(span=200,adjust=False).mean().to_numpy(),ho=hour.open.to_numpy(),hh=hour.high.to_numpy(),
            hl=hour.low.to_numpy(),hc=hour.close.to_numpy(),ht=hour.time.to_numpy(),hct=hour.close_time.to_numpy())
        for period,start,end in PERIODS:
            starts,trace=stream(df,lengths,aa,start,end)
            rows,ledger=observe(df,lengths>0,lengths,aa,[],start,end,tf,'Hist_v4.3.2',period)
            assert np.flatnonzero(starts.any(axis=1)).tolist()==[r['reference_index'] for r in rows]
            by_time={r['time']:r for r in trace}
            for r in rows:
                x=by_time[r['signal_time']]
                assert x['start']==r['direction'] and x['confirmation']==r['confirmation_level'] and x['invalidation']==r['invalidation_level']
                if r['status'] in ['success','failure']:
                    assert by_time[int(df.time.iloc[r['resolution_index']])][r['status']]==r['direction']
            if period=='full':
                _,pt=stream(df.iloc[:cut],lengths[:cut],aa[:cut],start,end)
                assert pt==trace[:len(pt)]
                previous=readlines(ROOT/f'results/hist_progress_v4/timeline_{tf}.jsonl.gz')
                keys=['time','bull_length','bear_length','start','success','failure','active_direction','confirmation','invalidation']
                assert [{k:r[k] for k in keys} for r in trace]==[{k:r[k] for k in keys} for r in previous]
            group=f'{tf}_{period}'
            jsonlines(OUT/'events'/f'{group}.jsonl.gz',rows);jsonlines(OUT/'ledgers'/f'{group}.jsonl.gz',ledger)
            jsonlines(OUT/'timeline'/f'{group}.jsonl.gz',trace)
            structures.append(dict(tf=tf,period=period,group=group,raw_signal_bars=len(ledger),**stats(rows)))
            for d in [1,-1]:sides.append(dict(group=group,tf=tf,period=period,direction=d,**stats([r for r in rows if r['direction']==d])))
            qr,ql=observe(df,lengths>0,lengths,aa,ctx['bad_execution_bars'],start,end,tf,'Hist',period)
            jsonlines(OUT/'events'/f'{group}_quality.jsonl.gz',qr);jsonlines(OUT/'ledgers'/f'{group}_quality.jsonl.gz',ql)
            before=readlines(ROOT/f'results/structure_reversal/events/{tf}_Hist_{period}.jsonl.gz')
            keys=['reference_index','resolution_index','status','confirmation_level','invalidation_level']
            assert [{k:r[k] for k in keys} for r in qr]==[{k:r[k] for k in keys} for r in before]
            structures.append(dict(tf=tf,period=period,group=group+'_quality',raw_signal_bars=len(ql),**stats(qr)))
            variants=[('current_starts',starts)] + ([('raw_hist',lengths>0)] if period=='full' else [])
            for variant,ss in variants:
                # research.run uses column 1 for Hist. All other indicators disabled.
                ctx['sig']=np.zeros((len(df),10,2),dtype=bool);ctx['sig'][:,1]=ss
                for scenario in [dict(id='risk_base'),dict(id='cost_2x',cost_multiplier=2)]:
                    g=f'{tf}_{variant}_{scenario["id"]}_{period}'
                    s,trades,curve,tl=run(ctx,1,scenario,start,end,g)
                    s.update(period=period,signal_stream=variant);trading.append(s)
                    jsonlines(OUT/'trades'/f'{g}.jsonl.gz',trades);jsonlines(OUT/'equity'/f'{g}.jsonl.gz',curve)
                    jsonlines(OUT/'trade_ledgers'/f'{g}.jsonl.gz',tl)
                    if scenario['id']=='risk_base' and variant=='current_starts':
                        for d in [1,-1]:trade_sides.append(dict(group=g,tf=tf,period=period,direction=d,**summarize([r for r in trades if r['direction']==d])))
                        uncertainty.append(dict(group=g,**bootstrap(trades,20261019)))
            print(tf,period,'structure',stats(rows)['completed_accuracy'],'events',len(rows),flush=True)
        checks.append(dict(tf=tf,source_bars=len(df),signal_span_mismatches=0,signals_recomputed=True,prefix_stable=True,full_timeline_matches_v4_formal_core=True))
    save(OUT/'structure_summary.json',structures);save(OUT/'structure_by_direction.json',sides)
    save(OUT/'trade_summary.json',trading);save(OUT/'trade_by_direction.json',trade_sides);save(OUT/'uncertainty.json',uncertainty)
    save(OUT/'checks.json',dict(status='PASS',source_sha256=cfg['source_sha256'],protocol_sha256=hashlib.sha256(protocol.read_bytes()).hexdigest(),datasets=checks,
        formal_core_exactly_equal_v41=True,batch_and_streaming_events_equal=True,old_quality_results_equal=True,
        TradingView_full_history_export='PENDING',scope='Python specification replay; not a Pine interpreter or new data feed validation.'))
    paths=[source,protocol,ROOT/'config/protocol.json',ROOT/'src/research.py',ROOT/'src/signal_port.py',ROOT/'src/structure_reversal.py',ROOT/'src/verify_hist_lifecycle.py',Path(__file__)]
    paths += list((ROOT/'data/raw').glob('*')) + list((ROOT/'data/derived').glob('*'))
    save(OUT/'input_hashes.json',{p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in paths if p.is_file()})

from pathlib import Path
if __name__=='__main__':main()
