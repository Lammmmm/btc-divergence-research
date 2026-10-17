"""Recompute all saved trade accounting and summary totals independently."""
import gzip,json,math
from pathlib import Path
import numpy as np
R=Path(__file__).resolve().parents[1]
def read(p):
    with gzip.open(p,'rt',encoding='utf-8') as f:return [json.loads(s) for s in f]
summary=json.loads((R/'results/summary.json').read_text())
funding=read(R/'data/derived/funding_resolved.jsonl.gz')
ft=np.array([x['time'] for x in funding],dtype=np.int64)
fv=np.array([x['rate']*x['mark_price'] for x in funding])
total=0;maxerr=0;primary=0
for s in summary:
    rows=read(R/'results/trades'/f"{s['group']}.jsonl.gz")
    curve=read(R/'results/equity'/f"{s['group']}.jsonl.gz")
    ledger=read(R/'results/signal_ledger'/f"{s['group']}.jsonl.gz")
    assert len(rows)==s['n']==sum(x['status']=='entered' for x in ledger)
    assert len(ledger)==s['raw_signal_bars']
    prior=10000.;prev_exit=-1
    cost=2 if s['scenario']=='cost_2x' else 1
    for t in rows:
        assert t['signal_confirm_time']<t['entry_time']<=t['exit_time_lower']<=t['exit_time_upper']
        assert t['entry_time']>prev_exit
        assert s['start']<=t['signal_open_time']<t['exit_time_upper']<s['end']
        assert abs(t['equity_before']-prior)<1e-8
        assert abs(t['fees']-t['quantity']*(t['entry_exec']+t['exit_exec'])*.0005*cost)<1e-8
        selected=(ft>t['entry_time'])&(ft<=t['exit_time_upper'])
        independent_funding=t['direction']*t['quantity']*fv[selected].sum()
        assert abs(independent_funding-t['funding'])<1e-7
        pnl=t['direction']*t['quantity']*(t['exit_exec']-t['entry_exec'])-t['fees']-t['funding']
        assert abs(pnl-t['pnl'])<1e-8
        assert t['notional']*(1+.0005*cost) <= t['equity_before']+1e-7
        if s['scenario']!='fixed10_1x':assert t['initial_risk']<=t['equity_before']*.005+1e-8
        prior+=pnl;maxerr=max(maxerr,abs(prior-t['equity_after']));prev_exit=t['exit_time_upper']
    assert abs(prior-s['ending_equity'])<1e-7
    peak=10000.;dd=0;last=-1
    for point in curve:
        assert point['time']>=last;last=point['time']
        peak=max(peak,point['equity']);dd=max(dd,1-point['equity']/peak)
    assert abs(dd-s['maxdd_hourly_close'])<1e-12
    assert abs(sum(r['pnl'] for r in rows)-(prior-10000))<1e-7
    if rows:
        assert abs(np.mean([r['pnl']>0 for r in rows])-s['net_win'])<1e-12
        assert abs(np.mean([r['net_R'] for r in rows])-s['mean_net_R'])<1e-12
    total+=len(rows)
    if s['period']=='full' and s['scenario']=='risk_base':primary+=len(rows)
out=dict(status='PASS',groups=len(summary),trade_rows_all_groups=total,primary_trade_rows=primary,
    max_equity_accounting_error=maxerr,overlap_checks=True,signal_before_entry=True,fees_and_cash=True,
    drawdown_recomputed=True,funding_recomputed_from_individual_events=True,
    notes='Repeated history across scenarios/windows is not independent sample size.')
(R/'results/accounting_checks.json').write_text(json.dumps(out,indent=2))
print(json.dumps(out,indent=2))
