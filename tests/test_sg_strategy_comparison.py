import unittest
from datetime import datetime,timezone,timedelta
from unittest.mock import patch
from turf_lab.sg_strategy_comparison import select,settle,summarize

class Strategies(unittest.TestCase):
    def setUp(self):
        self.now=datetime(2026,11,16,12,tzinfo=timezone.utc)
        self.protocol=dict(first_eligible_race_date='2026-11-16',model='v3',model_sha256='abc',minimum_ev=.1,stake_eur_per_runner=1,strategies=[dict(id='top1',max_rank=1),dict(id='top2',max_rank=2),dict(id='top3',max_rank=3),dict(id='top4',max_rank=4),dict(id='p10',min_probability=.1),dict(id='p15',min_probability=.15),dict(id='p20',min_probability=.2)])
        self.p=dict(race_id='race',scheduled_start=(self.now+timedelta(minutes=2)).isoformat(),predicted_at=self.now.isoformat(),target_snapshot=dict(date='2026-11-16',participants=[dict(numPmu=n,statut='PARTANT') for n in range(1,6)]),models={'v3':{'model_sha256':'abc'}},individual_history_check={'status':'CHECKED_RETURNED_HISTORY_ONLY'})
        self.q=dict(operator='ZEturf',observed_at=self.now.isoformat(),quotes=[dict(number=n) for n in range(1,6)])
        self.rows=[dict(number=n,models={'v3':dict(probability=p,ev=e)}) for n,p,e in [(1,.4,.1),(2,.25,.09),(3,.15,.2),(4,.1,.1),(5,.1,.1)]]
    def choose(self):
        with patch('turf_lab.sg_strategy_comparison.compare',return_value={'rows':self.rows}):return select(self.p,self.q,self.protocol,self.now)
    def test_exact_thresholds_and_rank_before_ev(self):
        self.assertEqual(self.choose()['strategies'],{'top1':[1],'top2':[1],'top3':[1,3],'top4':[1,3,4],'p10':[1,3,4,5],'p15':[1,3],'p20':[1]})
    def test_after_start_rejected(self):
        self.p['scheduled_start']=self.now.isoformat()
        with self.assertRaises(ValueError):self.choose()
    def test_missing_quote_rejected(self):
        self.q['quotes'].pop()
        with self.assertRaises(ValueError):self.choose()
    def test_old_quote_rejected(self):
        self.q['observed_at']=(self.now-timedelta(minutes=20)).isoformat()
        with self.assertRaises(ValueError):self.choose()
    def test_seen_race_rejected(self):
        self.p['target_snapshot']['date']='2026-11-15'
        with self.assertRaises(ValueError):self.choose()
    def test_model_change_rejected(self):
        self.p['models']['v3']['model_sha256']='new'
        with self.assertRaises(ValueError):self.choose()
    def test_missing_payout_pending(self):self.assertEqual(settle(self.choose(),None)['status'],'PENDING')
    def evidence(self):return dict(race_id='race',operator='ZEturf',verified=True,final=True,source_evidence='official receipt',observed_at=(self.now+timedelta(hours=1)).isoformat(),winner_numbers=[1],sg_total_return_per_eur={'1':3.5,'3':0,'4':0,'5':0})
    def test_actual_dividend_and_drawdown(self):
        s=self.choose();e=self.evidence();r=settle(s,e)
        self.assertEqual(r['strategies']['p10']['net'],-.5)
        report=summarize([(s,r),(dict(s,race_id='next'),{'status':'PENDING'})])
        self.assertEqual(report['all']['p10']['max_drawdown'],.5);self.assertEqual(report['pending'],1)
    def test_wrong_operator_rejected(self):
        e=self.evidence();e['operator']='PMU'
        with self.assertRaises(ValueError):settle(self.choose(),e)
    def test_partial_settlement_pending(self):
        e=self.evidence();del e['sg_total_return_per_eur']['4']
        self.assertEqual(settle(self.choose(),e)['status'],'PENDING')
    def test_dead_heat_actual_paid_reports(self):
        e=self.evidence();e['winner_numbers']=[1,3];e['sg_total_return_per_eur'].update({'1':1.7,'3':4.2})
        r=settle(self.choose(),e)['strategies']['top3'];self.assertAlmostEqual(r['returned'],5.9);self.assertEqual(r['wins'],2)
