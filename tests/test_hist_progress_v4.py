import copy,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from hist_progress_v4 import formation,structure,touched,Candidate,clear_line
from verify_hist_lifecycle import Lifecycle

class ProgressTests(unittest.TestCase):
    def test_bull_approach_both_required(self):
        self.assertEqual(formation(101,-2,100,-1,1,2,2),(50,50,50))
        self.assertEqual(formation(99,-4,100,-1,1,2,2)[0],0)
        self.assertEqual(formation(103,0,100,-1,1,2,2)[0],0)
        self.assertEqual(formation(99,0,100,-1,1,2,2)[0],99)
    def test_bear_mirror(self):
        self.assertEqual(formation(99,2,100,1,-1,2,2),(50,50,50))
        self.assertEqual(formation(101,0,100,1,-1,2,2)[0],99)
    def test_equality_cannot_confirm(self):
        self.assertEqual(formation(100,1,100,1,1,2,2)[0],99)
    def test_units_and_translation_invariance(self):
        a=formation(101,-2,100,-1,1,2,2)
        self.assertEqual(a,formation(1010,-20,1000,-10,1,20,20))
        self.assertEqual(a,formation(1101,98,1100,99,1,2,2))
    def test_reversible(self):
        xs=[formation(p,h,100,-1,1,2,2)[0] for p,h in [(101,-2),(100,-1),(102,-3)]]
        self.assertEqual(xs,[50,99,0])
    def test_structure_both_directions(self):
        for price,expected in [(90,0),(95,25),(100,50),(110,100),(120,100)]:self.assertEqual(structure(price,90,110),expected)
        for price,expected in [(110,0),(105,25),(100,50),(90,100),(80,100)]:self.assertEqual(structure(price,110,90),expected)
    def test_touch_equality_and_recovery_not_failure(self):
        self.assertTrue(touched(1,89,105,89));self.assertTrue(touched(-1,95,111,111))
        s=Lifecycle();s.step(0,100,102,98,[True,False],110,90,2)
        s.step(1,100,105,88,[False,False]);self.assertIsNotNone(s.active)
        self.assertEqual(structure(100,89,110),100*11/21)
    def test_intrabar_cannot_commit_candidate_state(self):
        a=Candidate();before=copy.deepcopy(a);c=[100]*8;h=[1]*8
        a.step(c,h,7,[0],1,2,2,confirmed=False);self.assertEqual(a,before)
    def test_reference_reset_and_scales_frozen(self):
        a=Candidate();c=[100]*15;h=[1]*15
        r=a.step(c,h,7,[0],1,2,3);self.assertTrue(r['changed'])
        r=a.step(c,h,8,[0],1,20,30);self.assertFalse(r['changed']);self.assertEqual((r['atr'],r['vol']),(2,3))
        r=a.step(c,h,14,[7,0],1,4,5);self.assertTrue(r['changed']);self.assertEqual((r['ref'],r['atr'],r['vol']),(7,4,5))
    def test_newest_eligible_not_best_score(self):
        a=Candidate();c=[100]*20;h=[1]*20
        r=a.step(c,h,19,[18,12,0],1,2,2);self.assertEqual(r['ref'],12)
    def test_expiry_and_episode_end(self):
        a=Candidate();c=[100]*102;h=[1]*102
        a.step(c,h,100,[0],1,2,2)
        r=a.step(c,h,101,[0],1,2,2);self.assertTrue(r['lost']);self.assertIsNone(r['score'])
    def test_line_obstruction_is_red_without_fake_confirmation(self):
        a=Candidate();c=[100,101,101,90,101,101,101,99];h=[0,1,1,-5,1,1,1,2]
        r=a.step(c,h,7,[0],1,2,2)
        self.assertEqual(r['score'],99);self.assertTrue(r['broken']);self.assertFalse(r['clear'])
    def test_previously_satisfied_price_is_revoked(self):
        a=Candidate();c=[100]+[102]*6+[99,101];h=[0]+[3]*6+[2,3]
        self.assertFalse(a.step(c,h,7,[0],1,2,2)['broken'])
        self.assertTrue(a.step(c,h,8,[0],1,2,2)['broken'])
    def test_no_touch_before_activation_and_same_bar_restart(self):
        s=Lifecycle();self.assertIsNone(s.active)
        s.step(0,100,120,70,[True,False],120,70,2)
        # A newly activated structure did not exist during its start bar's earlier wick.
        self.assertEqual(s.active['t'],0)
        p=s.step(1,121,125,60,[False,True],125,60,2)
        self.assertEqual((p['success'],p['start']),(1,-1))

if __name__=='__main__':unittest.main(verbosity=2)
