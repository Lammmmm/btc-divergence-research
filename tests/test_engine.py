"""Independent synthetic fill, accounting, boundary and no-lookahead tests."""
import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import numpy as np
import pandas as pd
from research import run,exit_decision,HOUR,START

def fixture(direction=1):
    n=60;ht=START+np.arange(n)*HOUR
    h=pd.DataFrame(dict(time=ht,close_time=ht+HOUR-1,open=np.full(n,100.),high=np.full(n,101.),low=np.full(n,99.),close=np.full(n,100.)))
    df=h.iloc[::4].reset_index(drop=True).copy();df.close_time=df.time+4*HOUR-1
    sig=np.zeros((len(df),10,2),dtype=bool);sig[0,0,0 if direction==1 else 1]=True
    return dict(df=df,sig=sig,hour=h,ft=np.array([],dtype=np.int64),fc=np.array([0.]),tf='4h',
        time=df.time.to_numpy(),ct=df.close_time.to_numpy(),open=df.open.to_numpy(),close=df.close.to_numpy(),
        atr=np.full(len(df),2.),ema=np.full(len(df),100.),ho=h.open.to_numpy(),hh=h.high.to_numpy(),
        hl=h.low.to_numpy(),hc=h.close.to_numpy(),ht=h.time.to_numpy(),hct=h.close_time.to_numpy())

def execute(c,s=None):return run(c,0,s or {'id':'risk_base'},START,START+60*HOUR,'unit')
class EngineTests(unittest.TestCase):
    def test_stop_first_long_and_short(self):
        self.assertEqual(exit_decision(100,107,96,97,106,1),(97.,'stop',True,False))
        self.assertEqual(exit_decision(100,104,93,103,94,-1),(103.,'stop',True,False))
    def test_gap(self):
        self.assertEqual(exit_decision(90,95,85,97,106,1),(90.,'stop_gap',False,True))
        self.assertEqual(exit_decision(110,115,105,97,106,1),(106.,'target_gap',False,True))
    def test_long_stop_cash(self):
        c=fixture();c['hh'][4]=107;c['hl'][4]=96
        s,r,_,_=execute(c);x=r[0]
        entry=100*1.0002;qty=50/3;ex=(entry-3)*.9998
        expected=qty*(ex-entry)-.0005*qty*(entry+ex)
        self.assertAlmostEqual(x['pnl'],expected);self.assertTrue(x['ambiguous_hour'])
        self.assertAlmostEqual(x['initial_risk'],50)
        self.assertEqual(x['entry_time'],START+4*HOUR)
    def test_short_stop_cash(self):
        c=fixture(-1);c['hh'][4]=104;c['hl'][4]=93
        _,r,_,_=execute(c);entry=100*.9998;qty=50/3;ex=(entry+3)*1.0002
        self.assertAlmostEqual(r[0]['pnl'],qty*(entry-ex)-.0005*qty*(entry+ex))
    def test_funding_sign_boundary(self):
        for d in [1,-1]:
            c=fixture(d);c['ft']=np.array([START+4*HOUR,START+8*HOUR]);c['fc']=np.array([0.,.1,.3])
            _,r,_,_=execute(c)
            self.assertEqual(r[0]['funding_events'],1)
            self.assertAlmostEqual(r[0]['funding'],d*r[0]['quantity']*.2)
    def test_single_position_both_directions(self):
        c=fixture();c['sig'][1,0,1]=True;c['sig'][10,0,1]=True
        s,r,_,ledger=execute(c)
        self.assertEqual(len(r),1)
        self.assertEqual(ledger[1]['status'],'ignored_position_open')
        self.assertEqual(ledger[2]['status'],'purged_boundary')
    def test_fixed_timing_and_cap(self):
        c=fixture();s,r,_,_=execute(c,{'id':'fixed10_1x','fixed_hold':True})
        self.assertEqual(r[0]['exit_time_upper'],START+44*HOUR-1)
        self.assertAlmostEqual(r[0]['notional']*1.0005,10000)
        c['atr'][:]=.01
        _,r,_,_=execute(c)
        self.assertLessEqual(r[0]['notional']*1.0005,10000+1e-8)
    def test_future_changes_do_not_modify_trade(self):
        c=fixture();c['hl'][4]=96
        _,a,_,_=execute(c)
        c['hh'][8:]=1e7;c['hl'][8:]=1
        _,b,_,_=execute(c)
        self.assertEqual(a[0],b[0])
    def test_boundary_uses_maximum_horizon(self):
        c=fixture();c['hl'][4]=96
        s,r,_,ledger=run(c,0,{'id':'risk_base'},START,START+40*HOUR,'unit')
        self.assertEqual(r,[]);self.assertEqual(ledger[0]['status'],'purged_boundary')
    def test_bad_price_window_purged_before_outcome(self):
        c=fixture();c['hl'][4]=96;c['bad_execution_bars']=[START+20*HOUR]
        _,r,_,ledger=execute(c)
        self.assertEqual(r,[]);self.assertEqual(ledger[0]['status'],'purged_price_inconsistency')
    def test_short_target(self):
        c=fixture(-1);c['hl'][4]=93
        _,r,_,_=execute(c)
        self.assertEqual(r[0]['exit_reason'],'target');self.assertGreater(r[0]['pnl'],0)

if __name__=='__main__':unittest.main(verbosity=2)
