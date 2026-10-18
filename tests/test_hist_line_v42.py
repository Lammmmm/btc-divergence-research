import sys, unittest, math
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from hist_line_v42 import formation,score,scale,Candidate,Display

def row(bs=60,ts=40,ref=1,broken=False,**kw):
    r=dict(time=1,bull=dict(ref=ref,score=bs,broken=broken),bear=dict(ref=2,score=ts,broken=False),active_direction=0,start=0,success=0,failure=0,invalid_touch=False,structure_progress=None)
    r.update(kw);return r

class ViewTests(unittest.TestCase):
    def test_continuous_threshold_and_monotonic(self):
        self.assertEqual(score(0),50)
        self.assertLess(score(.01),51)
        self.assertLess(abs(score(.00001)-score(-.00001)),.001)
        self.assertTrue(all(score(x)<score(x+.1) for x in [-5,-1,0,1,5]))
    def test_both_required_and_mirrored(self):
        v,p,h=formation(99,8,100,10,1,1,1)
        self.assertEqual(v,min(p,h));self.assertLess(v,50)
        self.assertEqual(formation(101,12,100,10,-1,1,1)[0],v)
    def test_scale_floor(self):
        self.assertEqual(scale(.01,8),4)
        self.assertEqual(scale(float('nan'),float('nan')),.1)
    def test_units_and_translation(self):
        x=formation(100.2,-1.9,100,-2,1,2,.5)
        y=formation(200.4+7,-3.8+3,200+7,-4+3,1,4,1)
        for a,b in zip(x,y):self.assertAlmostEqual(a,b)
    def test_direction_does_not_flip_on_one_bar(self):
        d=Display();self.assertEqual(d.step(row())['focus'],1)
        self.assertEqual(d.step(row(30,80))['focus'],1)
        self.assertEqual(d.step(row(30,80))['focus'],1)
        self.assertEqual(d.step(row(30,80))['focus'],-1)
    def test_red_not_delayed_or_smoothed(self):
        d=Display();d.step(row());r=d.step(row(60,40,broken=True))
        self.assertTrue(r['warning']);self.assertEqual(r['value'],60)
        r=d.step(row(active_direction=1,start=1,structure_progress=27,invalid_touch=True))
        self.assertTrue(r['warning']);self.assertEqual(r['value'],27)
    def test_context_seam_and_real_terminal(self):
        d=Display();d.step(row());self.assertTrue(d.step(row(ref=3))['seam'])
        self.assertTrue(d.step(row(active_direction=1,start=1,structure_progress=17))['seam'])
        r=d.step(row(success=1));self.assertFalse(r['seam']);self.assertEqual(r['value'],100)
        self.assertTrue(d.step(row())['seam'])
    def test_rollback(self):
        d=Display();d.step(row());before=d.__dict__.copy()
        d.step(row(20,90,broken=True),confirmed=False);self.assertEqual(d.__dict__,before)
    def test_candidate_keeps_coherent_pivot_and_freezes_scales(self):
        c=[100.]*20;h=[0.]*20;d=Candidate()
        r=d.step(c,h,10,[2],1,1,1)
        self.assertEqual(r['ref'],2)
        r=d.step(c,h,15,[8,2],1,100,100)
        self.assertEqual(r['ref'],2);self.assertEqual(r['atr'],1)
    def test_missing_candidate_is_not_fabricated_progress(self):
        d=Display();r=row(ref=-1);r['bear']['ref']=-1
        self.assertIsNone(d.step(r)['value'])
    def test_candidate_replaces_only_after_three_prior_broken_closes(self):
        c=[100.]*25;h=[0.]*25;c[9]=90
        d=Candidate()
        for k,t in enumerate([10,11,12]):
            r=d.step(c,h,t,[2],1,1,1)
            self.assertTrue(r['broken']);self.assertEqual(d.bad,k+1)
        r=d.step(c,h,18,[11,2],1,2,3)
        self.assertEqual(r['ref'],11);self.assertTrue(r['changed'])
        self.assertEqual(r['atr'],2);self.assertEqual(r['vol'],3)
    def test_candidate_intrabar_warning_without_committing(self):
        c=[100.]*20;h=[0.]*20;d=Candidate();d.step(c,h,10,[2],1,1,1)
        before=d.__dict__.copy();c[11]=90
        r=d.step(c,h,12,[2],1,1,1,confirmed=False)
        self.assertTrue(r['broken']);self.assertEqual(d.__dict__,before)
    def test_old_failure_new_event_same_bar(self):
        d=Display();d.step(row(active_direction=1,start=1,structure_progress=12))
        r=d.step(row(active_direction=-1,start=-1,failure=1,invalid_touch=True,structure_progress=55))
        self.assertEqual(r['value'],55);self.assertTrue(r['warning']);self.assertTrue(r['seam'])

if __name__=='__main__':unittest.main()
