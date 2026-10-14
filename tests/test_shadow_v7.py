import hashlib
import json
import os
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
from scripts.shadow_v7 import capture, verify
from scripts.followup_connections import needs_refresh
from turf_lab.evidence import dump


class V7ShadowTests(unittest.TestCase):
    def test_freeze_and_tamper(self):
        lock, _, models = verify()
        self.assertEqual(set(models), {'v6','v7_speed'})
        self.assertFalse(lock['promotion'])
        with patch('scripts.shadow_v7.digest', return_value='changed'):
            with self.assertRaisesRegex(ValueError,'frozen model'):
                verify()

    def test_capture_immutable_and_baseline_checked(self):
        old=Path.cwd()
        with tempfile.TemporaryDirectory() as folder:
            try:
                os.chdir(folder)
                v5=Path('predictions_v5/2099-01-01/race/prediction.json')
                v6=Path('predictions_v6/2099-01-01/race/prediction.json')
                model={'probabilities':{'1':.7,'2':.3}}
                source={'scheduled_start':'2099-01-01T12:00:00+00:00','history_sha256':hashlib.sha256(b'[]').hexdigest(),
                    'target_snapshot':{},'models':{'v6':model}}
                dump(v6,source)
                before=v6.read_bytes()
                with patch('scripts.shadow_v7.compute',return_value=({}, {'v6':model,'v7_speed':model})):
                    path=capture([],v5)
                    result=json.loads(Path(path).read_text())
                    self.assertTrue(result['experimental'])
                    self.assertFalse(result['promoted'])
                    self.assertEqual(before,v6.read_bytes())
                    with self.assertRaisesRegex(ValueError,'immutable'):
                        capture([],v5)
                with patch('scripts.shadow_v7.compute',return_value=({}, {'v6':{'probabilities':{'1':.5,'2':.5}}})):
                    with self.assertRaisesRegex(ValueError,'reproduction failed'):
                        capture([],v5)
                source['scheduled_start']='2000-01-01T12:00:00+00:00'
                dump(v6,source)
                with self.assertRaisesRegex(ValueError,'after start'):
                    capture([],v5)
            finally:
                os.chdir(old)

    def test_missing_v7_refresh_only_before_start(self):
        snapshots={'race':[{'scheduled_start':'2026-10-14T12:00:00+00:00',
            'predicted_at':'2026-10-14T06:00:00+00:00','history_gap_days':0}]}
        before=datetime(2026,10,14,7,tzinfo=timezone.utc)
        after=datetime(2026,10,14,13,tzinfo=timezone.utc)
        self.assertFalse(needs_refresh(snapshots,before,'2026-10-14'))
        self.assertTrue(needs_refresh(snapshots,before,'2026-10-14',True))
        self.assertFalse(needs_refresh(snapshots,after,'2026-10-14',True))
