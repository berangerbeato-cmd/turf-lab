import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from turf_lab.available_history_operational import verify_active, compute
from turf_lab.operational_quotes import compare


class ActiveModelTests(unittest.TestCase):
    def test_exact_selected_model_and_temperature(self):
        policy,t=verify_active()
        frozen=json.loads(Path(policy['selection_file']).read_text())
        self.assertEqual(policy['variant'],'last5_available_dq20')
        self.assertEqual(t,frozen['temperatures']['last5_available_dq20'])
        self.assertFalse(policy['recommendations_allowed'])

    def test_bad_hash_blocks_inference(self):
        policy,_=verify_active(); policy['files_sha256'][policy['model_file']]='bad'
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'policy.json';path.write_text(json.dumps(policy))
            with patch('turf_lab.available_history_operational.POLICY',path):
                with self.assertRaisesRegex(ValueError,'dependency changed'): verify_active()

    def test_same_day_history_rejected(self):
        row={'race_id':'target','date':'2026-10-31'}
        with self.assertRaisesRegex(ValueError,'precede target'):
            compute([row,{'race_id':'other','date':row['date']}],row)

    def test_comparison_uses_new_primary_not_benchmark(self):
        p=dict(race_id='race',scheduled_start='2020-01-01T15:00:00Z',predicted_at='2020-01-01T12:00:00Z',primary_model='available_history_v3',
            target_snapshot={'participants':[dict(numPmu=1,nom='A',statut='PARTANT'),dict(numPmu=2,nom='B',statut='PARTANT')]},
            models={'v6':dict(probabilities={1:.8,2:.2},version='v6'), 'available_history_v3':dict(probabilities={1:.3,2:.7},version='v3')})
        q=dict(race_id='race',source_evidence='test',operator='test',verified=True,observed_at='2020-01-01T12:01:00Z',odds_format='DECIMAL_TOTAL_RETURN',
            quotes=[dict(number=1,name='A',decimal_odds=2),dict(number=2,name='B',decimal_odds=2)])
        result=compare(p,q)
        self.assertEqual(result['primary_model'],'available_history_v3')
        self.assertEqual(result['rows'][0]['number'],2)
        self.assertFalse(result['recommendations_allowed'])
