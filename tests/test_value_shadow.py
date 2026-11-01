import unittest
from datetime import datetime,timezone,timedelta
from unittest.mock import patch
from turf_lab.value_shadow import shadow
from pathlib import Path
import json

class ShadowValueTests(unittest.TestCase):
 def fixture(self):
  now=datetime.now(timezone.utc);active=json.loads(Path('config/active_model.json').read_text())
  t=json.loads(Path(active['selection_file']).read_text())['temperatures'][active['variant']]
  p=dict(primary_model='available_history_v3',scheduled_start=(now+timedelta(minutes=4)).isoformat(),
   target_snapshot={'participants':[dict(numPmu=n,statut='PARTANT') for n in [1,2]]},
   models={'available_history_v3':dict(model_sha256=active['files_sha256'][active['model_file']],temperature=t)})
  q=dict(observed_at=now.isoformat(),operator='TEST',source_evidence='fixture')
  rows=[dict(number=n,odds=1.9,models={'available_history_v3':{'probability':v}}) for n,v in [(1,.6),(2,.4)]]
  return p,q,rows,now
 def test_complete_board(self):
  result=shadow(*self.fixture())
  self.assertEqual(result['status'],'PRESTART_SHADOW')
  self.assertAlmostEqual(sum(r['probability'] for r in result['rows']),1)
  self.assertFalse(result['recommendations_allowed'])
 def test_incomplete_board(self):
  p,q,r,n=self.fixture()
  self.assertEqual(shadow(p,q,r[:1],n)['status'],'UNAVAILABLE')
 def test_late_calculation_not_prospective(self):
  p,q,r,n=self.fixture()
  self.assertEqual(shadow(p,q,r,n+timedelta(minutes=5))['status'],'RETROSPECTIVE_REPLAY_NOT_PROSPECTIVE')
 def test_stale_and_wrong_model(self):
  p,q,r,n=self.fixture();q['observed_at']=(n-timedelta(minutes=6)).isoformat()
  self.assertEqual(shadow(p,q,r,n)['status'],'UNAVAILABLE')
  p,q,r,n=self.fixture();p['models']['available_history_v3']['model_sha256']='wrong'
  self.assertEqual(shadow(p,q,r,n)['status'],'UNAVAILABLE')
