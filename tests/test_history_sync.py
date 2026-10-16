import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch
from turf_lab.history_sync import Collector, History, days_until, summarize, cancelled, validate


def state(day='2026-10-15', status='OK'):
    return dict(date=day,status=status,records=[],pending=[],cancellations={},issues=[],expected=0,programme={'reunions':[]})


class HistorySyncTests(unittest.TestCase):
    def test_calendar_no_seven_day_limit(self):
        days=days_until(date(2026,10,16))
        self.assertEqual(days[0],'2022-01-01')
        self.assertEqual(days[-1],'2026-10-15')
        self.assertIn('2024-02-29',days)
        self.assertNotIn('2026-10-16',days)

    def test_gap_blocks_ok_even_when_yesterday_complete(self):
        rows=[state('2022-01-01'),state('2022-01-02','PARTIEL'),state()]
        rows[1]['pending']=[dict(race_id='missing',reasons=['not_final'])]
        r=summarize(rows,date(2026,10,16))
        self.assertEqual(r['status'],'PARTIEL')
        self.assertEqual(r['last_complete_day'],'2026-10-15')
        self.assertEqual(r['complete_continuously_through'],'2022-01-01')
        self.assertEqual(r['missing_races'],1)

    def test_unknown_programme_not_zero_races(self):
        s=state(status='PARTIEL');s['expected']=None
        r=summarize([s],date(2026,10,16))
        self.assertEqual(r['unknown_programme_days'],1)
        self.assertEqual(r['status'],'PARTIEL')

    def test_complete_day_no_download(self):
        collector=Collector()
        with patch.object(collector,'fetch',side_effect=AssertionError('download')):
            collector.repair(state())
        self.assertEqual(collector.requests,0)

    def test_cancel_requires_unambiguous_evidence(self):
        self.assertFalse(cancelled({'statut':'COURSE_ANNULEE'}))
        self.assertTrue(cancelled({'statut':'COURSE_ANNULEE','categorieStatut':'ANNULEE'}))
        self.assertFalse(cancelled({'statut':'COURSE_ANNULEE','categorieStatut':'ANNULEE','ordreArrivee':[[1]]}))

    def test_dead_heat_is_archived(self):
        r=dict(race_id='x',course={'nombreDeclaresPartants':2},participants=[
            dict(numPmu=1,idCheval='a',ordreArrivee=1),dict(numPmu=2,idCheval='b',ordreArrivee=1)],
            detail={'ordreArrivee':[[1,2]],'arriveeDefinitive':True})
        self.assertEqual(validate(r),[])
        r['detail']['arriveeDefinitive']=False
        self.assertTrue(validate(r))

    def test_repair_skips_verified_race_and_is_idempotent(self):
        from turf_lab.history_sync import make_record
        meeting={'numOfficiel':1,'pays':{'code':'FRA'},'hippodrome':{'libelleCourt':'test'}}
        courses=[dict(numOrdre=i,discipline='ATTELE',distance=2000,heureDepart=1,nombreDeclaresPartants=1) for i in (1,2)]
        meeting['courses']=courses
        parts={'participants':[dict(numPmu=1,idCheval='a',ordreArrivee=1)]}
        detail={'arriveeDefinitive':True,'ordreArrivee':[[1]]}
        s=state(status='PARTIEL');s['programme']={'reunions':[meeting]};s['expected']=2
        s['records']=[make_record(s['date'],meeting,courses[0],parts,detail)]
        with tempfile.TemporaryDirectory() as tmp, patch('turf_lab.history_sync.OVERLAYS',Path(tmp)):
            collector=Collector()
            with patch.object(collector,'fetch',side_effect=[detail,parts]) as fetch:
                collector.repair(s)
                self.assertEqual(fetch.call_count,2)
                self.assertEqual(fetch.call_args_list[0].args[2],2)
            history=History.__new__(History);history.entries={};history.sources={}
            result=history.day(s['date'])
            self.assertEqual(result['status'],'OK')
            with patch.object(collector,'fetch',side_effect=AssertionError('duplicate')):
                collector.repair(result)
            self.assertEqual(len(result['records']),2)

if __name__=='__main__':unittest.main()
