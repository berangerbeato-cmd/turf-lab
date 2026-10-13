import json
import tempfile
import unittest
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from scripts.collect_month import collect
from scripts.shadow_connections import live_record, compute
from scripts.backtest_connections import verify_frozen, PROTOCOL


def fixture():
    meeting = {'numOfficiel': 1, 'hippodrome': {'libelleCourt': 'TEST'}}
    course = {'numOrdre': 1, 'heureDepart': 1791982800000, 'distance': 2100}
    runners = [{'numPmu': i, 'nom': str(i), 'nomMere': 'M', 'nomPere': 'P',
                'statut': 'PARTANT', 'driver': 'D', 'entraineur': 'T'} for i in (1, 2)]
    return meeting, course, runners


class ShadowConnectionsTests(unittest.TestCase):
    def record(self):
        meeting, course, runners = fixture()
        day = datetime.fromtimestamp(course['heureDepart']/1000, timezone.utc).date().isoformat()
        return live_record(day, meeting, course, runners, datetime(2026, 10, 1, tzinfo=timezone.utc))

    def test_live_rejects_results_and_duplicates(self):
        meeting, course, runners = fixture()
        day = datetime.fromtimestamp(course['heureDepart']/1000, timezone.utc).date().isoformat()
        for field in ('ordreArrivee', 'tempsObtenu', 'incident'):
            changed = deepcopy(runners)
            changed[0][field] = 1
            with self.assertRaises(ValueError):
                live_record(day, meeting, course, changed, datetime(2026, 10, 1, tzinfo=timezone.utc))
        with self.assertRaises(ValueError):
            live_record(day, meeting, course, [runners[0], runners[0]], datetime(2026, 10, 1, tzinfo=timezone.utc))

    def test_started_is_rejected(self):
        meeting, course, runners = fixture()
        with self.assertRaises(ValueError):
            live_record('2026-10-14', meeting, course, runners, datetime(2026, 11, 1, tzinfo=timezone.utc))

    def test_normalized_and_target_labels_do_not_change_features(self):
        p = json.loads(PROTOCOL.read_text())
        frozen, models = verify_frozen(p)
        target = self.record()
        result = compute([], target, p, models, frozen['selected'])
        changed = deepcopy(target)
        changed['participants'][0]['ordreArrivee'] = 1
        other = compute([], changed, p, models, frozen['selected'])
        for name in result:
            self.assertEqual(result[name]['probabilities'], other[name]['probabilities'])
            self.assertAlmostEqual(sum(result[name]['probabilities'].values()), 1)
        with self.assertRaises(ValueError):
            compute([target], target, p, models, frozen['selected'])

    def test_partial_collection_stops_and_expands_from_cache(self):
        class Store:
            requests = 0
            def programme(self, day):
                return {'reunions': []}
        with tempfile.TemporaryDirectory() as tmp:
            first = collect('2026-10', Store(), Path(tmp), through='2026-10-02')
            self.assertEqual(len(first['days']), 2)
            again = collect('2026-10', Store(), Path(tmp), through='2026-10-03')
            self.assertEqual(len(again['days']), 3)
            with self.assertRaises(ValueError):
                collect('2026-10', Store(), Path(tmp), through='2026-11-01')
