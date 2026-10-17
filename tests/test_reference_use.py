import sys,unittest
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from reference_use import daily_context,barrier_path,adx14,HOUR

class ReferenceTests(unittest.TestCase):
    def test_daily_unclosed_cannot_leak(self):
        confirmed=np.array([24,48,72])*HOUR
        signal=np.array([[True,False],[False,True],[True,True]])
        query=np.array([23,24,47,48,71,72,400])*HOUR
        state,t,_=daily_context(query,confirmed,signal)
        np.testing.assert_array_equal(state,[0,1,1,-1,-1,0,0]);self.assertTrue((t<=query).all())
    def test_expiry(self):
        d,_,_=daily_context(np.array([24,264,265])*HOUR,np.array([24])*HOUR,np.array([[True,False]]))
        np.testing.assert_array_equal(d,[1,1,0])
    def test_barrier_long_short_and_tie(self):
        self.assertEqual(barrier_path([100],[102],[99.5],100,1,1),('favorable_first',1))
        self.assertEqual(barrier_path([100],[100.5],[98],100,1,-1),('favorable_first',1))
        self.assertEqual(barrier_path([100],[102],[98],100,1,1),('ambiguous_adverse_first',1))
        self.assertEqual(barrier_path([100],[100.5],[99.5],100,1,1),('neither',None))
    def test_trend_adx_and_prefix(self):
        c=np.arange(100.,200.)
        df=pd.DataFrame(dict(close=c,high=c+1,low=c-1))
        a,_,_=adx14(df);b,_,_=adx14(df.iloc[:60])
        self.assertAlmostEqual(a[-1],100)
        np.testing.assert_allclose(a[:60],b,equal_nan=True)

if __name__=='__main__':unittest.main(verbosity=2)
