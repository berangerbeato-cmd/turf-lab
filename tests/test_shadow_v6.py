import hashlib
import json
import os
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch
from turf_lab.evidence import dump
from turf_lab.shadow_v5_score import score
from scripts.shadow_v6 import capture
from tests.test_shadow_v5_score import fixture


class V6ShadowTests(unittest.TestCase):
    def setUp(self):
        self.old = Path.cwd()
        self.temp = tempfile.TemporaryDirectory()
        os.chdir(self.temp.name)
        self.path = Path('predictions_v5/2099-01-01/race/prediction.json')
        self.source, _, _ = fixture()
        self.source.update(scheduled_start='2099-01-01T12:00:00+00:00',
            history_sha256=hashlib.sha256(b'[]').hexdigest())
        dump(self.path, self.source)
        self.models = {'v5': deepcopy(self.source['models']['combined']),
                       'v6': deepcopy(self.source['models']['v3'])}

    def tearDown(self):
        os.chdir(self.old)
        self.temp.cleanup()

    def test_sidecar_does_not_change_source_and_is_immutable(self):
        before = self.path.read_bytes()
        with patch('scripts.shadow_v6.compute', return_value=({'lock': True}, self.models)):
            target = capture([], self.path)
            result = json.loads(Path(target).read_text())
            self.assertEqual(set(result['models']), {'v5', 'v6'})
            self.assertEqual(result['v5_snapshot_sha256'], hashlib.sha256(before).hexdigest())
            self.assertEqual(self.path.read_bytes(), before)
            with self.assertRaisesRegex(ValueError, 'immutable'):
                capture([], self.path)

    def test_history_or_baseline_mismatch_rejected(self):
        with self.assertRaisesRegex(ValueError, 'history mismatch'):
            capture([{'date': '2026-01-01'}], self.path)
        self.models['v5']['probabilities']['1'] = .5
        with patch('scripts.shadow_v6.compute', return_value=({}, self.models)):
            with self.assertRaisesRegex(ValueError, 'reproduction failed'):
                capture([], self.path)

    def test_late_capture_rejected_before_compute(self):
        self.source['scheduled_start'] = '2000-01-01T12:00:00+00:00'
        dump(self.path, self.source)
        with patch('scripts.shadow_v6.compute') as compute:
            with self.assertRaisesRegex(ValueError, 'after start'):
                capture([], self.path)
            compute.assert_not_called()

    def test_v6_paired_scoring_and_field_changes(self):
        p,d,r = fixture()
        p['models'] = self.models
        p['frozen'] = {'lock': True}
        self.assertEqual(score(p,d,r, ['v5','v6'])['status'], 'SCORED')
        r[0]['age'] = 7
        self.assertEqual(score(p,d,r, ['v5','v6'])['reason'], 'age_or_sex_changed')
        del r[0]['age']
        r[0]['driver'] = 'CHANGED'
        self.assertEqual(score(p,d,r, ['v5','v6'])['status'], 'QUARANTINE')
