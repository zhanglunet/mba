import sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts/watch-tools'))
import reaudit_trigger as mod

class TriggerTest(unittest.TestCase):
    def test_prior_events_do_not_retrigger(self):
        events=[{'id':'old','date':'2026-11-14','severity':'P0'}, {'id':'new','date':'2026-11-15','severity':'P1'}]
        self.assertFalse(mod.evaluate_new(events,'2026-11-14','2026-11-16')['hit'])
    def test_three_fresh_p1_trigger(self):
        events=[{'id':str(i),'date':'2026-11-15','severity':'P1'} for i in range(3)]
        self.assertTrue(mod.evaluate_new(events,'2026-11-14','2026-11-16')['hit'])
