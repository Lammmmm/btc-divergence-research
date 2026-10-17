import sys,unittest,random
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from hist_state_v3 import coordinates,neutral_score
from verify_hist_lifecycle import Lifecycle

class StateCoordinatesTests(unittest.TestCase):
    def test_constant_and_missing_history(self):
        for xs in [[],[None],[float('nan')],[7]*100]:self.assertEqual(neutral_score(xs),50)
    def test_hist_extremes_cannot_claim_divergence(self):
        self.assertEqual(coordinates([0,100000]),(90,'gray'))
        self.assertEqual(coordinates([0,-100000]),(10,'gray'))
    def test_preview_never_hits_endpoint_or_colors(self):
        self.assertEqual(coordinates([0,1],0,1),(5,'gray'))
        self.assertEqual(coordinates([0,1],0,-1),(95,'gray'))
        self.assertEqual(coordinates([0,1],0,0),(90,'gray'))
    def test_active_state_overrides_hist_and_preview(self):
        for xs in [[0,1],[0,-1],[None],[]]:
            self.assertEqual(coordinates(xs,1,-1),(0,'yellow'))
            self.assertEqual(coordinates(xs,-1,1),(100,'blue'))
    def test_bounded_random_inputs(self):
        rng=random.Random(42)
        for _ in range(1000):
            xs=[rng.uniform(-1e8,1e8) for _ in range(100)]
            for d in [-1,0,1]:
                v,c=coordinates(xs,d)
                self.assertTrue(0<=v<=100)
                self.assertEqual(v in [0,100],d!=0)
    def test_prefix_causality(self):
        xs=[1,-2,5,0,9,-10,3]*30
        calc=lambda a:[coordinates(a[max(0,i-99):i+1]) for i in range(len(a))]
        self.assertEqual(calc(xs),calc(xs+[1e12,-1e12]*50)[:len(xs)])
    def test_intrabar_and_end_transitions(self):
        s=Lifecycle()
        s.step(0,100,102,98,[True,False],110,90,2,False)
        self.assertIsNone(s.active)
        s.step(0,100,102,98,[True,False],110,90,2)
        self.assertEqual(coordinates([1,2],s.active['direction']),(0,'yellow'))
        s.step(1,120,125,70,[False,False],confirmed=False)
        self.assertEqual(coordinates([1,2],s.active['direction']),(0,'yellow'))
        s.step(1,111,115,100,[False,False])
        self.assertIsNone(s.active)
        self.assertEqual(coordinates([1,2]),(90,'gray'))
    def test_failure_and_same_bar_restart(self):
        s=Lifecycle();s.step(0,100,102,98,[False,True],110,90,2)
        s.step(1,112,115,100,[False,False])
        self.assertIsNone(s.active);self.assertEqual(coordinates([1,2])[1],'gray')
        s.step(2,100,102,98,[True,False],110,90,2)
        p=s.step(3,111,115,100,[False,True],115,95,2)
        self.assertEqual((p['success'],p['start']),(1,-1))
        self.assertEqual(coordinates([1,2],s.active['direction']),(100,'blue'))

if __name__=='__main__':unittest.main(verbosity=2)
