"""Display-only regression. Source equivalence proves the formal/candidate core is unchanged."""
import gzip, hashlib, json, math
from pathlib import Path
R=Path(__file__).resolve().parents[1]

def display(rows):
    focus=0; previous=None; smooth=None; value=50.; event=0; out=[]
    for r in rows:
        b,t=r['bull'],r['bear']; bs=b['score'] or 0.; ts=t['score'] or 0.
        active=r['active_direction']; forming=not active and not r['success'] and not r['failure']
        if forming:
            if focus==0: focus=0 if b['ref']==t['ref']==-1 else -1 if b['ref']==-1 else 1 if t['ref']==-1 else 1 if bs>=ts else -1
            elif focus==1 and t['ref']!=-1 and (b['ref']==-1 or (bs<50 and ts>bs+25)):focus=-1
            elif focus==-1 and b['ref']!=-1 and (t['ref']==-1 or (ts<50 and bs>ts+25)):focus=1
        elif active:focus=active
        candidate=b if focus==1 else t
        phase=2 if active else 3 if r['success'] or r['failure'] else 1 if forming and focus and candidate['ref']!=-1 else 0
        if r['start']:event+=1
        context=(phase,focus,candidate['ref'] if phase==1 else event if active else -1)
        changed=context!=previous
        if phase==1:
            raw=candidate['score']; smooth=raw if changed or smooth is None else .5*raw+.5*smooth
            assert 0<=smooth<=99
        else:smooth=None
        if active:
            value=r['structure_progress']
        elif r['success']:value=100.
        elif r['failure']:value=0.
        elif phase==1:value=smooth
        assert math.isfinite(value) and 0<=value<=100
        if active:assert value==r['structure_progress'], 'Structural smoothing would distort the price position'
        out.append(dict(time=r['time'],value=value,phase=phase,focus=focus,reset=changed))
        previous=context
    return out

def main():
    old=(R/'pine/Hist_Divergence_Progress_v4.pine').read_text(encoding='utf-8')
    new=(R/'pine/Hist_Divergence_Line_v4_1.pine').read_text(encoding='utf-8')
    begin='[macdValue, signalValue, hist]';end='color bullTraceColor ='
    core=old[old.index(begin):old.index(end)]
    assert new[new.index(begin):new.index('// ONE continuous display path.')]==core
    assert old[old.index('alertcondition('):]==new[new.index('alertcondition('):]
    visible=[line for line in new.splitlines() if line.startswith('plot(') and 'display=display.data_window' not in line]
    assert len(visible)==1 and 'style=plot.style_line)' in visible[0]
    assert 'plotshape(' not in new and 'plot.style_linebr' not in new
    reports=[]
    for tf in ('1d','4h'):
        with gzip.open(R/f'results/hist_progress_v4/timeline_{tf}.jsonl.gz','rt',encoding='utf-8') as f:rows=[json.loads(s) for s in f]
        trace=display(rows);cut=len(rows)//2
        assert display(rows[:cut])==trace[:cut]
        reports.append({'tf':tf,'bars':len(rows),'finite_continuous_values':True,'range_0_100':True,'structure_values_exact':True,'prefix_stable':True})
    result={'status':'PASS','source_sha256':hashlib.sha256((R/'pine/Hist_Divergence_Line_v4_1.pine').read_bytes()).hexdigest(),'formal_and_candidate_core_byte_equal_v4':True,'alerts_byte_equal_v4':True,'visible_curve_count':1,'shape_count':0,'datasets':reports,'scope':'Source regression plus offline display specification, not a Pine interpreter or full TradingView history export.'}
    out=R/'results/hist_line_v4_1';out.mkdir(exist_ok=True)
    (out/'checks.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
