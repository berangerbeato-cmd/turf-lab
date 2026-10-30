"""Execute a strictly market-free, separately labeled historical sensitivity."""
import json,hashlib
from pathlib import Path
from turf_lab.sport_history_repair import sensitivity
from turf_lab.evidence import dump

def main():
    source=Path('predictions_operational/2026-10-29/2026-10-29_R4C8_20261029T183552548416Z/prediction.json')
    p=json.loads(source.read_text());checks=json.loads(Path('reports/market_repair_v1/individual_history_case.json').read_text())
    out={'race_id':p['race_id'],'status':'RETROSPECTIVE_SENSITIVITY_NOT_VALIDATION','models':{},'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest()}
    for key,m in p['models'].items():
        path=Path(m['model_file'])
        if hashlib.sha256(path.read_bytes()).hexdigest()!=m['model_sha256']:raise ValueError('Model hash mismatch')
        model=json.loads(path.read_text())
        if key=='v6':model=model['models']['combined']
        out['models'][key]=sensitivity(m,checks,model)
    out['training_status']='BLOCKED_NO_REPRESENTATIVE_ENRICHED_TRAIN_AND_TEST_DATA'
    out['training_reason']='Twelve individual histories collected retrospectively for one selected race cannot train or validate a general model.'
    dump('reports/market_repair_v1/sport_sensitivity.json',out)
    print({k:{n:round(v,4) for n,v in m['probabilities'].items() if n in (2,3,10)} for k,m in out['models'].items()})
if __name__=='__main__':main()
