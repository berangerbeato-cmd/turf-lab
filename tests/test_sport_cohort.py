import json
import tempfile
from pathlib import Path
import unittest
from scripts.collect_sport_cohort import sporting_row, bundle_evidence, restore_evidence, prefetch


def run(day, status='ARRIVE', rank=1):
    return {'raceDate':day, 'racecourse':'TEST', 'raceNumber':1, 'discipline':'ATTELE',
            'raceRunParticipant':{'horseName':'TEST HORSE', 'place':{'arrivalStatus':status, 'runnerRank':rank}}}


class SportCohortTests(unittest.TestCase):
    def setUp(self):
        self.runner = {'nom':'TEST HORSE', 'numPmu':2}

    def row(self, entries):
        return sporting_row({'runner':{'racesRun':entries}}, self.runner, '2026-10-20')

    def test_target_and_future_do_not_affect_features(self):
        before = run('2026-10-10')
        original = self.row([before])
        changed = self.row([run('2026-10-20'), run('2026-10-30'), before])
        self.assertEqual(original['features'], changed['features'])
        self.assertEqual(changed['excluded_target_or_future'], 2)
        self.assertFalse(changed['window_supported'])

    def test_dq_counts_as_failure(self):
        row = self.row([run('2026-10-10', 'DISQUALIFIE', None),run('2026-10-01')])
        self.assertEqual(row['features'][:3], [.5,.5,.5])

    def test_short_truncated_window_is_not_supported(self):
        self.assertFalse(self.row([run('2026-10-10')])['window_supported'])
        row = self.row([run('2026-10-10'),run('2026-08-01')])
        self.assertTrue(row['window_supported'])
        self.assertEqual(len(row['history']), 1)
        self.assertEqual(row['completeness'], 'UNKNOWN_SOURCE_MAY_OMIT_STARTS')

    def test_market_and_target_counters_do_not_enter_features(self):
        baseline = self.row([run('2026-10-10')])
        self.runner.update(dernierRapportDirect={'rapport':80}, nombreCourses=999, ordreArrivee=1)
        self.assertEqual(baseline, self.row([run('2026-10-10')]))

    def test_conflicts_and_identity_fail_closed(self):
        with self.assertRaises(ValueError):
            self.row([run('2026-10-10', rank=1),run('2026-10-10', rank=2)])
        bad=run('2026-10-10');bad['raceRunParticipant']['horseName']='OTHER'
        with self.assertRaises(ValueError):self.row([bad])

    def test_evidence_bundle_restores_exact_bytes(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); evidence=root/'evidence';evidence.mkdir()
            (evidence/'manifest.json').write_text('{}')
            (evidence/'horse.json.gz').write_bytes(b'raw test bytes')
            bundle_evidence(root)
            for path in evidence.iterdir():path.unlink()
            restore_evidence(root)
            self.assertEqual((evidence/'horse.json.gz').read_bytes(), b'raw test bytes')
            self.assertEqual(json.loads((evidence/'manifest.json').read_text()), {})

    def test_changed_selection_rejected_before_network(self):
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder)/'protocol.json').write_text('{"dates":[]}')
            with self.assertRaises(ValueError):
                prefetch({'dates':['2026-10-20']}, folder, 10)
