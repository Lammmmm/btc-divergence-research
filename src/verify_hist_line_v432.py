"""Check incoming segment coloring against saved v4.3 display events."""
from pathlib import Path
import gzip,json,hashlib
R=Path(__file__).resolve().parents[1]
def colored(prev,cur):
    return bool(prev and cur['active'] and prev['active'] and cur['event']==prev['event'] and cur['direction']==prev['direction'] and cur['value']==prev['value']==(0 if cur['direction']==1 else 100))
def main():
    old=(R/'pine/Hist_Divergence_Line_v4_3_1.pine').read_text(encoding='utf-8');new=(R/'pine/Hist_Divergence_Line_v4_3_2.pine').read_text(encoding='utf-8')
    a=new.index('// A plot color paints');b=new.index('\nhline(',a)
    reverted=new[:a]+'plot(mainValue, "形成评分 / 背离持续状态", color=mainColor, linewidth=lineWidth, style=plot.style_line)'+new[b:]
    assert reverted.replace('v4.3.2','v4.3.1')==old
    # Regression: entry slopes, opposite switches and distinct same-direction events stay gray.
    top=dict(active=True,event=1,direction=-1,value=100)
    assert not colored(dict(active=False,event=0,direction=0,value=49),top)
    assert colored(top,dict(top))
    assert not colored(top,dict(top,event=2))
    assert not colored(top,dict(active=True,event=2,direction=1,value=0))
    assert not colored(top,dict(top,active=False))
    assert not colored(None,top)
    out=R/'results/hist_line_v4_3_2';out.mkdir(exist_ok=True);report=[]
    for tf in ['1d','4h']:
        with gzip.open(R/f'results/hist_line_v4_3/timeline_{tf}.jsonl.gz','rt') as f:rows=[json.loads(x) for x in f]
        prev=None;event=0;count=0;entries=0;trace=[]
        for r in rows:
            if r['start']:event+=1
            cur=dict(active=bool(r['active_direction']),event=event,direction=r['active_direction'],value=r['value'])
            c=colored(prev,cur)
            if c:assert cur['value']==prev['value'] and cur['value'] in [0,100];count+=1
            if r['start']:assert not c;entries+=1
            trace.append(dict(time=r['time'],value=r['value'],color=('blue' if cur['direction']==1 else 'red') if c else 'gray',event=event))
            prev=cur
        with gzip.open(out/f'segments_{tf}.jsonl.gz','wt',encoding='utf-8') as f:
            for r in trace:f.write(json.dumps(r)+'\n')
        report.append(dict(timeframe=tf,bars=len(rows),colored_horizontal_segments=count,entries_with_gray_incoming_segment=entries,colored_slopes=0))
    d=dict(status='PASS',only_title_and_plot_segment_color_changed=True,formal_logic_and_values_unchanged=True,source_sha256=hashlib.sha256((R/'pine/Hist_Divergence_Line_v4_3_2.pine').read_bytes()).hexdigest(),datasets=report,limits='Display-spec regression checks using saved event records; Pine visual checks recorded separately.')
    (out/'checks.json').write_text(json.dumps(d,indent=2)+'\n',encoding='utf-8');print(json.dumps(d,indent=2))
if __name__=='__main__':main()
