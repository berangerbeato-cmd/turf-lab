import unittest
from copy import deepcopy
from turf_lab.opposition import augment,candidate
from turf_lab.pilot import fit,probabilities


def race(day, name='r'):
    return {'date':day,'race_id':day+name,'runners':[
        {'horse_id':h,'number':i,'non_runner':False,'rank':i,'won':int(i==1),
         'incident':None,'features':[0,0,0,0,0]} for i,h in enumerate(('a','b'),1)]}

class OppositionTests(unittest.TestCase):
    def test_target_future_and_same_day_do_not_change_features(self):
        rows=[race('2024-01-01'),race('2024-01-02'),race('2024-01-02','s'),race('2024-01-03')]
        old=augment(rows);changed=deepcopy(rows)
        for row in changed[1:]:
            for r in row['runners']:r['rank']=3-r['rank'];r['incident']='DISQUALIFIE'
        new=augment(changed)
        for a,b in zip(old[:3],new[:3]):
            self.assertEqual([r['opposition_features'] for r in a['runners']],[r['opposition_features'] for r in b['runners']])
        self.assertGreater(old[1]['runners'][0]['opposition_features'][0],0)

    def test_unknown_np_and_dq_do_not_become_elo_losses(self):
        for incident,np in [('DISQUALIFIE',False),(None,True),(None,False)]:
            first=race('2024-01-01');first['runners'][1].update(rank=None,incident=incident,non_runner=np)
            result=augment([first,race('2024-01-02')])[1]['runners']
            self.assertEqual(result[0]['opposition_features'][0],0)
            self.assertEqual(result[1]['opposition_features'][0],0)
            if incident:self.assertGreater(result[1]['opposition_features'][2],result[0]['opposition_features'][2])

    def test_new_year_resets_and_inputs_unchanged(self):
        rows=[race('2024-01-01'),race('2025-01-01')];saved=deepcopy(rows)
        result=augment(rows)
        self.assertEqual(result[0]['runners'][0]['opposition_features'],result[1]['runners'][0]['opposition_features'])
        self.assertEqual(rows,saved)

    def test_extended_fit_has_all_dimensions_and_normalized_probabilities(self):
        rows=candidate(augment([race('2024-01-01'),race('2024-01-02')]),'combined')
        model=fit(rows,0.1)
        self.assertEqual(len(model['weights']),18)
        self.assertAlmostEqual(sum(probabilities(rows[1],model).values()),1)
