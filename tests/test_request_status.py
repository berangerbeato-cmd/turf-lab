import json, tempfile, os, unittest
from pathlib import Path
from unittest.mock import patch
from scripts.run_prediction_request import main

class RequestStatus(unittest.TestCase):
 def test_failure_cannot_be_reported_as_previous_success(self):
  with tempfile.TemporaryDirectory() as directory:
   old=os.getcwd()
   try:
    os.chdir(directory);Path('config').mkdir()
    Path('config/prediction_request.json').write_text(json.dumps({'date':'2026-10-17','reunion':5,'course':1,'request_id':'new-request'}))
    with patch.dict(os.environ,{'RACE_DATE':'','RACE_MEETING':'','RACE_NUMBER':''}),patch('scripts.predict_operational.run',side_effect=ValueError('source unavailable')):
     with self.assertRaises(ValueError):main()
    state=json.loads(Path('reports/operational/request_status.json').read_text())
    self.assertEqual(state['request_id'],'new-request');self.assertEqual(state['status'],'FAILED')
    self.assertEqual(state['error'],'source unavailable')
   finally:os.chdir(old)
