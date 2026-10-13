import unittest
from copy import deepcopy
from turf_lab.context import departure,augment_context,candidate
from turf_lab.opposition import augment
from tests.test_opposition import race


def inputs():
    rows=[race('2024-01-01'),race('2024-01-02'),race('2024-01-02','s'),race('2024-01-03')]
    raw=[]
    for r in rows:
        r.update(venue='A',distance_m=2700,start_type='AUTOSTART')
        raw.append({'race_id':r['race_id'],'course':{'distance':2700,'conditions':'AUTOSTART'},
                    'participants':[{'numPmu':i,'handicapDistance':2700} for i in (1,2)]})
    return rows,raw

class ContextTests(unittest.TestCase):
    def test_advance_requires_proof_and_number_is_never_position(self):
        c={'distance':2700,'conditions':'Avance de 25 m.'}
        self.assertEqual(departure(c,{'handicapDistance':2675,'numPmu':18})[0][0],-1)
        self.assertIsNone(departure({'distance':2700},{'handicapDistance':2675})[0][0])
        self.assertEqual(departure(c,{'handicapDistance':2725})[0][0],1)
        self.assertIsNone(departure(c,{'numPmu':1})[0][0])
        self.assertIsNone(departure(c,{'handicapDistance':2600})[0][0])

    def test_same_day_and_future_results_cannot_change_current_context(self):
        rows,raw=inputs();old=augment_context(augment(rows),raw);changed=deepcopy(rows)
        for row in changed[1:]:
            for p in row['runners']:p['rank']=3-p['rank']
        new=augment_context(augment(changed),raw)
        for a,b in zip(old[:3],new[:3]):
            self.assertEqual([p['aptitude_features'] for p in a['runners']],[p['aptitude_features'] for p in b['runners']])
        self.assertGreater(old[1]['runners'][0]['aptitude_features'][0],0)
        self.assertEqual(len(candidate(old,'combined')[0]['runners'][0]['features']),17)

    def test_dq_np_and_expired_history_not_used_as_performance(self):
        for status,np in [('DISQUALIFIE',False),(None,True)]:
            rows,raw=inputs();rows[0]['runners'][0].update(incident=status,non_runner=np,rank=None)
            result=augment_context(augment(rows),raw)
            self.assertIsNone(result[1]['runners'][0]['aptitude_features'][0])
        rows,raw=inputs();rows[-1]['date']='2024-04-01'
        result=augment_context(augment(rows),raw)
        self.assertIsNone(result[-1]['runners'][0]['aptitude_features'][0])

    def test_unknown_start_type_not_standing_start(self):
        rows,raw=inputs();rows[1]['start_type']='NON_PRECISE'
        result=augment_context(augment(rows),raw)
        self.assertIsNone(result[1]['runners'][0]['aptitude_features'][4])
