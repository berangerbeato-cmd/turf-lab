import gzip
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from urllib.request import Request
from scripts.recover_reference import SafeRedirect
from turf_lab.evidence import EvidenceStore, races
from turf_lab.quality import horse_id


class EvidenceTests(unittest.TestCase):
    def test_geographical_and_discipline_scope(self):
        programme={'programme':{'reunions':[
          {'pays':{'code':'FRA'},'courses':[{'discipline':'ATTELE'},{'discipline':'MONTE'}]},
          {'pays':{'code':'BEL'},'courses':[{'discipline':'ATTELE'}]},
          {'courses':[{'discipline':'ATTELE'}]}]}}
        self.assertEqual(len(list(races(programme))),1)

    def test_resume_checks_integrity_without_network(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw=b'{"ok":true}';root=Path(tmp)
            (root/'sample.json.gz').write_bytes(gzip.compress(raw,mtime=0))
            (root/'manifest.json').write_text(json.dumps({'sample':{'url':'https://example.test/sample','status':200,
              'file':'sample.json.gz','sha256':hashlib.sha256(raw).hexdigest()}}))
            store=EvidenceStore(tmp,max_requests=0)
            self.assertEqual(store.get('https://example.test/sample','sample'),{'ok':True})
            self.assertEqual(store.requests,0)
            (root/'sample.json.gz').write_bytes(gzip.compress(b'{}'))
            with self.assertRaises(ValueError):store.get('https://example.test/sample','sample')

    def test_github_credential_not_forwarded_to_artifact_host(self):
        request=Request('https://api.github.com/repos/a/b/actions/artifacts/1/zip',headers={'Authorization':'Bearer test-placeholder'})
        redirected=SafeRedirect().redirect_request(request,None,302,'Found',{},'https://example.test/signed-download')
        self.assertIsNone(redirected.get_header('Authorization'))

    def test_historical_identity_requires_both_parents(self):
        self.assertEqual(horse_id({'nom':'A','nomMere':'B','nomPere':'C'}),'A-B-C')
        self.assertIsNone(horse_id({'nom':'A','nomMere':'B'}))


if __name__=='__main__':unittest.main()
