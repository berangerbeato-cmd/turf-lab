"""Turf Lab V4 unified research output and fail-closed provenance tests."""
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from turf_lab.v4_unified import assemble, prepare_features

ROOT = Path("predictions_operational/2026-11-21/2026-11-21_R4C5_20261121T172911422587Z")
REPAIR = Path("reports/history_repair_shadow_v1/replays_nancy_alias_v1_1/2026-11-21_R4C5_20261121T172911422587Z.json")
PAIR = Path("reports/value_history_pair_v1/reims_r4c5_retrospective.json")


class UnifiedV4Tests(unittest.TestCase):
    def test_reims_single_result_and_locked_sources(self):
        r = assemble(ROOT/"prediction.json",REPAIR,PAIR,ROOT/"quotes.json",
                     now=datetime(2026,11,21,19,0,tzinfo=timezone.utc))
        self.assertEqual(r["version"],"turf_lab_v4_research_1")
        self.assertEqual(r["freshness"],"RETROSPECTIVE")
        self.assertEqual(r["decision"],"NO BET")
        self.assertFalse(r["recommendations_allowed"])
        self.assertEqual(len(r["top5"]["numbers"]),5)
        self.assertEqual(len(set(r["top5"]["numbers"])),5)
        self.assertEqual(r["value"]["paper_candidates_not_bets"],[])
        self.assertEqual(r["value"]["status"],"RETROSPECTIVE_PAIRED_REPLAY")
        self.assertGreater(len(r["history_repair"]["unresolved"]),0)

    def test_no_cotes_no_fabricated_ev(self):
        r=assemble(ROOT/"prediction.json",REPAIR,
                   now=datetime(2026,11,21,19,0,tzinfo=timezone.utc))
        self.assertEqual(r["value"]["status"],"NO_VERIFIED_COTES")
        self.assertEqual(r["value"]["paper_candidates_not_bets"],[])
        self.assertEqual(r["gagnant"]["basis"],"REPAIRED_SPORT_UNCALIBRATED")
        self.assertEqual(r["decision"],"NO BET")

    def test_history_repair_is_mandatory(self):
        with self.assertRaises(FileNotFoundError):
            assemble(ROOT/"prediction.json",Path("/tmp/turf_v4_nonexistent_history.json"))
        original=json.loads(REPAIR.read_text())
        original["candidate"]="old_history_version"
        with tempfile.TemporaryDirectory() as tmp:
            file=Path(tmp)/"wrong_repair.json"
            file.write_text(json.dumps(original))
            with self.assertRaisesRegex(ValueError,"History Repair"):
                assemble(ROOT/"prediction.json",file)

    def test_late_repair_rejected(self):
        original=json.loads(REPAIR.read_text())
        original["status"]="PRESTART_HISTORY_REPAIR_SHADOW"
        original["shadow_calculated_at"]="2026-11-21T18:00:00+00:00"
        with tempfile.TemporaryDirectory() as tmp:
            file=Path(tmp)/"late_repair.json"
            file.write_text(json.dumps(original))
            with self.assertRaisesRegex(ValueError,"Late history"):
                assemble(ROOT/"prediction.json",file)

    def test_corrected_features_match_original_snapshot_before_patch(self):
        original=json.loads((ROOT/"prediction.json").read_text())
        repair=json.loads(REPAIR.read_text())
        rows,problems=prepare_features(original,repair)
        self.assertEqual(len(rows),14)
        self.assertGreater(len(problems),0)
        item=next(a for a in repair["runner_audit"] if a["status"]=="UPDATED")
        row=next(r for r in rows if r["number"]==item["number"])
        self.assertEqual(row["features"][:5],item["candidate_recent5"])
        original["models"]["available_history_v3"]["runners"][item["number"]-1]["features"][0]=999
        with self.assertRaisesRegex(ValueError,"Repair changes frozen"):
            prepare_features(original,repair)

    def test_pair_requires_original_quote_snapshot(self):
        with self.assertRaisesRegex(ValueError,"Missing odds"):
            assemble(ROOT/"prediction.json",REPAIR,PAIR)


if __name__=="__main__":
    unittest.main()
