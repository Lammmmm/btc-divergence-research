import json
from pathlib import Path
import numpy as np
import pandas as pd
from backtest_divergence import run_events,FEE,SLIP

root=Path(__file__).resolve().parent
t=pd.DataFrame(json.loads((root/'trades.json').read_text()))
for tf,step in [('4h',14400000),('1d',86400000)]:
    rows=t[t.tf==tf]
    assert ((rows.entry_time-rows.signal_time)==step).all()
    assert ((rows.exit_time-rows.entry_time)==rows.h*step-1).all()
for _,g in t.groupby(['tf','name','side','h']):
    g=g.sort_values('entry_time')
    assert (g.entry_time.to_numpy()[1:]>g.exit_time.to_numpy()[:-1]).all()
assert (t[t.split=='development'].exit_time<1735689600000).all()
assert (t[t.split=='validation'].entry_time>=1735689600000).all()

base=1609459200000
df=pd.DataFrame({'time':base+np.arange(8)*14400000,'close_time':base+(np.arange(8)+1)*14400000-1,'open':np.full(8,100.),'close':np.arange(8)+100.})
mask=np.ones(8,dtype=bool)
for side,direction in [(0,1),(1,-1)]:
    events=run_events(df,mask,2,np.array([],dtype=np.int64),np.array([0.]),'unit','4h',side)
    first=events[0]
    assert first['entry_time']==base+14400000
    assert first['exit_time']==base+3*14400000-1
    assert abs(first['gross']-direction*.02)<1e-10
    e=100*(1+direction*SLIP); x=102*(1-direction*SLIP)
    expected=direction*(x/e-1)-FEE*(1+x/e)
    assert abs(first['net']-expected)<1e-10
checks=json.loads((root/'checks.json').read_text())
checks.update({'next_open_entry_verified':True,'holding_period_off_by_one_verified':True,'directional_nonoverlap_verified':True,'no_split_boundary_leakage':True,'synthetic_cost_sign_checks':True,'trade_records_all_scenarios':len(t)})
(root/'checks.json').write_text(json.dumps(checks,indent=2))
print(json.dumps(checks,indent=2))
