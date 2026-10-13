import importlib.util
import json
import os
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch
from tests.test_connections import fixture
from turf_lab.opposition import augment
from turf_lab.connections import augment_connections
from scripts.backtest_connections import split,validate,test as evaluate_test,verify_frozen


class ConnectionsPipelineTests(unittest.TestCase):
    def test_missing_month_blocks_instead_of_shortening_validation(self):
        with self.assertRaisesRegex(ValueError,'Incomplete evaluation months'):
            split([{'date':'2025-03-02'}],{'from':'2025-03-02','to':'2025-05-31'},1)

    @unittest.skipUnless(importlib.util.find_spec('numpy'),'V5 workflow installs numpy')
    def test_selection_is_frozen_before_independent_evaluation(self):
        from turf_lab.fast_logit import fit
        protocol=json.loads(Path('config/connections_v5_protocol.json').read_text())
        protocol['minimum_races_per_month']=1;protocol['iterations']=2
        base,raw=fixture();row=augment_connections(augment(base),raw)[0]
        rows=[]
        for year,months in [(2024,[3,4,5]),(2025,[3,4,5]),(2026,[5,6])]:
            for month in months:
                r=deepcopy(row);r['date']=f'{year}-{month:02d}-02';r['race_id']=r['date'];rows.append(r)
        previous=os.getcwd()
        with tempfile.TemporaryDirectory() as tmp:
            try:
                os.chdir(tmp);Path('config').mkdir()
                Path('config/connections_v5_protocol.json').write_text(json.dumps(protocol))
                with patch('scripts.backtest_connections.CODE',['config/connections_v5_protocol.json']),patch('scripts.backtest_connections.prepare',return_value=(rows,'synthetic',[])) as source,patch('scripts.backtest_connections.fit',wraps=fit) as fitting,patch('builtins.print'):
                    validate(protocol)
                    self.assertEqual(fitting.call_count,5)
                    self.assertTrue(all(all(r['date'].startswith('2024') for r in c.args[0]) for c in fitting.call_args_list))
                    self.assertEqual(source.call_args.args[1],'validate')
                    validate(protocol);self.assertEqual(fitting.call_count,5)
                    evaluate_test(protocol);self.assertEqual(fitting.call_count,5)
                    self.assertEqual(source.call_args.args[1],'test')
                    out=json.loads(Path('reports/connections_v5_test.json').read_text())
                    self.assertEqual(out['test_races'],2);self.assertFalse(out['refitted'])
                    Path('models/connections_v5_candidates.json').write_text('{}')
                    with self.assertRaisesRegex(ValueError,'Frozen model/protocol mismatch'):verify_frozen(protocol)
            finally:os.chdir(previous)
