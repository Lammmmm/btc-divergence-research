import sys,unittest
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from structure_reversal import first_resolution,freeze_levels

class StructureTests(unittest.TestCase):
    def test_long_sideways_then_confirm(self):
        close=np.r_[np.full(200,100.),111.]
        self.assertEqual(first_resolution(close,0,len(close),1,110,90),(200,'success'))
    def test_failure_cannot_be_rescued_later(self):
        self.assertEqual(first_resolution([100,89,120],0,3,1,110,90),(1,'failure'))
    def test_pending_not_failure(self):
        self.assertEqual(first_resolution([100]*40,0,40,1,110,90),(39,'pending'))
    def test_short_and_strict_close(self):
        self.assertEqual(first_resolution([100,90,89],0,3,-1,90,110),(2,'success'))
        self.assertEqual(first_resolution([100,111,80],0,3,-1,90,110),(1,'failure'))
    def test_bad_data_is_unscored(self):
        self.assertEqual(first_resolution([100,120],0,2,1,110,90,[1]),(1,'data_interrupted'))
    def test_frozen_box_uses_no_future(self):
        high=np.array([101.,103,104,110,105,106,105,107,1000]);low=np.array([99.,97,96,95,94,93,92,91,1])
        a=freeze_levels(high,low,7,6,1,2)
        self.assertEqual(a['structure_high'],110);self.assertEqual(a['structure_low'],91)
        self.assertEqual(a['invalidation_level'],90)
        b=freeze_levels(high[:8],low[:8],7,6,1,2);self.assertEqual(a,b)

if __name__=='__main__':unittest.main(verbosity=2)
