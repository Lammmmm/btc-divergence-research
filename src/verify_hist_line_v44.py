"""Display-mode regression against v4.3.2; formal/candidate engine stays exact."""
from pathlib import Path
import hashlib,json,math
from research import jsonlines,save,load
from reference_use import readlines
R=Path(__file__).resolve().parents[1]

def value(r, mode):
    if mode=='hold':return r['value']
    if r['active_direction']:return r['structure_progress']
    if r['success']:return 100.
    if r['failure']:return 0.
    return r['value']

def segment(prev,cur,mode):
    same=bool(prev and prev['active'] and cur['active'] and prev['event']==cur['event'] and prev['direction']==cur['direction'])
    colored=same and (mode=='structure' or cur['value']==prev['value']==(0 if cur['direction']==1 else 100))
    return ('blue' if cur['direction']==1 else 'red') if colored else 'gray'

def main():
    old=(R/'pine/Hist_Divergence_Line_v4_3_2.pine').read_text(encoding='utf-8');new=(R/'pine/Hist_Divergence_Line_v4_4.pine').read_text(encoding='utf-8')
    a='[macdValue, signalValue, hist]'
    assert old[old.index(a):old.index('// Display only: active bottom=')]==new[new.index(a):new.index('// Display only. Formation')]
    assert old[old.index('plot(bullScore,'):]==new[new.index('plot(bullScore,'):]
    assert 'plot.style_linebr' not in new and 'color=seam ? na' not in new
    assert 'string displayMode = input.string("结构位置"' in new and '"持续横线"' in new
    assert '等待结构结果' in new and '0失效 · 100反转确认' in new
    # Terminal and same-close restart semantics. A new event supersedes old result.
    r=dict(active_direction=1,structure_progress=37.,success=-1,failure=0,value=0.)
    assert value(r,'structure')==37 and value(r,'hold')==0
    r.update(active_direction=0,success=1);assert value(r,'structure')==100
    r.update(success=0,failure=-1);assert value(r,'structure')==0
    prev=dict(active=True,event=1,direction=1,value=31)
    cur=dict(prev,value=42)
    assert segment(prev,cur,'structure')=='blue' and segment(prev,cur,'hold')=='gray'
    assert segment(prev,dict(cur,event=2),'structure')=='gray'
    assert segment(dict(prev,active=False),cur,'structure')=='gray'
    assert segment(prev,dict(cur,active=False),'structure')=='gray'
    out=R/'results/hist_line_v4_4';out.mkdir(exist_ok=True);checks=[]
    for tf in ['4h','1d']:
        rows=readlines(R/f'results/hist_line_v4_3/timeline_{tf}.jsonl.gz')
        colors=readlines(R/f'results/hist_line_v4_3_2/segments_{tf}.jsonl.gz')
        formal=readlines(R/f'results/hist_v432_backtest/timeline/{tf}_full.jsonl.gz')
        by_time={int(b.time):b.close for b in load(tf).itertuples()}
        event=0;prevs={'hold':None,'structure':None};trace=[];changes=0;inside=0
        assert len(rows)==len(colors)==len(formal)
        for r,oldcolor,f in zip(rows,colors,formal):
            assert r['time']==f['time']==oldcolor['time']
            if r['start']:event+=1
            rec=dict(time=r['time'],active_direction=r['active_direction'],event=event,start=r['start'],success=r['success'],failure=r['failure'],warning=r['warning'])
            for mode in ['hold','structure']:
                v=value(r,mode);assert math.isfinite(v) and 0<=v<=100
                cur=dict(active=bool(r['active_direction']),event=event,direction=r['active_direction'],value=v)
                color=segment(prevs[mode],cur,mode);rec[mode+'_value']=v;rec[mode+'_color']=color
                if mode=='hold':assert v==oldcolor['value'] and color==oldcolor['color']
                if mode=='structure' and cur['active']:
                    expected=max(0,min(100,100*(by_time[r['time']]-f['invalidation'])/(f['confirmation']-f['invalidation'])))
                    assert abs(v-expected)<1e-10
                    if prevs[mode] and prevs[mode]['active'] and prevs[mode]['event']==event:
                        inside+=1;changes+=int(v!=prevs[mode]['value'])
                prevs[mode]=cur
            trace.append(rec)
        jsonlines(out/f'timeline_{tf}.jsonl.gz',trace)
        checks.append(dict(tf=tf,bars=len(rows),events=event,old_mode_values_and_colors_identical=True,
            structure_position_matches_frozen_prices=True,within_event_segments=inside,dynamic_segments=changes,no_missing_values=True))
    result=dict(status='PASS',source_sha256=hashlib.sha256((R/'pine/Hist_Divergence_Line_v4_4.pine').read_bytes()).hexdigest(),
        formal_candidate_core_exact_v432=True,audit_plots_and_alerts_exact_v432=True,synthetic_edge_assertions=8,datasets=checks,
        limit='Display specification over saved records plus exact Pine core comparison; not full historical Pine export reconciliation or a new profitability backtest.')
    save(out/'checks.json',result);print(json.dumps(result,indent=2))

if __name__=='__main__':main()
