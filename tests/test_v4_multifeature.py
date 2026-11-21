"""All four historical feature additions and learned market-R safeguards."""
import copy
import unittest
from turf_lab.v4_multi_features import derive,attach,live_context
from turf_lab.v4_reliability_market import probs

def horse(n,rank,gain,day):
    return {"numPmu":n,"nom":"H"+str(n),"nomMere":"M"+str(n),"nomPere":"F"+str(n),
            "statut":"PARTANT","ordreArrivee":rank,"incident":None,
            "gainsParticipant":{"gainsCarriere":gain}}

def race(day,num,grades):
    return {"date":day,"race_id":day+"_R1C"+str(num),
            "participants":[horse(n,rank,gain,day) for n,rank,gain in grades]}

def target(r):
    from turf_lab.month_history import identity
    return {"race_id":r["race_id"],"date":r["date"],"runners":[{
        "number":p["numPmu"],"horse_id":identity(p),"non_runner":False,
        "features":[0.2,0.3,0.1,1.5,.4]+[0]*37+[None],
        "won":int(p["ordreArrivee"]==1)}
        for p in r["participants"]]}

class JointV4FeatureTests(unittest.TestCase):
    def setup(self):
        a=race("2024-01-01",1,[(1,1,10),(2,2,5),(3,3,2)])
        b=race("2024-01-02",1,[(1,3,20),(2,1,8),(3,2,4)])
        c=race("2024-01-02",2,[(1,1,30),(2,3,9),(3,2,6)])
        d=race("2024-01-03",1,[(1,1,40),(2,2,10),(3,3,7)])
        return [a,b,c,d],[target(x) for x in (a,b,c,d)]

    def test_four_features_and_same_day_future_result_is_not_used(self):
        records,rows=self.setup()
        frozen=copy.deepcopy(rows)
        features,audit=derive(rows,records)
        r1=features[records[0]["race_id"]]
        r2=features[records[1]["race_id"]]
        r3=features[records[2]["race_id"]]
        self.assertIsNone(r1[1]["relative_career_gains_prior"])
        self.assertIsNone(r1[1]["weighted_recent_form"])
        self.assertAlmostEqual(r2[1]["weighted_recent_form"],1.)
        self.assertAlmostEqual(r3[1]["weighted_recent_form"],1.)
        self.assertAlmostEqual(r2[1]["relative_career_gains_prior"],r3[1]["relative_career_gains_prior"])
        self.assertGreater(r2[1]["relative_class_proxy"],r2[2]["relative_class_proxy"])
        self.assertLessEqual(r2[1]["reliability_R"],1)
        out,_=attach(rows,features)
        self.assertEqual(len(out[0]["runners"][0]["features"]),47)
        self.assertEqual(rows,frozen)
        self.assertEqual(audit["races"],4)
        self.assertEqual(audit["prior_gains_available"],9)

    def test_stale_money_and_unknowable_rank_are_missing_not_made_up(self):
        records,rows=self.setup()
        records[0]["date"]="2022-01-01"
        records[0]["race_id"]="2022-01-01_R1C1"
        rows[0]["race_id"]="2022-01-01_R1C1"
        rows[0]["date"]="2022-01-01"
        for p in records[0]["participants"]:
            p["ordreArrivee"]=None
        r,_=derive(rows,records)
        self.assertIsNone(r[records[1]["race_id"]][1]["relative_career_gains_prior"])
        self.assertIsNone(r[records[1]["race_id"]][1]["weighted_recent_form"])

    def test_live_rejects_same_day_outcome_history(self):
        records,rows=self.setup()
        with self.assertRaisesRegex(ValueError,"earlier days"):
            live_context(records[:2],records[1],rows[1])

    def test_R_changes_market_sport_weight_but_not_manual_haircut(self):
        odds=[3.,4.,7.]
        sport=[.55,.3,.15]
        neutral=probs(odds,sport,[.2,.8,.3],[.9,.3,0.])
        changed=probs(odds,sport,[.2,.8,.3],[.9,.3,.7])
        self.assertAlmostEqual(sum(neutral),1.)
        self.assertAlmostEqual(sum(changed),1.)
        self.assertNotEqual(neutral,changed)
        with self.assertRaisesRegex(ValueError,"Invalid odds, sport or R"):
            probs(odds,sport,[.2,1.5,.3],[.9,.3,.7])

if __name__=="__main__":
    unittest.main()
