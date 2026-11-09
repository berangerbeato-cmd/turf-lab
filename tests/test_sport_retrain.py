import unittest
from turf_lab.sport_retrain import outcome, repaired_features, replace_features


def row(day, rank=None, incident=None):
    return {'date': day, 'race_id': day+'_R1C1', 'rank': rank, 'incident': incident}


class SportingRepairTests(unittest.TestCase):
    def test_unknown_is_not_a_loss_or_non_dq(self):
        f=repaired_features([row('2026-10-01',1),row('2026-10-02')],'2026-10-10')
        self.assertEqual(f[:3],[1,1,0]);self.assertEqual(f[-2],.5)
        self.assertEqual(repaired_features([row('2026-10-02')],'2026-10-10')[:3],[None]*3)

    def test_stopped_fallen_and_dq_are_distinct(self):
        for s in ('ARRETE','TOMBE'):
            self.assertEqual(outcome(None,s),(0,0,0,1))
        self.assertEqual(outcome(None,'DISQUALIFIE_POUR_ALLURE_IRREGULIERE'),(0,0,1,0))
        self.assertIsNone(outcome(1,'ARRETE'))
        self.assertIsNone(outcome(True,None))

    def test_future_and_same_day_rejected(self):
        for day in ('2026-10-10','2026-10-11'):
            with self.assertRaises(ValueError):repaired_features([row(day,1)],'2026-10-10')

    def test_window_and_five_latest(self):
        h=[row('2026-08-01',1)]+[row('2026-10-0'+str(i),2) for i in range(1,7)]
        f=repaired_features(h,'2026-10-10')
        self.assertEqual(f[:3],[0,1,0]);self.assertEqual(f[4],1)
        self.assertEqual(repaired_features([],'2026-10-10'),[None,None,None,None,0,None,None])

    def test_no_mutation_or_market_features(self):
        original=list(range(38));history=[row('2026-10-01',1)]
        new=replace_features(original,history,'2026-10-10')
        self.assertEqual(original,list(range(38)));self.assertEqual(new[5:38],original[5:])
        self.assertEqual(len(new),40)
        history[0]['odds']=999;history[0]['target_win']=False
        self.assertEqual(new,replace_features(original,history,'2026-10-10'))

class RebuildIntegrationTests(unittest.TestCase):
    def test_same_day_results_excluded_and_hashes_checked(self):
        import gzip, hashlib, json, os, tempfile
        from pathlib import Path
        from scripts.retrain_sport_v1 import rebuild
        from turf_lab.month_history import identity
        original=Path.cwd()
        with tempfile.TemporaryDirectory() as folder:
            try:
                os.chdir(folder)
                root=Path('data/month_2026-01');root.mkdir(parents=True)
                horse={'nom':'H','nomMere':'M','nomPere':'P','numPmu':1,'statut':'PARTANT','ordreArrivee':1}
                parts=[];frames=[]
                for i,day in enumerate(['2026-01-01','2026-01-01','2026-01-02']):
                    rid=f'{day}_R1C{i+1}'
                    raw=json.dumps({'date':day,'race_id':rid,'participants':[horse]}).encode()
                    path=root/f'{i}.gz';path.write_bytes(gzip.compress(raw))
                    parts.append({'file':str(path),'sha256':hashlib.sha256(raw).hexdigest()})
                    frames.append({'date':day,'race_id':rid,'runners':[{'number':1,'horse_id':identity(horse),'features':[None]*38}]})
                manifest_path=root/'manifest.json';manifest_path.write_text(json.dumps({'partitions':parts}))
                manifest={'provenance':{'source_manifests':{'2026-01':hashlib.sha256(manifest_path.read_bytes()).hexdigest()}}}
                p={'excluded_months':[],'excluded_races':[]}
                splits,_,_=rebuild({'train':frames},manifest,p)
                self.assertEqual(splits['train'][0]['runners'][0]['features'][:3],[None]*3)
                self.assertEqual(splits['train'][1]['runners'][0]['features'][:3],[None]*3)
                self.assertEqual(splits['train'][2]['runners'][0]['features'][:3],[1,1,0])
                Path(parts[0]['file']).write_bytes(gzip.compress(b'corrupt'))
                with self.assertRaises(ValueError):rebuild({'train':frames},manifest,p)
            finally:os.chdir(original)
