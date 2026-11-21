"""Critical old-V7 speed prior-date and V4+speed feature boundary tests."""
import copy
import unittest

from turf_lab.v4_speed_data import dated_speed_features, append_speed

POLICY={
    "history_days":60,"last_starts":5,"minimum_context_races":1,
    "context_prior_strength":1,"distance_bucket_metres":500,
    "minimum_timed_per_race":3,"pace_min":50000,"pace_max":150000,
    "joint_time_distance_tolerance":0.01
}


def race(day, suffix,pace=72000):
    ident=day+"_R1C"+suffix
    participants=[]
    for n in range(1,4):
        runner_pace=pace+n*1000
        participants.append({
           "numPmu":n,"idCheval":"H"+str(n),"nom":"H"+str(n),
           "statut":"PARTANT","incident":None,"ordreArrivee":n,
           "reductionKilometrique":runner_pace,
           "tempsObtenu":int(runner_pace*2.7),
           "handicapDistance":2700
        })
    return {"race_id":ident,"date":day,"venue":"VINCENNES",
            "start_type":"VOLTE","distance_m":2700,"participants":participants}


class V4SpeedTests(unittest.TestCase):
    def test_speed_uses_only_previous_days(self):
        rows=[race("2024-03-01","1"),race("2024-03-02","1",70000),
              race("2024-03-02","2",71000),race("2024-03-03","1",72000)]
        features,audit=dated_speed_features(rows,POLICY)
        a=features[rows[0]["race_id"]][1]
        b=features[rows[1]["race_id"]][1]
        same_day=features[rows[2]["race_id"]][1]
        next_day=features[rows[3]["race_id"]][1]
        self.assertIsNone(a[1])
        self.assertIsNone(b[1])
        self.assertIsNone(same_day[1])
        self.assertIsNotNone(next_day[1])
        self.assertEqual(next_day[2],2)
        self.assertEqual(audit["active"],12)

    def test_only_43rd_feature_is_added_without_mutating_v4(self):
        before={"race_id":"2024-03-03_R1C1","runners":[
           {"number":1,"horse_id":"H1","non_runner":False,"features":[None]*42},
           {"number":2,"horse_id":"H2","non_runner":False,"features":[.1]*42}
        ]}
        pristine=copy.deepcopy(before)
        speed={before["race_id"]:{1:("H1",2.5,2),2:("H2",None,0)}}
        after,cov=append_speed([before],speed)
        self.assertEqual(before,pristine)
        self.assertEqual(after[0]["runners"][0]["features"][:42],pristine["runners"][0]["features"])
        self.assertEqual(after[0]["runners"][0]["features"][-1],2.5)
        self.assertEqual(len(after[0]["runners"][1]["features"]),43)
        self.assertEqual(cov["with_past_context_speed"],1)

    def test_mismatched_id_and_width_refuse_to_train(self):
        frame={"race_id":"2024-03-03_R1C1","runners":[
            {"number":1,"horse_id":"H1","non_runner":False,"features":[0]*42}]}
        wrong={frame["race_id"]:{1:("DIFFERENT_HORSE",1.0,1)}}
        with self.assertRaisesRegex(ValueError,"identity mismatch"):
            append_speed([frame],wrong)
        wrong={frame["race_id"]:{1:("H1",1.0,1)}}
        frame["runners"][0]["features"].pop()
        with self.assertRaisesRegex(ValueError,"width"):
            append_speed([frame],wrong)


if __name__=="__main__":
    unittest.main()
