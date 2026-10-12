import unittest
from turf_lab.history import before_target, summarize_run, parse_time_seconds


def run(day, status="PLACE", rank=1):
    return {"raceDate":day,"racecourseCode":"VIN","raceNumber":1,"discipline":"ATTELE",
            "distance":2700,"raceRunParticipant":{"place":{"arrivalStatus":status,"runnerRank":rank},
                                                    "mileageReduction":"1'12\"30", "shoes":"3"}}


class HistoryTests(unittest.TestCase):
    def test_cannot_leak_target_or_future_race(self):
        history = {"runner":{"racesRun":[run("2026-10-06"),run("2026-10-05"),run("2026-10-01")]}}
        rows, rejected, n = before_target(history,"2026-10-05")
        self.assertEqual([r['raceDate'] for r in rows],["2026-10-01"])
        self.assertEqual(len(rejected),2)
        self.assertEqual(n,1)

    def test_non_runner_does_not_count_as_performance(self):
        history = {"runner":{"racesRun":[run("2026-10-01","NON_PARTANT"),run("2026-09-01")]}}
        rows, _, n = before_target(history,"2026-10-05")
        self.assertEqual(n,1)

    def test_disqualification_not_imputed_rank_or_speed(self):
        row = summarize_run(run("2026-09-01","DISQUALIFIE_POUR_ALLURE_IRREGULIERE",1))
        self.assertTrue(row['disqualified'])
        self.assertIsNone(row['rank'])
        self.assertIsNone(row['seconds_per_km'])

    def test_conflicting_duplicates_fail(self):
        history = {"runner":{"racesRun":[run("2026-09-01",rank=1),run("2026-09-01",rank=2)]}}
        with self.assertRaises(ValueError): before_target(history,"2026-10-05")

    def test_distanced_horse_cannot_keep_a_winning_rank(self):
        row=summarize_run(run("2026-09-01","DISTANCE",1))
        self.assertTrue(row['disqualified'])
        self.assertIsNone(row['rank'])

    def test_source_time_units(self):
        self.assertAlmostEqual(parse_time_seconds("1'14\"70"),74.7)
        self.assertAlmostEqual(parse_time_seconds("1'14\"7"),74.7)
        self.assertIsNone(parse_time_seconds("0'00\"00"))
        self.assertIsNone(parse_time_seconds("1'64\"70"))


if __name__ == '__main__': unittest.main()
