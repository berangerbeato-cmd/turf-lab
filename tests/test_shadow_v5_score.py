import math
import unittest
from copy import deepcopy
from turf_lab.shadow_v5_score import score, choose_snapshot
from scripts.followup_connections import needs_refresh
from datetime import datetime, timezone


def fixture():
    parts = [{'numPmu': n, 'nom': str(n), 'nomMere': 'M', 'nomPere': 'P', 'statut': 'PARTANT',
              'driver': 'D', 'entraineur': 'T', 'deferre': 'DEFERRE_POSTERIEURS'} for n in (1, 2)]
    prediction = {'predicted_at': '2026-10-13T18:00:00+00:00', 'scheduled_start': '2026-10-14T12:00:00+00:00',
                  'frozen': {'selected': 'combined'}, 'target_snapshot': {'participants': deepcopy(parts)},
                  'models': {'v3': {'probabilities': {'1': .6, '2': .4}}, 'combined': {'probabilities': {'1': .7, '2': .3}}}}
    for p in parts:
        p['ordreArrivee'] = p['numPmu']
    return prediction, {'arriveeDefinitive': True, 'ordreArrivee': [[1], [2]]}, parts


class ScoreTests(unittest.TestCase):
    def test_paired_metrics_and_no_mutation(self):
        p,d,r = fixture()
        old = deepcopy(p)
        result = score(p,d,r)
        self.assertEqual(result['status'], 'SCORED')
        self.assertAlmostEqual(result['models']['combined']['log_loss'], -math.log(.7))
        self.assertAlmostEqual(result['models']['combined']['brier_multiclass'], .18)
        self.assertEqual(p, old)

    def test_pending_late_and_ambiguous(self):
        p,d,r = fixture()
        d['arriveeDefinitive'] = False
        self.assertEqual(score(p,d,r)['status'], 'PENDING')
        d['arriveeDefinitive'] = True
        p['predicted_at'] = p['scheduled_start']
        self.assertEqual(score(p,d,r)['status'], 'QUARANTINE')
        p,d,r = fixture()
        d['ordreArrivee'] = [[1,2]]
        self.assertEqual(score(p,d,r)['status'], 'QUARANTINE')

    def test_runner_equipment_driver_changes_excluded(self):
        for field, value in [('statut','NON_PARTANT'),('driver','OTHER'),('entraineur','OTHER'),('deferre','DEFERRE_ANTERIEURS'),('nom','OTHER')]:
            p,d,r = fixture()
            r[1][field] = value
            self.assertEqual(score(p,d,r)['status'], 'QUARANTINE')

    def test_invalid_probabilities_and_disqualified_winner(self):
        p,d,r = fixture()
        p['models']['combined']['probabilities']['1'] = float('nan')
        self.assertEqual(score(p,d,r)['status'], 'QUARANTINE')
        p,d,r = fixture()
        r[0]['incident'] = 'DISQUALIFIE'
        self.assertEqual(score(p,d,r)['status'], 'QUARANTINE')

    def test_latest_prestart_without_outcome_selection(self):
        p,_,_ = fixture()
        later = deepcopy(p)
        later['predicted_at'] = '2026-10-14T07:00:00+00:00'
        late = deepcopy(p)
        late['predicted_at'] = '2026-10-14T13:00:00+00:00'
        self.assertEqual(choose_snapshot([('old',p),('new',later),('late',late)])[0], 'new')
        self.assertIsNone(choose_snapshot([('late',late)]))

    def test_refresh_delayed_schedule_and_no_repeat(self):
        p,_,_ = fixture()
        p['history_gap_days'] = 1
        snapshots = {'race': [p]}
        now = datetime(2026,10,14,8,30,tzinfo=timezone.utc)
        self.assertTrue(needs_refresh(snapshots, now, '2026-10-14'))
        self.assertFalse(needs_refresh(snapshots, now, '2026-10-15'))
        self.assertFalse(needs_refresh(snapshots, datetime(2026,10,14,13,tzinfo=timezone.utc), '2026-10-14'))
        p['history_gap_days'] = 0
        p['predicted_at'] = '2026-10-14T08:00:00+00:00'
        self.assertFalse(needs_refresh(snapshots, now, '2026-10-14'))
