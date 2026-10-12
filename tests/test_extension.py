import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from scripts.backtest_extension import load_sources

class ExtensionTests(unittest.TestCase):
    def test_protocol_has_disjoint_unseen_test_and_warmup(self):
        p=json.loads(Path('config/history_extension_protocol.json').read_text())
        self.assertEqual(len(set(p['months'])),9)
        self.assertLess(p['train']['to'],p['validation']['from'])
        self.assertLess(p['validation']['to'],p['test']['from'])
        self.assertLess(p['test']['to'],'2026-10-05')
        self.assertEqual(p['lookback_days'],60)

    def test_missing_programme_blocks_training(self):
        protocol={'months':['2024-01']}
        manifest={'status':'COLLECTED_WITH_GAPS','days':[{'date':'2024-01-01','status':'PROGRAMME_UNAVAILABLE'}]}
        with patch('pathlib.Path.read_text',return_value=json.dumps(manifest)):
            with self.assertRaisesRegex(ValueError,'Incomplete monthly programmes'):
                load_sources(protocol)

    def test_end_to_end_freezes_test_and_fits_only_training_period(self):
        import os
        from scripts.backtest_extension import main
        from tests.test_month_history import race
        protocol=json.loads(Path('config/history_extension_protocol.json').read_text())
        protocol['minimum_races_per_split']=2
        records=[race(f'{year}-03-{day:02d}') for year in (2024,2025,2026) for day in (2,3)]
        previous=os.getcwd()
        with tempfile.TemporaryDirectory() as tmp:
            try:
                os.chdir(tmp)
                Path('config').mkdir()
                Path('config/history_extension_protocol.json').write_text(json.dumps(protocol))
                with patch('scripts.backtest_extension.load_sources',return_value=(records,[])), patch('scripts.backtest_extension.fit',return_value={'kind':'uniform'}) as fit_mock, patch('builtins.print'):
                    main()
                    self.assertEqual(fit_mock.call_count,2)
                    for call in fit_mock.call_args_list:
                        self.assertTrue(all(r['date'].startswith('2024-') for r in call.args[0]))
                    result=json.loads(Path('reports/backtest_extension_v2.json').read_text())
                    self.assertEqual(result['split_races'],{'train':2,'validation':2,'test':2})
                    main()
                    self.assertEqual(fit_mock.call_count,2)
            finally:
                os.chdir(previous)
