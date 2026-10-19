"""Endpoint-only color invariant across both modes; unchanged divergence core."""
from pathlib import Path
import hashlib,json,math
from research import save,jsonlines
from reference_use import readlines
from verify_hist_line_v45 import tick
R=Path(__file__).resolve().parents[1]

def color(previous,current):
    if not previous:return 'gray'
    same=current['active_direction'] and previous['active_direction']==current['active_direction'] and current['event']==previous['event']
    endpoint=0 if current['active_direction']==1 else 100
    return ('blue' if endpoint==0 else 'red') if same and current['value']==previous['value']==endpoint else 'gray'

def main():
    old=(R/'pine/Hist_Divergence_Line_v4_5.pine').read_text(encoding='utf-8');p=R/'pine/Hist_Divergence_Line_v4_5_1.pine';new=p.read_text(encoding='utf-8')
    a='[macdValue, signalValue, hist]';b='// Display only. Formation'
    assert old[old.index(a):old.index(b)]==new[new.index(a):new.index(b)]
    assert old[old.index('plot(bullScore,'):]==new[new.index('plot(bullScore,'):]
    assert 'color segmentColor = heldSegment ? mainColor : mutedColor' in new
    assert 'input.string("持续横线", "主线显示模式"' in new
    # Entry, exit, interior, opposite endpoint, event switch cannot be colored.
    base=dict(active_direction=1,event=1,value=0)
    assert color(base,base)=='blue'
    top=dict(active_direction=-1,event=2,value=100);assert color(top,top)=='red'
    for prev,cur in [(dict(base,value=30),base),(base,dict(base,value=20)),(base,dict(base,active_direction=0)),(base,dict(base,event=2)),(dict(top,value=40),dict(top,value=40)),(dict(base,value=100),dict(base,value=100))]:assert color(prev,cur)=='gray'
    out=R/'results/hist_line_v4_5_1';out.mkdir(exist_ok=True);checks=[]
    for tf in ['4h','1d']:
        rows=readlines(R/f'results/hist_line_v4_4/timeline_{tf}.jsonl.gz');trace=[]
        for mode in ['hold','structure']:
            previous=None;colored=0;formation_changes=0
            for row in rows:
                raw=row[mode+'_value'];active=bool(row['active_direction']);terminal=bool(row['success'] or row['failure'])
                smooth=mode=='structure' or not(active or terminal)
                y=tick(raw,previous['value'] if previous else None,enabled=smooth)
                cur=dict(row,value=y,mode=mode);cur['color']=color(previous,cur)
                assert math.isfinite(y) and 0<=y<=100
                if mode=='hold' and active:assert y==(0 if row['active_direction']==1 else 100)
                if smooth and previous:assert abs(y-previous['value'])<=15+1e-12
                if not active and not terminal:formation_changes+=int(y!=raw)
                if cur['color']!='gray':
                    colored+=1
                    assert previous['value']==y and active
                    assert (cur['color']=='blue' and y==0 and row['active_direction']==1) or (cur['color']=='red' and y==100 and row['active_direction']==-1)
                previous=cur;trace.append(cur)
            checks.append(dict(tf=tf,mode=mode,bars=len(rows),colored_horizontal_endpoint_segments=colored,colored_slopes=0,colored_interior_segments=0,colored_outside_active=0,smoothed_candidate_bars=formation_changes))
        jsonlines(out/f'timeline_{tf}.jsonl.gz',trace)
    result=dict(status='PASS',source_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),formal_core_and_audits_alerts_exact_v45=True,default_mode='hold',datasets=checks,limit='Offline display replay and source comparison. Entry into held endpoint is intentionally immediate and gray; not subject to smoothing cap.')
    save(out/'checks.json',result);print(json.dumps(result,indent=2))
if __name__=='__main__':main()
