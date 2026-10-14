import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from scripts import v7_holdout as h
from tests import test_demographics_tandem as fixtures
from turf_lab.demographics_tandem import augment


class V7HoldoutTests(unittest.TestCase):
    def test_freeze_and_tampering(self):
        p,lock,_,models=h.verify()
        self.assertEqual(p['test'],{'from':'2025-09-01','to':'2025-10-31'})
        self.assertEqual(set(models),{'v6','v7_speed'})
        with patch.object(h,'digest',return_value='changed'):
            with self.assertRaises(ValueError):
                h.verify()

    def test_scope_guard_before_network(self):
        for month in ('2025-08','2026-10'):
            with patch.object(h,'EvidenceStore') as store:
                with self.assertRaises(ValueError):
                    h.collect_one(month)
                store.assert_not_called()

    def test_evaluation_no_refit_and_idempotent(self):
        p,lock,base,_=h.verify()
        p.update(minimum_races_per_month=1,source_months=[])
        configs={n:Path('config/'+n).read_text() for n in ['demographics_tandem_v6_protocol.json','speed_v7_protocol.json']}
        rows,records=fixtures.V6Tests().prepare()
        rows=augment(rows,records)
        for r,day in zip(rows,['2025-09-01','2025-09-02','2025-10-01','2025-10-02']):
            r.update(date=day,race_id=day)
            for horse in r['runners']:
                horse['speed_features']=[None]
        models={n:{'kind':'uniform'} for n in p['models']}
        previous=Path.cwd()
        with tempfile.TemporaryDirectory() as tmp:
            try:
                os.chdir(tmp)
                Path('config').mkdir()
                for n,content in configs.items():
                    Path('config/'+n).write_text(content)
                with patch.object(h,'verify',return_value=(p,lock,base,models)), patch.object(h,'load_sources',return_value=([],[])), patch.object(h,'augment',return_value=(rows,{})):
                    h.evaluate()
                    output=Path('reports/v7_holdout.json')
                    original=output.read_bytes()
                    result=json.loads(original)
                    self.assertEqual(result['test_races'],4)
                    self.assertFalse(result['refitted'])
                    self.assertEqual(result['speed_coverage']['with_speed'],0)
                    h.evaluate()
                    self.assertEqual(output.read_bytes(),original)
            finally:
                os.chdir(previous)
