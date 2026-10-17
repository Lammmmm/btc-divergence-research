import concurrent.futures as cf
import datetime as dt
import json
from pathlib import Path
import time
import requests

ROOT = Path(__file__).resolve().parent
BASE = 'https://fapi.binance.com'
def ms(s):
    return int(dt.datetime.fromisoformat(s).replace(tzinfo=dt.timezone.utc).timestamp()*1000)
def get(path, params=None):
    for attempt in range(5):
        try:
            r = requests.get(BASE+path, params=params, timeout=30)
            r.raise_for_status()
            result=r.json()
            if isinstance(result,dict) and 'code' in result:
                raise RuntimeError(result)
            return result
        except Exception:
            if attempt == 4: raise
            time.sleep(2+attempt*2)

def fetch_klines(interval, end):
    cache=ROOT/f'binance_BTCUSDT_{interval}.json'
    if cache.exists(): return json.loads(cache.read_text())
    cursor=ms('2020-01-01')
    rows=[]
    while cursor<end:
        batch=get('/fapi/v1/klines',dict(symbol='BTCUSDT', interval=interval, startTime=cursor, endTime=end-1, limit=1500))
        if not batch: break
        rows.extend(row for row in batch if row[6]<end)
        cursor=batch[-1][6]+1
        print(interval, len(rows), dt.datetime.fromtimestamp(cursor/1000,dt.timezone.utc).isoformat(),flush=True)
        time.sleep(.12)
    cache.write_text(json.dumps(rows))
    return rows

def fetch_funding(end):
    cache=ROOT/'binance_BTCUSDT_funding.json'
    if cache.exists(): return json.loads(cache.read_text())
    cursor=ms('2021-01-01'); rows=[]
    while cursor<end:
        batch=get('/fapi/v1/fundingRate',dict(symbol='BTCUSDT',startTime=cursor,endTime=end-1,limit=1000))
        if not batch: break
        rows.extend(batch); cursor=batch[-1]['fundingTime']+1
        print('funding',len(rows),flush=True)
        time.sleep(.25)
    cache.write_text(json.dumps(rows))
    return rows

if __name__=='__main__':
    server=get('/fapi/v1/time')['serverTime']
    end=min(ms('2026-10-16'),server)
    with cf.ThreadPoolExecutor(max_workers=3) as pool:
        jobs=[pool.submit(fetch_klines,i,end) for i in ['4h','1d']]
        jobs.append(pool.submit(fetch_funding,end))
        results=[j.result() for j in jobs]
    manifest={'exchange':'Binance USD-M BTCUSDT perpetual','server_time_ms':server,'exclusive_end_ms':end,'start':'2020-01-01','analysis_start':'2021-01-01','validation_start':'2025-01-01','counts':dict(zip(['4h','1d','funding'],map(len,results))),'urls':['https://fapi.binance.com/fapi/v1/klines','https://fapi.binance.com/fapi/v1/fundingRate']}
    (ROOT/'data_manifest.json').write_text(json.dumps(manifest,indent=2))
    print(json.dumps(manifest,indent=2))
