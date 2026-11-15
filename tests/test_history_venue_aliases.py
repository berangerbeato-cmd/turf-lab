import gzip,json,unittest
from pathlib import Path
from turf_lab.individual_history_check import reconcile,venue_key

class VenueAliases(unittest.TestCase):
    def test_exact_aliases(self):
        for a,b in [('PARIS-VINCENNES','VINCENNES'),('TOULOUSE','LA CEPIERE'),('MARSEILLE-BORELY','BORELY'),('BORDEAUX-LE BOUSCAT','LE BOUSCAT'),('LE CROISE-LAROCHE','LE CROISE LAROCHE')]:self.assertEqual(venue_key(a),venue_key(b))
        self.assertNotEqual(venue_key('MARSEILLE VIVAUX'),venue_key('MARSEILLE BORELY'))
    def fixture(self):
        root=Path('predictions_operational/2026-11-15/2026-11-15_R3C5_20261115T115929320844Z')
        p=json.loads((root/'prediction.json').read_text())
        runner=next(r for r in p['target_snapshot']['participants'] if r['numPmu']==10)
        frame=next(r for r in p['models']['v6']['runners'] if r['number']==10)
        payload=json.loads(gzip.decompress((root/'individual_history_evidence/horse_10.json.gz').read_bytes()))
        return runner,frame,payload
    def test_two_dqs_already_present_no_duplicates(self):
        r,f,p=self.fixture();out=reconcile(r,f,p,'2026-11-15')
        self.assertEqual(out['status'],'NO_DISCREPANCY_IN_RETURNED_WINDOW')
        self.assertEqual(out['supplemented_recent_features_for_research'],f['features'][:5])
    def test_conflict_not_hidden_by_alias(self):
        r,f,p=self.fixture();f['history'][0]['dq']=False
        self.assertEqual(reconcile(r,f,p,'2026-11-15')['status'],'CONFLICT')
    def test_different_race_number_not_merged(self):
        r,f,p=self.fixture();f['history'][0]['race_id']='2026-10-21_R1C99'
        self.assertEqual(len(reconcile(r,f,p,'2026-11-15')['missing_recent_starts']),1)
