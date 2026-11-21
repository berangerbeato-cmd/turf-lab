"""Forward scoring must not import Reims retrospective forecasts into V4 results."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.score_v4_prospective import metrics, run


class ForwardV4Tests(unittest.TestCase):
    def test_one_race_paired_winner_and_top5(self):
        probs={1:.45,2:.2,3:.15,4:.1,5:.06,6:.04}
        outcome=[2,1,4,6,3]
        m=metrics(probs,[1,2,3,4,5],outcome)
        self.assertAlmostEqual(m["log_loss"],1.6094379124341)
        self.assertEqual(m["top1_correct"],0)
        self.assertEqual(m["top5_overlap"],4)
        self.assertEqual(m["top5_exact"],0)

    def test_no_new_forecast_means_zero_results_no_retrospective_backfill(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            with patch("scripts.score_v4_prospective.ROOT",root):
                with patch("scripts.score_v4_prospective.History"):
                    report=run(root/"scores.json")
            self.assertEqual(report["prospective_captures"],0)
            self.assertEqual(report["verified_results"],0)
            self.assertEqual(report["means"],{})
            self.assertFalse(report["validation_ready"])
            self.assertIsNone(report["roi"])


if __name__=="__main__":
    unittest.main()
