"""Check all saved lifecycle bars and v3 Pine source; retain reproducible audit rows."""
import json,hashlib
from collections import deque,Counter
from research import ROOT,jsonlines,save
from reference_use import readlines
from hist_state_v3 import coordinates

def main():
    old=(ROOT/'pine/Hist_Divergence_Line_v2.pine').read_text(encoding='utf-8')
    new=(ROOT/'pine/Hist_Divergence_State_v3.pine').read_text(encoding='utf-8')
    # Only label Y coordinates may differ inside the signal/lifecycle core.
    start='[macdValue, signalValue, hist]';end='color phaseColor ='
    core=lambda s:s[s.index(start):s.index(end)]
    adjusted=core(old).replace('label.new(bar_index, hist, lastResultText','label.new(bar_index, 50, lastResultText').replace('label.new(bar_index, hist, "#"','label.new(bar_index, direction == 1 ? 0 : 100, "#"')
    assert adjusted==core(new)
    assert old[old.index('alertcondition('):]==new[new.index('alertcondition('):]
    assert all(x not in new for x in ['plot.style_columns','plotshape(','bgcolor(','line.new(','plotcandle(','plot(hist, "Hist 背离折线"','showMacdLines'])
    plots=[x for x in new.splitlines() if x.startswith('plot(') and 'display=display.data_window' not in x]
    assert len(plots)==1 and plots[0].startswith('plot(stateScore,')
    out=ROOT/'results/hist_state_v3';out.mkdir(exist_ok=True)
    datasets=[]
    for tf in ['1d','4h']:
        saved=readlines(ROOT/f'data/derived/indicators_signals_{tf}.jsonl.gz')
        states=readlines(ROOT/f'results/hist_lifecycle/timeline_{tf}.jsonl.gz')
        by_time={r['time']:r for r in states};q=deque(maxlen=100);rows=[];counts=Counter();starts=Counter()
        for source in saved:
            q.append(source['Hist_value'])
            r=by_time.get(source['time'])
            if r is None:continue
            d=r['active_direction'];conflict=r['bull_length']>0 and r['bear_length']>0
            preview=0 if d or conflict else 1 if r['potential_bull']>0 and r['potential_bear']==0 else -1 if r['potential_bear']>0 and r['potential_bull']==0 else 0
            score,color=coordinates(q,d,preview)
            assert 0<=score<=100
            assert (score==0)==(d==1) and (score==100)==(d==-1)
            if r['start']:assert d==r['start'];starts[str(d)]+=1
            if (r['success'] or r['failure']) and not r['start']:assert 0<score<100 and color=='gray'
            counts[color]+=1
            rows.append(dict(time=r['time'],state_score=score,color=color,active_direction=d,preview_direction=preview,start=r['start'],success=r['success'],failure=r['failure']))
        assert len(rows)==len(states)
        jsonlines(out/f'coordinates_{tf}.jsonl.gz',rows)
        datasets.append(dict(tf=tf,bars=len(rows),minimum=min(r['state_score'] for r in rows),maximum=max(r['state_score'] for r in rows),color_bars=dict(counts),starts=dict(starts),all_endpoint_and_resolution_assertions=True))
    result=dict(status='PASS',signal_lifecycle_unchanged_except_label_coordinates=True,alerts_unchanged=True,visible_plots_only_state_score=True,datasets=datasets,source_sha256=hashlib.sha256((ROOT/'pine/Hist_Divergence_State_v3.pine').read_bytes()).hexdigest(),scope='Python display specification over saved lifecycle records, plus Pine source equivalence; not a Pine interpreter or full TradingView history reconciliation.')
    save(out/'offline_checks.json',result);print(json.dumps(result,indent=2))

if __name__=='__main__':main()
