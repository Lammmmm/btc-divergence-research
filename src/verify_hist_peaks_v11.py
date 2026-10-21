"""Source-equivalence check for display-only v1.1; not a Pine interpreter."""
import hashlib, json
from pathlib import Path
r=Path(__file__).resolve().parents[1]
a=(r/'pine/Hist_Divergence_Peaks_v1.pine').read_text(encoding='utf-8')
p=r/'pine/Hist_Divergence_Peaks_v1_1.pine'
b=p.read_text(encoding='utf-8')
for start,end in [('[macdValue, signalValue, hist] =','            color c = bull ? bullColor : bearColor'),('// Non-backdated data-window series',None)]:
    assert a[a.index(start):a.index(end) if end else None] == b[b.index(start):b.index(end) if end else None], start
out=r/'results/hist_peaks_v1_1/checks.json'
report=json.loads(out.read_text(encoding='utf-8'))
report['source_sha256']=hashlib.sha256(p.read_bytes()).hexdigest()
report['status']='PASS'
out.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('PASS: exact signal, deduplication, audit and alert blocks; original Hist unchanged')
