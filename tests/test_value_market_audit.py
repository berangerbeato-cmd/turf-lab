import copy
import json
import tempfile
import unittest
from pathlib import Path
from scripts.audit_value_market import joined_race, odds_band, summarize
from turf_lab.recommendation_policy import recommendation_state


class Audit(unittest.TestCase):
    def record(self):
        return {'race_id':'2026-01-01_R1C1','date':'2026-01-01','scheduled_start_ms':1000,
                'participants':[{'numPmu':n,'statut':'PARTANT','ordreArrivee':1 if n==1 else None,
                    'incident':None if n==1 else 'DISQUALIFIE_POUR_ALLURE_IRREGULIERE',
                    'dernierRapportDirect':{'rapport':c,'typePari':'SIMPLE_GAGNANT','numPmu1':n,'dateRapport':1100}}
                    for n,c in [(1,2.),(2,50.)]]}

    def test_dq_is_loss_and_market_normalizes(self):
        r=joined_race(self.record(),{'1':.6,'2':.4})
        self.assertEqual((r[1]['y'],r[1]['dq']),(0,True))
        self.assertAlmostEqual(sum(x['market_p'] for x in r),1.)
        self.assertEqual(summarize(r)['wins'],1)
        self.assertAlmostEqual(summarize(r)['expected_wins'],1.)
        self.assertTrue(all(x['quote_after_start'] for x in r))

    def test_missing_price_excludes_whole_race(self):
        r=self.record();r['participants'][1].pop('dernierRapportDirect')
        self.assertIsNone(joined_race(r,{'1':.6,'2':.4}))

    def test_bad_probability_and_wrong_market_rejected(self):
        with self.assertRaises(ValueError):joined_race(self.record(),{'1':.6,'2':.6})
        r=self.record();r['participants'][0]['dernierRapportDirect']['numPmu1']=2
        self.assertIsNone(joined_race(r,{'1':.6,'2':.4}))

    def test_nonrunner_not_market_or_loser(self):
        r=self.record();r['participants'].append({'numPmu':3,'statut':'NON_PARTANT'})
        self.assertEqual(len(joined_race(r,{'1':.6,'2':.4,'3':0})),2)
        with self.assertRaises(ValueError):joined_race(r,{'1':.6,'2':.4,'3':.1})

    def test_band_edges(self):
        self.assertEqual([odds_band(x) for x in [2.9,3,5,10,20,50,80]],
                         ['1-3','3-5','5-10','10-20','20-50','50-80','80+'])

    def test_policy_fail_closed(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'policy.json'
            for value in [None,'broken','{}','[]',json.dumps({'status':'ACTIVE','recommendations_allowed':True})]:
                if value is not None:p.write_text(value)
                self.assertFalse(recommendation_state(p)['recommendations_allowed'])
            p.write_text(json.dumps({'status':'SUSPENDED','recommendations_allowed':False,'reasons':['audit']}))
            self.assertEqual(recommendation_state(p)['recommendation_reasons'],['audit'])

    def test_high_ev_does_not_resume_recommendation(self):
        from tests.test_operational_quotes import Quotes
        from turf_lab.operational_quotes import compare
        fixture=Quotes();fixture.setUp();fixture.q['quotes'][0]['decimal_odds']=80
        before=copy.deepcopy(fixture.p)
        result=compare(fixture.p,fixture.q)
        self.assertGreater(result['rows'][0]['models']['v6']['ev'],1)
        self.assertFalse(result['recommendations_allowed'])
        self.assertEqual(result['recommendation_status'],'SUSPENDED')
        self.assertEqual(fixture.p,before)

if __name__=='__main__':unittest.main()
