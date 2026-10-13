import hashlib
import json
import unittest
from copy import deepcopy
from unittest.mock import patch
from turf_lab.shadow_quarantine import apply_quarantine
from scripts.shadow_connections import record_failure


class QuarantineTests(unittest.TestCase):
    def fixture(self):
        records = [{'race_id': '2026-07-04_R6C7'}]
        digest = hashlib.sha256((json.dumps(records[0], ensure_ascii=False, sort_keys=True)+'\n').encode()).hexdigest()
        coverage = [{'month': '2026-07', 'retained': 100, 'quarantine': [],
                     'coverage_counts': {'retained': 100, 'eligible': 100, 'unresolved': 0, 'fraction': 1}}]
        exclusions = [{'race_id': records[0]['race_id'], 'source_sha256': digest, 'reason': 'identity'}]
        return records, coverage, exclusions

    def test_preserves_raw_and_denominator(self):
        records, coverage, exclusions = self.fixture()
        old = deepcopy(coverage)
        remaining, adjusted, audit = apply_quarantine(records, coverage, exclusions, .98)
        self.assertEqual(remaining, [])
        self.assertEqual(len(records), 1)
        self.assertEqual(coverage, old)
        self.assertEqual(adjusted[0]['coverage_counts']['eligible'], 100)
        self.assertEqual(adjusted[0]['coverage_counts']['unresolved'], 1)
        self.assertEqual(adjusted[0]['coverage_counts']['fraction'], .99)
        self.assertEqual(audit, exclusions)

    def test_source_changes_and_missing_target_block(self):
        records, coverage, exclusions = self.fixture()
        records[0]['extra'] = 'changed'
        with self.assertRaisesRegex(ValueError, 'source changed'):
            apply_quarantine(records, coverage, exclusions, .98)
        with self.assertRaisesRegex(ValueError, 'absent'):
            apply_quarantine([], coverage, exclusions, .98)

    def test_coverage_is_not_lowered(self):
        records, coverage, exclusions = self.fixture()
        with self.assertRaisesRegex(ValueError, 'Coverage gate'):
            apply_quarantine(records, coverage, exclusions, 1)

    def test_failure_preserves_current_rejections_and_saved_paths(self):
        state = {'batch': 'test', 'saved': ['capture'], 'rejected': [{'race_id': 'r', 'reason': 'identity'}]}
        with patch('scripts.shadow_connections.dump') as dump:
            record_failure(state, ValueError('No valid prospective capture'))
        self.assertEqual(state['rejected'][0]['reason'], 'identity')
        self.assertEqual(state['saved'], ['capture'])
        self.assertEqual(state['status'], 'BLOCKED_NO_BET')
        self.assertEqual(dump.call_count, 2)
