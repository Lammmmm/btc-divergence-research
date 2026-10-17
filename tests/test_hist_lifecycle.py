import copy,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from verify_hist_lifecycle import Lifecycle,progress

class HistLifecycleTests(unittest.TestCase):
    def start(self,d=1):
        s=Lifecycle();s.step(0,100,102,98,[d==1,d==-1],110,90,2);return s
    def test_intrabar_cannot_resolve_or_mutate(self):
        s=self.start();before=copy.deepcopy(s)
        self.assertEqual(s.step(1,120,125,70,[False,True],125,70,3,False),dict(start=0,success=0,failure=0))
        self.assertEqual(s,before)
    def test_wick_crossings_and_equality_do_not_resolve(self):
        s=self.start();s.step(1,100,130,60,[False,False]);self.assertIsNotNone(s.active)
        s.step(2,110,115,95,[False,False]);self.assertIsNotNone(s.active)
        s.step(3,89,95,85,[False,False]);self.assertIsNotNone(s.active)
    def test_new_signal_does_not_move_frozen_box(self):
        s=self.start();s.step(1,100,105,95,[False,True],120,80,9)
        self.assertEqual((s.active['target'],s.active['invalid'],s.active['ignored']),(110,89,1))
    def test_same_close_can_finish_then_start(self):
        s=self.start();p=s.step(1,111,112,100,[False,True],115,95,2)
        self.assertEqual(p,dict(start=-1,success=1,failure=0));self.assertEqual(s.active['t'],1)
    def test_failure_not_rescued_by_later_price(self):
        s=self.start();s.step(1,88,100,85,[False,False]);s.step(2,130,140,120,[False,False])
        self.assertEqual([r['status'] for r in s.completed],['failure'])
    def test_short_direction_and_conflicts(self):
        s=self.start(-1);s.step(1,89,100,85,[True,True],120,80,2)
        self.assertIsNone(s.active);self.assertEqual(s.completed[0]['status'],'success')
    def test_long_wait_no_expiry(self):
        s=self.start()
        for i in range(1,401):s.step(i,100,105,95,[False,False])
        self.assertIsNotNone(s.active)
        s.step(401,111,112,100,[False,False]);self.assertEqual(s.completed[0]['resolution'],401)
    def test_progress_has_direction_and_can_reverse(self):
        self.assertEqual(progress(105,1,100,110,90),50)
        self.assertEqual(progress(95,1,100,110,90),-50)
        self.assertEqual(progress(95,-1,100,90,110),50)
        self.assertEqual(progress(105,-1,100,90,110),-50)
        self.assertEqual(progress(150,1,100,110,90),100)

if __name__=='__main__':unittest.main(verbosity=2)
