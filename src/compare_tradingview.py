"""Compare user-exported TradingView CSV with frozen Python bar signals.
Usage: python src/compare_tradingview.py --timeframe 4h --csv exported.csv
No export is supplied in the repository; this check is currently PENDING.
"""
import argparse,csv,gzip,json
from pathlib import Path
import pandas as pd
R=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser();p.add_argument('--timeframe',choices=['4h','1d'],required=True);p.add_argument('--csv',type=Path,required=True);args=p.parse_args()
    with gzip.open(R/f'data/derived/indicators_signals_{args.timeframe}.jsonl.gz','rt') as f:ref={r['time']:r for r in map(json.loads,f)}
    with args.csv.open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
    assert rows,'Empty CSV'
    cols=list(rows[0]);tc=next((c for c in cols if c.lower() in ['time','timestamp','date']),None)
    assert tc,'CSV needs UTC time column'
    names=['MACD','Hist','RSI','Stoch','CCI','MOM','OBV','VWMACD','CMF','MFI']
    keys=[f'{n}_{side}' for n in names for side in ['bull','bear']]
    mapping={k:[c for c in cols if c==k or c.endswith(': '+k) or c.endswith(' '+k)] for k in keys}
    assert all(len(v)==1 for v in mapping.values()),mapping
    compared=0;diff=[];missing=0
    for row in rows:
        v=row[tc]
        try:
            num=float(v);t=int(num*(1000 if abs(num)<1e11 else 1))
        except ValueError:
            ts=pd.Timestamp(v)
            assert ts.tzinfo is not None,'ISO times must include timezone; do not silently assume local time'
            t=int(ts.value//10**6)
        if t not in ref:missing+=1;continue
        compared+=1
        for k in keys:
            got=float(row[mapping[k][0]])
            if got!=ref[t][k]:diff.append(dict(time=t,column=k,tradingview=got,python=ref[t][k]))
    assert compared>0,'No common timestamps'
    result={'status':'MATCH_ON_SUPPLIED_ROWS' if not diff else 'MISMATCH','timeframe':args.timeframe,'compared_bars':compared,'unmatched_times':missing,'differences':diff,'note':'Signal match only; price history, warmup, export coverage and strategy fills need separate review.'}
    (R/f'results/tradingview_comparison_{args.timeframe}.json').write_text(json.dumps(result,indent=2))
    print(result['status'],compared,'bars',len(diff),'differences')
if __name__=='__main__':main()
