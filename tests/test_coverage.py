import gzip
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from turf_lab.coverage import cancelled_evidence, coverage_counts

class CoverageTests(unittest.TestCase):
    def test_only_explicit_noncontradictory_cancellation_is_excluded(self):
        cases = [({'statut':'COURSE_ANNULEE','categorieStatut':'ANNULEE'},1),
                 ({'statut':'PROGRAMMEE','categorieStatut':'A_PARTIR'},0),
                 ({'statut':'COURSE_ANNULEE'},0),
                 ({'statut':'COURSE_ANNULEE','categorieStatut':'ANNULEE','ordreArrivee':[[1]]},0)]
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); folder=root/'month_2026-01';folder.mkdir()
            for detail, expected in cases:
                raw=json.dumps(detail).encode()
                (folder/'detail.gz').write_bytes(gzip.compress(raw))
                (folder/'manifest.json').write_text(json.dumps({'race_course_detail':{
                    'status':200,'file':'detail.gz','sha256':hashlib.sha256(raw).hexdigest()}}))
                self.assertEqual(len(cancelled_evidence('2026-01',[{'race_id':'race'}],root)),expected)
            (folder/'detail.gz').write_bytes(gzip.compress(b'{}'))
            with self.assertRaisesRegex(ValueError,'digest mismatch'):
                cancelled_evidence('2026-01',[{'race_id':'race'}],root)

    def test_unresolved_remains_in_denominator(self):
        m={'candidate_races':3,'partitions':[{'race_id':'a'}],
           'quarantine':[{'race_id':'b'},{'race_id':'c'}]}
        result=coverage_counts(m,[{'race_id':'b'}])
        self.assertEqual(result['fraction'],0.5)
        self.assertEqual(result['unresolved'],1)
        with self.assertRaisesRegex(ValueError,'accounting'):
            coverage_counts(m,[{'race_id':'a'}])
