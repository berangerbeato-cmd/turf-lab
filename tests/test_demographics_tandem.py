import unittest
from copy import deepcopy
from tests.test_connections import fixture
from turf_lab.opposition import augment as opposition
from turf_lab.connections import augment_connections
from turf_lab.demographics_tandem import augment, candidate


class V6Tests(unittest.TestCase):
    def prepare(self):
        rows, records = fixture()
        for rec in records:
            for p in rec['participants']:
                p.update(age=5, sexe='HONGRES')
        return augment_connections(opposition(rows), records), records

    def test_no_same_day_target_future_leakage(self):
        rows, records = self.prepare()
        first = augment(rows, records)
        changed = deepcopy(rows)
        for race in changed[1:]:
            for r in race['runners']:
                r.update(rank=3-r['rank'], incident='DISQUALIFIE')
        second = augment(changed, records)
        for a, b in zip(first[:3], second[:3]):
            self.assertEqual([r['tandem_features'] for r in a['runners']], [r['tandem_features'] for r in b['runners']])

    def test_dimensions_missing_and_expiry(self):
        rows, records = self.prepare()
        records[-1]['participants'][0].update(age=None, sexe=None)
        rows[-1]['date'] = '2024-05-01'
        result = augment(rows, records)
        self.assertEqual(result[-1]['runners'][0]['age_sex_features'], [None]*5)
        self.assertEqual(result[-1]['runners'][0]['tandem_features'][1], 0)
        for name, size in [('v5',29),('age_sex',34),('tandem',33),('combined',38)]:
            self.assertEqual(len(candidate(result, name)[0]['runners'][0]['features']), size)

    def test_nonrunner_never_updates_pair(self):
        rows, records = self.prepare()
        rows[0]['runners'][0]['non_runner'] = True
        result = augment(rows, records)
        self.assertEqual(result[1]['runners'][0]['tandem_features'][3], 0)
