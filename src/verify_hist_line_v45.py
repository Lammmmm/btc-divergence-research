"""Causal display-only smoothing: bounds, lag, bypass, prefix and tick invariance."""
from pathlib import Path
import hashlib,json,math,statistics
from research import save,jsonlines
from reference_use import readlines
R=Path(__file__).resolve().parents[1]

def tick(raw,previous,length=3,limit=15,enabled=True,structure=True):
    if not enabled or not structure or previous is None:return raw
    delta=max(-limit,min(limit,2/(length+1)*(raw-previous)))
    return max(0,min(100,previous+delta))

def replay(values,**kwargs):
    result=[];previous=None
    for raw in values:
        previous=tick(raw,previous,**kwargs);result.append(previous)
    return result

def main():
    old=(R/'pine/Hist_Divergence_Line_v4_4.pine').read_text(encoding='utf-8')
    path=R/'pine/Hist_Divergence_Line_v4_5.pine';new=path.read_text(encoding='utf-8')
    start='[macdValue, signalValue, hist]';end='// Display only. Formation'
    assert old[old.index(start):old.index(end)]==new[new.index(start):new.index(end)]
    assert old[old.index('plot(bullScore,'):]==new[new.index('plot(bullScore,'):]
    for marker in ['color mainColor =','bool sameActiveEvent =','bool heldSegment =','color segmentColor =','bool warning =']:
        assert next(x for x in old.splitlines() if x.startswith(marker))==next(x for x in new.splitlines() if x.startswith(marker))
    assert 'nz(mainValue[1], rawMainValue)' in new and 'varip' not in new
    # Hand-computed response: no overshoot, 15-point cap, then EMA convergence.
    assert replay([0,100,100,100,100,100,100])==[0,15,30,45,60,75,87.5]
    assert replay([100,0,0,0])==[100,85,70,55]
    assert replay([42]*10)==[42]*10
    assert replay([0,100,0],enabled=False)==[0,100,0]
    assert replay([0,100,0],structure=False)==[0,100,0]
    assert replay([0,100,0],length=1,limit=100)==[0,100,0]
    # Multiple intrabar quotes recalculate from previous close, not prior tick.
    prior_close=35
    intrabar_values=[tick(raw,prior_close) for raw in [10,95,3,80]]
    assert intrabar_values==[22.5,50,20,50]
    assert intrabar_values[-1]==tick(80,prior_close)==50
    checks=[];out=R/'results/hist_line_v4_5';out.mkdir(exist_ok=True)
    for tf in ['4h','1d']:
        rows=readlines(R/f'results/hist_line_v4_4/timeline_{tf}.jsonl.gz')
        raw=[x['structure_value'] for x in rows];smooth=replay(raw)
        assert replay(raw,enabled=False)==raw
        held=[x['hold_value'] for x in rows];assert replay(held,structure=False)==held
        for cut in [1,17,len(raw)//2,len(raw)-1]:assert replay(raw[:cut])==smooth[:cut]
        trace=[];color_errors=0
        for i,(row,y) in enumerate(zip(rows,smooth)):
            assert math.isfinite(y) and 0<=y<=100
            if i:
                assert abs(y-smooth[i-1])<=15+1e-12
                assert min(smooth[i-1],raw[i])-1e-12<=y<=max(smooth[i-1],raw[i])+1e-12
            color=row['structure_color']
            if color!='gray':
                color_errors+=int(not row['active_direction'] or color!=('blue' if row['active_direction']==1 else 'red'))
            trace.append(dict(row,smoothed_value=y,smoothed_color=color))
        assert color_errors==0
        dif=lambda xs:[abs(b-a) for a,b in zip(xs,xs[1:])]
        rawstep=dif(raw);smstep=dif(smooth)
        checks.append(dict(tf=tf,bars=len(rows),events=sum(bool(x['start']) for x in rows),
            max_raw_step=max(rawstep),max_smoothed_step=max(smstep),
            mean_raw_step=statistics.mean(rawstep),mean_smoothed_step=statistics.mean(smstep),
            mean_absolute_display_lag=statistics.mean(abs(a-b) for a,b in zip(raw,smooth)),
            raw_steps_above_15=sum(x>15 for x in rawstep),smooth_steps_above_15=sum(x>15+1e-12 for x in smstep),
            color_sequence_exact_v44=True,color_outside_active_events=0,disable_exact_v44=True,hold_mode_exact_v44=True,prefix_invariant=True))
        jsonlines(out/f'timeline_{tf}.jsonl.gz',trace)
    result=dict(status='PASS',source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        defaults=dict(length=3,max_step=15),formal_candidate_core_exact_v44=True,
        original_audit_and_alerts_exact_v44=True,color_and_warning_expressions_exact_v44=True,
        datasets=checks,limit='Saved-record display replay plus source equality; not full TradingView historical export reconciliation. Smoothing deliberately lags numerical position, never state transitions.')
    save(out/'checks.json',result);print(json.dumps(result,indent=2))

if __name__=='__main__':main()
