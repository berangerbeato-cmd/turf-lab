"""Full V4 training history reconciliation regression safeguards."""
import copy
import unittest

from turf_lab.v4_retrain_data import reconcile


class V4HistoryTrainingTests(unittest.TestCase):
    @staticmethod
    def pair(old,new,rid="2024-04-03_R1C1"):
        base={"race_id":rid,"date":rid[:10],"runners":[{"number":1,"horse_id":"H1","won":1,
               "non_runner":False,"features":list(old)+[0]*33}]}
        repair=copy.deepcopy(base)
        repair["runners"][0]["features"][:5]=new
        archive={"race_id":rid,"date":rid[:10],"runners":[{"number":1,
                 "horse_id":"H1","won":1,"non_runner":False,
                 "available_recent":list(old)}]}
        cohort={"original":{rid:base},"enriched":{rid:repair}}
        audit={rid:{"added_starts":1}}
        return archive,cohort,audit

    def test_repaired_recent_five_is_the_only_change(self):
        a,b,meta=self.pair([0,.2,.2,2,1],[.2,.4,.2,1.8,1])
        original=copy.deepcopy(a)
        rows,stats,changes=reconcile([a],b,meta)
        self.assertEqual(stats["runners_repaired"],1)
        self.assertEqual(rows[0]["runners"][0]["available_recent"],[.2,.4,.2,1.8,1])
        self.assertEqual(a,original)
        self.assertEqual(len(changes),1)

    def test_incomplete_archive_not_falsely_asserted_as_repaired(self):
        a,b,meta=self.pair([0,.2,.2,2,1],[.2,.4,.2,1.8,1])
        a["runners"][0]["available_recent"]=[0,0,0,3,1]
        rows,stats,changes=reconcile([a],b,meta)
        self.assertEqual(stats["runners_cohort_baseline_mismatch_abstained"],1)
        self.assertEqual(stats["runners_repaired"],0)
        self.assertEqual(changes,[])

    def test_unknown_races_remain_archive_only(self):
        a,b,meta=self.pair([0,.2,.2,2,1],[.2,.4,.2,1.8,1])
        rows,stats,changes=reconcile([a],{"original":{},"enriched":{}},{})
        self.assertEqual(stats["races_archive_only"],1)
        self.assertEqual(stats["runners_repaired"],0)

    def test_target_or_horse_identity_mismatch_fails_closed(self):
        a,b,meta=self.pair([0,.2,.2,2,1],[.2,.4,.2,1.8,1])
        b["enriched"][a["race_id"]]["runners"][0]["horse_id"]="WRONG"
        with self.assertRaisesRegex(ValueError,"identity"):
            reconcile([a],b,meta)
        a,b,meta=self.pair([0,.2,.2,2,1],[.2,.4,.2,1.8,1])
        b["enriched"][a["race_id"]]["date"]="2024-04-04"
        with self.assertRaisesRegex(ValueError,"race identity"):
            reconcile([a],b,meta)

    def test_repair_may_not_erase_archived_known_starts(self):
        a,b,meta=self.pair([0,.2,.2,2,1],[.2,.4,.2,1.8,.8])
        with self.assertRaisesRegex(ValueError,"removes known starts"):
            reconcile([a],b,meta)


if __name__=="__main__":
    unittest.main()
