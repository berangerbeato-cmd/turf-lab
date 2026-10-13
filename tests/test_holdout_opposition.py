import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from scripts.holdout_opposition import checked_json

class HoldoutOppositionTests(unittest.TestCase):
    def test_frozen_model_tampering_blocks_evaluation(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'model.json';p.write_bytes(b'{"weights":[1]}')
            digest=hashlib.sha256(p.read_bytes()).hexdigest()
            self.assertEqual(checked_json(p,digest)['weights'],[1])
            p.write_bytes(b'{"weights":[2]}')
            with self.assertRaisesRegex(ValueError,'Frozen file mismatch'):checked_json(p,digest)

    def test_holdout_is_disjoint_and_chosen_before_collection(self):
        p=json.loads(Path('config/opposition_v3_holdout.json').read_text())
        earlier=json.loads(Path('config/history_extension_protocol.json').read_text())
        self.assertGreater(p['test_from'],earlier['test']['to'])
        self.assertTrue(p['no_refit']);self.assertTrue(p['no_prospective_replacement'])
        checked_json(p['models_file'],p['models_sha256'])
        checked_json('config/opposition_v3_protocol.json',p['feature_protocol_sha256'])
