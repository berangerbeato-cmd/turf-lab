import gzip
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch
from urllib.error import URLError

from scripts.backfill_history import StopOnUnavailable
from turf_lab.evidence import dump


class RecoveryTests(unittest.TestCase):
    def store(self, root, status='error', error='Connection reset by peer', minutes=30):
        store = StopOnUnavailable(root, max_requests=2, delay=0)
        store.manifest['day'] = {'url': 'https://example.test', 'status': status,
            'error': error, 'fetched_at_utc': (datetime.now(timezone.utc) -
                timedelta(minutes=minutes)).isoformat()}
        dump(store.manifest_path, store.manifest)
        return store

    def test_delayed_recovery_preserves_original_and_uses_digest_cache(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = self.store(Path(tmp))
            original = dict(store.manifest['day'])
            raw = b'original response bytes'
            (Path(tmp) / 'original.gz').write_bytes(gzip.compress(raw))
            original['file'] = 'original.gz'
            store.manifest['day'] = original
            response = MagicMock(status=200)
            response.read.return_value = b'{"recovered": true}'
            response.headers.get.return_value = None
            response.__enter__.return_value = response
            with patch('turf_lab.evidence.urlopen', return_value=response) as request:
                self.assertEqual(store.get('https://example.test', 'day'), {'recovered': True})
                request.assert_called_once()
            self.assertEqual(store.requests, 1)
            self.assertEqual(store.manifest['day']['previous_attempts'], [original])
            self.assertEqual(gzip.decompress((Path(tmp) / 'original.gz').read_bytes()), raw)
            with patch('turf_lab.evidence.urlopen', side_effect=AssertionError('network')):
                resumed = StopOnUnavailable(Path(tmp), delay=0)
                self.assertEqual(resumed.get('https://example.test', 'day'), {'recovered': True})
                self.assertEqual(resumed.requests, 0)

    def test_empty_response_gets_one_delayed_recovery(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = self.store(Path(tmp), error='Expecting value: line 1 column 1 (char 0)')
            response = MagicMock(status=200)
            response.read.return_value = b'{"programme": {}}'
            response.headers.get.return_value = None
            response.__enter__.return_value = response
            with patch('turf_lab.evidence.urlopen', return_value=response) as request:
                self.assertEqual(store.get('https://example.test', 'day'), {'programme': {}})
                request.assert_called_once()
            self.assertEqual(len(store.manifest['day']['previous_attempts']), 1)

    def test_nonempty_invalid_json_is_not_retried(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = self.store(Path(tmp), error='Expecting value: line 1 column 1 (char 0)')
            store.manifest['day']['file'] = 'invalid.json.gz'
            with patch('turf_lab.evidence.urlopen', side_effect=AssertionError('network')):
                with self.assertRaises(RuntimeError): store.get('https://example.test', 'day')
            self.assertEqual(store.requests, 0)

    def test_failed_recovery_is_not_retried_across_runs(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = self.store(Path(tmp))
            original = dict(store.manifest['day'])
            with patch('turf_lab.evidence.urlopen', side_effect=URLError('timed out')) as request:
                with self.assertRaises(RuntimeError): store.get('https://example.test', 'day')
                resumed = StopOnUnavailable(Path(tmp), delay=0)
                with self.assertRaises(RuntimeError): resumed.get('https://example.test', 'day')
                request.assert_called_once()
            self.assertEqual(resumed.manifest['day'], original)
            self.assertTrue((Path(tmp) / 'recovery/day/manifest.json').exists())

    def test_no_retry_for_denial_rate_limit_recent_or_invalid_payload(self):
        for status, error, minutes in [(403, '', 30), (429, '', 30),
                ('error', 'timed out', 1), ('error', 'Invalid JSON', 30)]:
            with self.subTest(status=status, error=error), tempfile.TemporaryDirectory() as tmp:
                store = self.store(Path(tmp), status, error, minutes)
                with patch('turf_lab.evidence.urlopen', side_effect=AssertionError('network')):
                    with self.assertRaises(RuntimeError): store.get('https://example.test', 'day')
                self.assertEqual(store.requests, 0)

    def test_url_mismatch_and_exhausted_budget_never_fetch(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = self.store(Path(tmp))
            with self.assertRaises(ValueError): store.get('https://different.test', 'day')
            store.requests = store.max_requests
            with patch('turf_lab.evidence.urlopen', side_effect=AssertionError('network')):
                with self.assertRaises(RuntimeError): store.get('https://example.test', 'day')
