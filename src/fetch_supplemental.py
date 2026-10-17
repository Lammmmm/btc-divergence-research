"""Public market data only. Frozen interval; never uses API keys or places orders."""
import json,time,hashlib,datetime
from pathlib import Path
import requests
ROOT=Path(__file__).resolve().parents[1]
RAW=ROOT/'data/raw'
START=1577836800000
END=1792108800000
def fetch(kind,interval):
    path='/fapi/v1/klines' if kind=='trade' else '/fapi/v1/markPriceKlines'
    dest=RAW/f'binance_BTCUSDT_{interval}_{kind}.json'
    if dest.exists():
        print('reuse',dest.name,flush=True);return
    rows=[];cursor=START
    while cursor<END:
        for attempt in range(5):
            try:
                r=requests.get('https://fapi.binance.com'+path,params=dict(symbol='BTCUSDT',interval=interval,startTime=cursor,endTime=END-1,limit=1500),timeout=30)
                r.raise_for_status();batch=r.json()
                if not isinstance(batch,list):raise ValueError(batch)
                break
            except Exception:
                if attempt==4:raise
                time.sleep(2+attempt)
        if not batch:break
        rows.extend(x for x in batch if x[6]<END)
        cursor=int(batch[-1][6])+1
        print(kind,interval,len(rows),flush=True)
        time.sleep(.15)
    dest.write_text(json.dumps(rows),encoding='utf-8')
    info={'url':'https://fapi.binance.com'+path,'symbol':'BTCUSDT','interval':interval,'startTime':START,'endTime':END-1,'retrieved_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'rows':len(rows),'sha256':hashlib.sha256(dest.read_bytes()).hexdigest()}
    dest.with_suffix('.provenance.json').write_text(json.dumps(info,indent=2))
if __name__=='__main__':
    fetch('trade','1h')
    fetch('mark','4h')
