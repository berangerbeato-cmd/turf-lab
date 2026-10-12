import copy
import unittest
from turf_lab.month_history import build_history


def race(day, suffix='1', incident=None, np=False):
    return {'date': day, 'race_id':day+'_'+suffix, 'venue':'TEST', 'country':'FRA',
        'start_type':'NON_PRECISE','distance_m':2100,'scheduled_start_ms':0,
        'participants':[{'numPmu':1,'nom':'A','nomMere':'M','nomPere':'P',
           'ordreArrivee':None if incident else 1, 'incident':incident,
           'statut':'NON_PARTANT' if np else 'PARTANT'}]}

class MonthlyHistoryTests(unittest.TestCase):
    def test_future_and_same_day_excluded(self):
        first=race('2024-01-01');same=race('2024-01-01','2');next_=race('2024-01-03')
        rows=build_history([next_,same,first])
        self.assertEqual(rows[0]['runners'][0]['history'],[])
        self.assertEqual(rows[1]['runners'][0]['history'],[])
        self.assertEqual(len(rows[2]['runners'][0]['history']),2)
        changed=copy.deepcopy(next_);changed['participants'][0]['ordreArrivee']=8
        altered=build_history([first,same,changed])
        self.assertEqual(rows[-1]['runners'][0]['features'],altered[-1]['runners'][0]['features'])

    def test_np_skipped_and_dq_preserved(self):
        rows=build_history([race('2024-01-01',np=True),race('2024-01-02',incident='DISQUALIFIE'),race('2024-01-04')])
        runner=rows[-1]['runners'][0]
        self.assertEqual(len(runner['history']),1)
        self.assertEqual(runner['features'][:3],[0.0,0.0,1.0])
        self.assertIsNone(runner['history'][0]['rank'])

    def test_no_market_dependency_and_duplicate_rejected(self):
        r=race('2024-01-01'); later=race('2024-01-03')
        base=build_history([r,later])
        later['participants'][0]['rapportDirect']={'rapport':99}
        self.assertEqual(base,build_history([r,later]))
        with self.assertRaises(ValueError):build_history([r,r])
