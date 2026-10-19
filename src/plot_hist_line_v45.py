"""Visual comparison on the same frozen records; no new trading experiment."""
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from datetime import datetime,timezone
from reference_use import readlines
R=Path(__file__).resolve().parents[1]
fig,axes=plt.subplots(2,1,figsize=(14,7),constrained_layout=True)
for ax,tf,count in zip(axes,['4h','1d'],[300,180]):
    rows=readlines(R/f'results/hist_line_v4_5/timeline_{tf}.jsonl.gz')[-count:]
    raw=[x['structure_value'] for x in rows];sm=[x['smoothed_value'] for x in rows]
    ax.plot(raw,color='#c3c8d0',linewidth=.8,label='v4.4 raw position')
    segments=[[(i-1,sm[i-1]),(i,sm[i])] for i in range(1,len(sm))]
    colors=[{'gray':'#697586','blue':'#1744d1','red':'#d50032'}[x['smoothed_color']] for x in rows[1:]]
    ax.add_collection(LineCollection(segments,colors=colors,linewidths=1.3))
    ax.plot([],[],color='#1744d1',label='v4.5 display (EMA length 3, max step 15)')
    ticks=list(range(0,len(rows),max(1,len(rows)//6)))
    ax.set_xticks(ticks,[datetime.fromtimestamp(rows[i]['time']/1000,timezone.utc).strftime('%Y-%m-%d') for i in ticks],fontsize=8)
    ax.set_ylim(-3,103);ax.set_ylabel('Display points, not probability');ax.set_title(f'BTCUSDT perpetual {tf.upper()} | same inputs and event rules',loc='left')
    ax.grid(alpha=.15);ax.legend(loc='upper left',fontsize=8)
fig.savefig(R/'reports/hist_line_v4_5_comparison.png',dpi=150)
print('Saved smoothing comparison.')
