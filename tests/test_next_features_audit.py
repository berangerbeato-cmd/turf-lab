import unittest
from copy import deepcopy
from scripts.audit_next_features import audit, ceiling, timed


def record(day, suffix=''):
    return {'date': day, 'race_id': day+suffix, 'distance_m': 2000, 'course': {},
            'participants': [{'nom': 'A', 'nomMere': 'M', 'nomPere': 'P', 'statut': 'PARTANT',
                'driver': 'D', 'age': 5, 'sexe': 'HONGRES', 'ordreArrivee': 1,
                'reductionKilometrique': 75000, 'tempsObtenu': 150000}]}


class NextFeatureTests(unittest.TestCase):
    def test_conservative_ceiling(self):
        self.assertEqual(ceiling("Pour 6 ans, n'ayant pas gagné 69.000. Recul de 25 m."), 69000)
        self.assertEqual(ceiling("n’ayant pas gagné 100 000 euros"), 100000)
        self.assertIsNone(ceiling('ayant gagné au moins 10.000'))
        self.assertIsNone(ceiling("n'ayant pas gagné 10.000 et n'ayant pas gagné 20.000"))

    def test_same_day_target_and_future_excluded(self):
        rows = [record('2025-03-01'), record('2025-03-02'), record('2025-03-02', 's'), record('2025-03-03')]
        bounds = [{'from': '2025-03-02', 'to': '2025-03-02'}]
        a = audit(rows, bounds)['evaluated']
        changed = deepcopy(rows)
        for r in changed[1:]:
            r['participants'][0].update(reductionKilometrique=None, ordreArrivee=None)
        b = audit(changed, bounds)['evaluated']
        for key in ('past_chrono_one', 'past_chrono_three', 'past_pair_one', 'past_pair_three'):
            self.assertEqual(a[key], b[key])
        self.assertEqual(a['past_chrono_one'], 2)
        self.assertEqual(a['past_chrono_three'], 0)

    def test_expiry_and_nonrunner(self):
        rows = [record('2025-01-01'), record('2025-04-01')]
        a = audit(rows, [{'from': '2025-04-01', 'to': '2025-04-01'}])['evaluated']
        self.assertEqual(a['past_pair_one'], 0)
        rows[0] = record('2025-03-31')
        rows[0]['participants'][0]['statut'] = 'NON_PARTANT'
        a = audit(rows, [{'from': '2025-04-01', 'to': '2025-04-01'}])['evaluated']
        self.assertEqual(a['past_pair_one'], 0)
        self.assertEqual(a['past_chrono_one'], 0)

    def test_disqualification_not_a_valid_chrono(self):
        p = record('2025-01-01')['participants'][0]
        self.assertTrue(timed(p))
        p['incident'] = 'DISQUALIFIE'
        self.assertFalse(timed(p))
