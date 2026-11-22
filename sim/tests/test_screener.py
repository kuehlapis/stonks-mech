import os
import sys
import unittest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import screener
from batchlock import BatchLock, LOCK


class ScreenerTests(unittest.TestCase):
    def setUp(self):
        if os.path.isdir(LOCK):
            import shutil
            shutil.rmtree(LOCK, ignore_errors=True)

    def tearDown(self):
        if os.path.isdir(LOCK):
            import shutil
            shutil.rmtree(LOCK, ignore_errors=True)

    def test_existing_variant_is_valid(self):
        self.assertTrue(os.path.isfile(screener.validate_candidate("c_aim")))

    def test_cover_candidate_requires_specs(self):
        with self.assertRaises(ValueError):
            screener.validate_candidate("cover_test")

    def test_seed_and_pair_delta_limits(self):
        rows = [
            {"seed": 1100000, "score_delta": 1.0, "kill_delta": 0.5},
            {"seed": 1100001, "score_delta": -1.0, "kill_delta": -0.5},
        ]
        d = screener.paired_delta(rows, "score_delta")
        self.assertEqual(d["mean"], 0.0)
        self.assertEqual(d["se"], 1.0)

    def test_pair_metrics_uses_inproc_slot_damage_attribution(self):
        def row(slot, label, place=16, kills=0, cause="gun", killed_by=None, dmg_by_slot=None):
            return {
                "slot": slot,
                "label": label,
                "place": place,
                "kills": kills,
                "cause": cause,
                "death_t": 100.0,
                "killed_by": killed_by,
                "dmg_taken": 100.0,
                "dmg_rear": 0.0,
                "ticks_alive": 100,
                "ticks_out": 0,
                "cubes": 0,
                "errors": 0,
                "late": 0,
                "ms_mean": 1.0,
                "ms_p99": 1.0,
                "ms_max": 1.0,
                "dmg_by_slot": dmg_by_slot or {},
            }

        candidate = {
            "seed": 1100000,
            "rows": [
                row(2, "cand", place=5, kills=1),
                row(3, "squad", cause="laser", killed_by="squad", dmg_by_slot={"2": 25.0}),
                row(4, "squad", cause="gun", killed_by="cand"),
            ],
        }
        baseline = {
            "seed": 1100000,
            "rows": [
                row(2, "s_base2", place=6, kills=0),
                row(3, "squad", cause="laser", killed_by="squad", dmg_by_slot={}),
            ],
        }

        metrics = screener.pair_metrics([candidate], [baseline], "cand")

        self.assertEqual(metrics["direct_squad_deaths"], {"gun": 1})
        self.assertEqual(metrics["assisted_squad_deaths"], {"laser": 1})

    def test_batch_lock_excludes_second_owner(self):
        first = BatchLock("first", timeout=1)
        first.acquire()
        second = BatchLock("second", timeout=0.05)
        with self.assertRaises(TimeoutError):
            second.acquire()
        first.release()


if __name__ == "__main__":
    unittest.main()
