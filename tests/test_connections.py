import importlib.util
import unittest
from copy import deepcopy
from tests.test_opposition import race
from turf_lab.opposition import augment
from turf_lab.connections import augment_connections,candidate,equipment


def fixture():
    rows=[race('2024-01-01'),race('2024-01-02'),race('2024-01-02','s'),race('2024-01-03')]
    records=[{'race_id':r['race_id'],'participants':[
        {'numPmu':i,'driver':'D'+str(i),'entraineur':'T'+str(i),'deferre':'DEFERRE_POSTERIEURS'} for i in (1,2)]} for r in rows]
    return rows,records


class ConnectionsTests(unittest.TestCase):
    def test_no_target_same_day_or_future_leakage(self):
        rows,records=fixture();old=augment_connections(augment(rows),records);changed=deepcopy(rows)
        for row in changed[1:]:
            for r in row['runners']:r['rank']=3-r['rank'];r['incident']='DISQUALIFIE'
        new=augment_connections(augment(changed),records)
        for a,b in zip(old[:3],new[:3]):
            self.assertEqual([r['connection_features'] for r in a['runners']],[r['connection_features'] for r in b['runners']])
        self.assertGreater(old[1]['runners'][0]['connection_features']['driver'][0],0)

    def test_missing_equipment_never_means_shod_or_no_change(self):
        rows,records=fixture();records[1]['participants'][0]['deferre']=None
        result=augment_connections(augment(rows),records)[1]['runners'][0]
        self.assertEqual(equipment(None),'UNKNOWN')
        self.assertEqual(result['connection_features']['equipment'][8],1)
        self.assertIsNone(result['connection_features']['equipment'][9])

    def test_changes_and_unknown_people(self):
        rows,records=fixture();records[1]['participants'][0].update(deferre='DEFERRE_ANTERIEURS',driver=None)
        result=augment_connections(augment(rows),records)[1]['runners'][0]
        self.assertEqual(result['connection_features']['equipment'][9],1)
        self.assertIsNone(result['connection_features']['driver'][0])
        self.assertIsNone(result['connection_features']['driver'][2])

    def test_np_dq_and_expiry(self):
        rows,records=fixture();rows[0]['runners'][0].update(non_runner=True)
        result=augment_connections(augment(rows),records)[1]['runners'][0]
        self.assertEqual(result['connection_features']['driver'][3],0)
        rows,records=fixture();rows[0]['runners'][0].update(rank=None,incident='DISQUALIFIE')
        result=augment_connections(augment(rows),records)[1]['runners'][0]
        self.assertIsNone(result['connection_features']['driver'][0])
        self.assertGreater(result['connection_features']['driver'][2],0)
        rows[-1]['date']='2024-05-01'
        result=augment_connections(augment(rows),records)[-1]['runners'][0]
        self.assertEqual(result['connection_features']['driver'][3],0)
        self.assertIsNone(result['connection_features']['equipment'][9])

    @unittest.skipUnless(importlib.util.find_spec('numpy'),'V5 workflow installs numpy')
    def test_fast_optimizer_matches_existing_reference(self):
        from turf_lab.fast_logit import fit
        from turf_lab.pilot import fit as reference,probabilities
        rows,records=fixture();data=candidate(augment_connections(augment(rows),records),'combined')
        a=fit(data,0.1);b=reference(data,0.1)
        for x,y in zip(a['weights'],b['weights']):self.assertAlmostEqual(x,y,places=11)
        self.assertAlmostEqual(sum(probabilities(data[-1],a).values()),1)

