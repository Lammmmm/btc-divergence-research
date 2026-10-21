"""Display-only equivalence against frozen Peaks v1.1; not a Pine interpreter."""
from pathlib import Path
import hashlib,json
r=Path(__file__).resolve().parents[1]
a=(r/'pine/Hist_Divergence_Peaks_v1_1.pine').read_text(encoding='utf-8')
p=r/'pine/Hist_Divergence_Peaks_v1_2.pine'
b=p.read_text(encoding='utf-8')
for start,end in [('[macdValue, signalValue, hist] =','            color c = bull ? bullColor : bearColor'),('// Non-backdated data-window series',None)]:
    assert a[a.index(start):a.index(end) if end else None] == b[b.index(start):b.index(end) if end else None],start
result=dict(status='PASS',source_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),compared_to='Hist_Divergence_Peaks_v1_1.pine',scope='Exact MACD, confirmed pivot search, trigger, deduplication, A/B values, audit and alert blocks; display-only change.',prior_replay='results/hist_peaks_v1/checks.json',changes=['Top red / bottom blue named confirmation badges at actual confirmation bar','Width 6 actual-value trigger Histogram and circle','Only last one A/B pair by default','A/B roles named and sequence IDs hidden by default','Ordinary-column transparency 55'])
(r/'results/hist_peaks_v1_2/checks.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print('PASS: exact signal and alert source; original Hist values retained')
