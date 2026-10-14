import json
import unittest
from copy import deepcopy
from pathlib import Path
from turf_lab.context_speed import augment, pace
from turf_lab.month_history import identity


def fixture():
    policy=json.loads(Path('config/speed_v7_protocol.json').read_text())
    policy['minimum_context_races']=1
    rows,records=[],[]
    for i,day in enumerate(['2024-01-01','2024-01-02','2024-01-03','2024-01-03','2024-01-04']):
        parts=[{'numPmu':n,'nom':str(n),'nomMere':'M','nomPere':'P','statut':'PARTANT',
            'ordreArrivee':n,'handicapDistance':2000,'reductionKilometrique':70000+n*1000,
            'tempsObtenu':(70000+n*1000)*2} for n in (1,2,3)]
        rid=day+'_'+str(i)
        records.append({'race_id':rid,'date':day,'venue':'A','start_type':'AUTO','distance_m':2000,'participants':parts})
        rows.append({'race_id':rid,'date':day,'runners':[{'horse_id':identity(p),'non_runner':False} for p in parts]})
    return rows,records,policy


class SpeedTests(unittest.TestCase):
    def test_past_only_and_day_batching(self):
        rows,records,p=fixture()
        first,_=augment(rows,records,p)
        self.assertIsNone(first[1]['runners'][0]['speed_features'][0])
        self.assertAlmostEqual(first[2]['runners'][0]['speed_features'][0],1)
        changed=deepcopy(records)
        for r in changed[2:]:
            for h in r['participants']:
                h['reductionKilometrique']+=5000
                h['tempsObtenu']+=10000
        second,_=augment(rows,changed,p)
        self.assertEqual(first[:4],second[:4])
        self.assertNotEqual(first[4],second[4])
        self.assertNotIn('speed_features',rows[0]['runners'][0])

    def test_invalid_units_dq_and_nonrunner(self):
        _,records,p=fixture()
        r=records[0]
        h=r['participants'][0]
        self.assertEqual(pace(h,r,p),71000)
        for key,value in [('tempsObtenu',142),('statut','NON_PARTANT'),('incident','DISQUALIFIE'),
                          ('ordreArrivee',True),('reductionKilometrique',float('nan'))]:
            other=dict(h,**{key:value})
            self.assertIsNone(pace(other,r,p))
        other=dict(h,handicapDistance=2025,tempsObtenu=71000*2.025)
        self.assertEqual(pace(other,r,p),71000)

    def test_expiry_and_year_reset(self):
        for day in ('2024-06-01','2025-01-01'):
            rows,records,p=fixture()
            rows[-1]['date']=records[-1]['date']=day
            out,_=augment(rows,records,p)
            self.assertIsNone(out[-1]['runners'][0]['speed_features'][0])

    def test_context_never_uses_its_own_race(self):
        rows,records,p=fixture()
        # The second race is fast; its context must remain that of the first race.
        for h in records[1]['participants']:
            h['reductionKilometrique']-=10000
            h['tempsObtenu']-=20000
        out,_=augment(rows,records,p)
        self.assertAlmostEqual(out[2]['runners'][0]['speed_features'][0],11)

    def test_source_date_guard(self):
        rows,records,p=fixture()
        records[0]['date']='2024-01-05'
        with self.assertRaisesRegex(ValueError,'date mismatch'):
            augment(rows,records,p)
