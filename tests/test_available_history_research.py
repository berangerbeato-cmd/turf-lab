import unittest
from copy import deepcopy
from turf_lab.month_history import build_history
from turf_lab.available_history_research import available_features, variant, calibrate_temperature
from turf_lab.full_history_evaluation import temper


def race(day, suffix='R1C1', incident=None, rank=1, status='PARTANT'):
    return dict(date=day,race_id=day+'_'+suffix,venue='TEST',country='FRA',start_type='AUTOSTART',distance_m=2100,scheduled_start_ms=0,course={},
        participants=[dict(numPmu=1,nom='A',nomMere='M',nomPere='P',statut=status,ordreArrivee=rank,incident=incident)])


class AvailableHistoryTests(unittest.TestCase):
    def test_old_history_and_day_cutoff(self):
        records=[race('2024-01-01',incident='DISQUALIFIE',rank=None),race('2024-04-01'),race('2024-04-01','R1C2')]
        original=build_history(records,60); before=deepcopy(original)
        rows,audit=available_features(records,original)
        self.assertEqual(rows[1]['runners'][0]['available_recent'],rows[2]['runners'][0]['available_recent'])
        self.assertEqual(rows[1]['runners'][0]['features'][4],0)
        self.assertEqual(rows[1]['runners'][0]['available_recent'][4],.2)
        self.assertEqual(rows[1]['runners'][0]['dq20_features'][1],.05)
        self.assertEqual(audit['history_empty_at_60_days_but_available'],2)
        variant(rows,'last5_available_dq20')
        self.assertEqual(original,before)
        self.assertEqual(len(variant(rows,'last5_available_dq20')[0]['runners'][0]['features']),9)

    def test_unknown_and_nonrunner_not_safe_results(self):
        records=[race('2024-01-01',rank=None),race('2024-01-02',status='NON_PARTANT'),race('2024-01-03')]
        rows,_=available_features(records,build_history(records,60))
        self.assertEqual(rows[-1]['runners'][0]['dq20_features'],[.2,0,None,0])
        self.assertIsNone(rows[-1]['runners'][0]['available_recent'][1])

    def test_fail_closed_on_changed_archive(self):
        records=[race('2024-01-01')]; frames=build_history(records,60)
        frames[0]['runners'][0]['features'][0]=.5
        with self.assertRaises(ValueError): available_features(records,frames)

    def test_temperature_preserves_ranking_and_normalization(self):
        rows=[dict(runners=[dict(number=1,won=1,non_runner=False),dict(number=2,won=0,non_runner=False)])]*3
        pred=[{1:.6,2:.4}]*3
        temp=calibrate_temperature(rows,pred)
        self.assertTrue(.5<=temp<=3)
        for p in temper(rows,pred,temp):
            self.assertAlmostEqual(sum(p.values()),1)
            self.assertGreater(p[1],p[2])
