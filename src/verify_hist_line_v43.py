"""Display invariants over saved formal event records; not a Pine interpreter."""
import gzip,hashlib,json
from pathlib import Path
R=Path(__file__).resolve().parents[1]
def view(r):
    d=r['active_direction']; outcome=r['success'] or r['failure']
    phase=r['view']['phase']
    value=(0 if d==1 else 100) if d else (0 if outcome==1 else 100) if outcome else r['view']['value'] if phase==1 and r['view']['value'] is not None else 50
    return dict(value=value,warning=bool(r['invalid_touch'] or r['failure'] or r['view']['warning']),context_change=r['view']['seam'])
def main():
    old=(R/'pine/Hist_Divergence_Line_v4_2.pine').read_text(encoding='utf-8');new=(R/'pine/Hist_Divergence_Line_v4_3.pine').read_text(encoding='utf-8')
    a='[macdValue, signalValue, hist]';b='// Display-only scoring;'
    assert old[old.index(a):old.index(b)]==new[new.index(a):new.index(b)]
    assert old[old.index(b):old.index('float mainValue =')]==new[new.index(b):new.index('// Display only: active bottom=')]
    assert old[old.index('alertcondition('):]==new[new.index('alertcondition('):]
    assert 'color=seam ? na' not in new and 'plot.style_linebr' not in new and 'plotshape(' not in new
    # Current event takes precedence over a same-close resolution of the previous event.
    template=dict(active_direction=-1,success=1,failure=0,invalid_touch=True,view=dict(phase=2,value=37,warning=True,seam=True))
    assert view(template)==dict(value=100,warning=True,context_change=True)
    template.update(active_direction=0,success=0,failure=-1);assert view(template)['value']==100
    template.update(failure=0,invalid_touch=False,view=dict(phase=0,value=None,warning=False,seam=True));assert view(template)['value']==50
    out=R/'results/hist_line_v4_3';out.mkdir(exist_ok=True);report=[]
    for tf in ['1d','4h']:
        with gzip.open(R/f'results/hist_line_v4_2/timeline_{tf}.jsonl.gz','rt',encoding='utf-8') as f:rows=[json.loads(x) for x in f]
        result=[];active_count=0;ended_count=0;warning_count=0
        for r in rows:
            v=view(r);assert 0<=v['value']<=100
            if r['active_direction']:
                assert v['value']==(0 if r['active_direction']==1 else 100);active_count+=1
            if (r['success'] or r['failure']) and not r['active_direction']:
                assert v['value']==(0 if (r['success'] or r['failure'])==1 else 100);ended_count+=1
            if r['invalid_touch'] or r['failure']:assert v['warning'];warning_count+=1
            result.append(dict(time=r['time'],**v,active_direction=r['active_direction'],start=r['start'],success=r['success'],failure=r['failure'],structure_progress=r['structure_progress']))
        with gzip.open(out/f'timeline_{tf}.jsonl.gz','wt',encoding='utf-8') as f:
            for r in result:f.write(json.dumps(r)+'\n')
        report.append(dict(tf=tf,bars=len(rows),active_horizontal_bars=active_count,terminal_bars=ended_count,immediate_warning_bars=warning_count,no_missing_values=True))
    report=dict(status='PASS',formal_core_equal_v42=True,formation_algorithm_equal_v42=True,alerts_equal_v42=True,source_sha256=hashlib.sha256((R/'pine/Hist_Divergence_Line_v4_3.pine').read_bytes()).hexdigest(),datasets=report,limits='Saved formal records reused. This checks the display specification and unchanged Pine source, not a new signal backtest or complete Pine export reconciliation.')
    (out/'checks.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
