"""Retain fresh exchange responses for anomalous native/hourly comparisons."""
import json,datetime
from pathlib import Path
import requests
R=Path(__file__).resolve().parents[1]
records=[]
for t in [1657944000000,1699617600000,1730145600000]:
    for tf in ['4h','1h','1d']:
        a=(t//86400000)*86400000 if tf=='1d' else t
        end=a+(86400000 if tf=='1d' else 14400000)-1
        params=dict(symbol='BTCUSDT',interval=tf,startTime=a,endTime=end,limit=10)
        x=requests.get('https://fapi.binance.com/fapi/v1/klines',params=params,timeout=30)
        x.raise_for_status()
        records.append({'params':params,'rows':x.json(),'retrieved_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()})
(R/'data/raw/discrepancy_requeries.json').write_text(json.dumps(records,indent=2))
print('Saved',len(records),'API responses')
