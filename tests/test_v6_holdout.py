import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from scripts import v6_holdout as h
from tests import test_demographics_tandem as fixtures
from turf_lab.demographics_tandem import augment


class HoldoutTests(unittest.TestCase):
    def test_freeze_and_tampering(self):
        p, lock, _, models = h.verify()
        self.assertEqual(p['v6_selected'], 'combined')
        self.assertEqual(set(models), {'v5', 'v6'})
        with patch.object(h, 'digest', return_value='changed'):
            with self.assertRaises(ValueError):
                h.verify()

    def test_out_of_scope_month_before_network(self):
        with patch.object(h, 'EvidenceStore') as store:
            with self.assertRaises(ValueError):
                h.collect_one('2026-10')
            store.assert_not_called()

    def test_synthetic_evaluation_is_idempotent(self):
        p, lock, v5p, _ = h.verify()
        p.update(minimum_races_per_month=1, source_months=[])
        config = Path('config/demographics_tandem_v6_protocol.json').read_text()
        rows, records = fixtures.V6Tests().prepare()
        rows = augment(rows, records)
        for r, day in zip(rows, ['2025-07-01','2025-07-02','2025-08-01','2025-08-02']):
            r['date'] = day
            r['race_id'] = day
        models = {'v5': {'kind': 'uniform'}, 'v6': {'kind': 'uniform'}}
        previous = Path.cwd()
        with tempfile.TemporaryDirectory() as tmp:
            try:
                os.chdir(tmp)
                Path('config').mkdir()
                Path('config/demographics_tandem_v6_protocol.json').write_text(config)
                with patch.object(h, 'verify', return_value=(p,lock,v5p,models)), patch.object(h, 'load_sources', return_value=([],[])), patch.object(h, 'augment', return_value=rows):
                    h.evaluate()
                    report = json.loads(Path('reports/v6_holdout.json').read_text())
                    self.assertEqual(report['test_races'], 4)
                    self.assertFalse(report['refitted'])
                    original = Path('reports/v6_holdout.json').read_bytes()
                    h.evaluate()
                    self.assertEqual(original, Path('reports/v6_holdout.json').read_bytes())
            finally:
                os.chdir(previous)
