"""Independently reconstruct frozen boxes, first close crossings and excursions."""
import json
import numpy as np
from research import ROOT,load,atr,save
from reference_use import readlines
R=ROOT/'results/structure_reversal'

def main():
    summaries=json.loads((R/'summary.json').read_text())
    checks=json.loads((ROOT/'results/data_and_signal_checks.json').read_text())
    dfs={tf:load(tf) for tf in ['1d','4h']};total=0
    saved={tf:readlines(ROOT/f'data/derived/indicators_signals_{tf}.jsonl.gz') for tf in dfs}
    for s in summaries:
        df=dfs[s['tf']];aa=atr(df);rows=readlines(R/'events'/f"{s['group']}.jsonl.gz")
        ledger=readlines(R/'ledgers'/f"{s['group']}.jsonl.gz")
        assert len(rows)==s['events']==sum(x['status']=='observed' for x in ledger)
        bad=set(checks['datasets'][s['tf']]['bad_execution_bars'])
        cutoff=1735689600000 if s['period']=='earlier' else 1792108800000
        stop=int(np.searchsorted(df.close_time.to_numpy(),cutoff))
        prev=-1
        for row in rows:
            t=row['reference_index'];p=t-row['divergence_length'];d=row['direction'];side='bull' if d==1 else 'bear'
            assert saved[s['tf']][t][s['indicator']+'_'+side]==1
            assert saved[s['tf']][t][s['indicator']+'_'+side+'_length']==t-p
            assert row['confirm_time']>=prev and row['pivot_confirm_time']<=row['confirm_time']
            high=max(df.high.iloc[p:t+1]);low=min(df.low.iloc[p:t+1])
            assert row['structure_high']==high and row['structure_low']==low
            assert not any(int(v) in bad for v in df.time.iloc[p:t+1])
            target=high if d==1 else low;invalid=low-.5*aa[t] if d==1 else high+.5*aa[t]
            assert target==row['confirmation_level'] and invalid==row['invalidation_level']
            status='pending';k=stop-1
            for i in range(t+1,stop):
                close=float(df.close.iloc[i])
                if int(df.time.iloc[i]) in bad:status='data_interrupted';k=i;break
                if (close>target if d==1 else close<target):status='success';k=i;break
                if (close<invalid if d==1 else close>invalid):status='failure';k=i;break
            assert status==row['status'] and k==row['resolution_index']
            last=max(t,k-1 if status=='data_interrupted' else k)
            part=df.iloc[t+1:last+1];ref=float(df.close.iloc[t])
            mfe=mae=0.
            if len(part):
                mfe=max(0,float(part.high.max())-ref) if d==1 else max(0,ref-float(part.low.min()))
                mae=max(0,ref-float(part.low.min())) if d==1 else max(0,float(part.high.max())-ref)
            assert abs(mfe/ref-row['mfe_pct'])<1e-12 and abs(mae/ref-row['mae_pct'])<1e-12
            assert row['wait_bars']==last-t
            assert abs(row['wait_days']-(df.close_time.iloc[last]-df.close_time.iloc[t])/86400000)<1e-12
            prev=row['status_time']
        for status in ['success','failure','pending','data_interrupted']:
            assert sum(r['status']==status for r in rows)==s[status]
        completed=s['success']+s['failure']
        assert s['completed']==completed
        if completed:assert abs(s['completed_accuracy']-s['success']/completed)<1e-12
        total+=len(rows)
    save(R/'independent_checks.json',dict(status='PASS',period_runs=len(summaries),event_rows=total,
        frozen_levels_from_raw_OHLC=True,first_close_resolution_replayed=True,excursions_recomputed=True,
        no_overlap=True,pivot_known_at_signal=True,censored_events_not_scored=True))
    print('Structure verification PASS',len(summaries),'runs',total,'event rows')

if __name__=='__main__':main()
