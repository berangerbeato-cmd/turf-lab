"""Inventory available source fields without using outcomes to select predictors."""
import gzip
import hashlib
import json
from collections import Counter
from pathlib import Path
from turf_lab.evidence import dump


def main():
    runner_fields = ('driver','entraineur','deferre','ferrure','handicapDistance',
                     'placeCorde','positionDepart','ligneDepart','idCheval')
    race_fields = ('distance','corde','parcours','typePiste','etatPiste','terrain','meteo')
    rows=[]
    for path in sorted(Path('data').glob('month_????-??/manifest.json')):
        manifest=json.loads(path.read_text()); rc=Counter();cc=Counter();values={f:Counter() for f in runner_fields}
        total=0; starts=Counter(); negative_recoil=0;recoils=Counter()
        for entry in manifest['partitions']:
            raw=gzip.decompress(Path(entry['file']).read_bytes())
            if hashlib.sha256(raw).hexdigest()!=entry['sha256']:
                raise ValueError('Digest mismatch: '+entry['race_id'])
            record=json.loads(raw);starts[record['start_type']]+=1
            for f in race_fields:
                cc[f]+=record['course'].get(f) not in (None,'',[],{})
            for runner in record['participants']:
                total+=1
                for f in runner_fields:
                    value=runner.get(f)
                    if value not in (None,'',[],{}):
                        rc[f]+=1;values[f][str(value)]+=1
                distance=runner.get('handicapDistance');base=record['distance_m']
                if isinstance(distance,(int,float)) and isinstance(base,(int,float)):
                    difference=distance-base
                    recoils[str(difference)]+=1;negative_recoil+=difference<0
        rows.append({'month':manifest['month'],'races':len(manifest['partitions']),'participants':total,
                     'runner_nonempty':dict(rc),'race_nonempty':dict(cc),'start_types':dict(starts),
                     'deferre_values':dict(values['deferre']),
                     'handicap_distance_minus_race_distance':dict(recoils),
                     'negative_distance_differences':negative_recoil})
    dump('reports/extension_field_audit.json',{
        'status':'INVENTORY_ONLY_NOT_MODEL_INPUTS','months':rows,
        'limitations':['Retrospective snapshots do not establish original pre-race publication.',
                      'PMU number is not verified autostart position.',
                      'Missing start type is not evidence of a standing start.',
                      'deferre values require semantic validation; absence is not shod.',
                      'Race-level absence does not rule out fields in programme/reunion or other sources.']})
    lines=['# Inventaire des extensions — données conservées','',
           'Inventaire descriptif, sans modification des modèles ni sélection sur les résultats.','',
           '| Mois | Courses | Participants | Driver | Entraîneur | deferre | handicapDistance |',
           '|---|---:|---:|---:|---:|---:|---:|']
    for r in rows:
        lines.append('| '+r['month']+' | '+str(r['races'])+' | '+str(r['participants'])+' | '+
                     ' | '.join(str(r['runner_nonempty'].get(f,0)) for f in ('driver','entraineur','deferre','handicapDistance'))+' |')
    lines+=['','Les nombres sont des champs non vides, pas une preuve de disponibilité historique avant départ.',
            'Le champ ferrure précédemment audité était absent, mais un champ distinct deferre existe : ses valeurs sont conservées dans le JSON pour validation.',
            'Position et ligne autostart : aucune dérivation automatique depuis numPmu.',
            'Distance individuelle : différences avec la distance de course inventoriées, valeurs négatives signalées.',
            'Météo et état de piste : absence éventuelle à ce niveau ne conclut pas sur les réunions ou une source externe.',
            'Prochaine étape : définir un protocole V3 sur train/validation uniquement ; test V2 désormais réservé à son évaluation figée.']
    Path('reports/EXTENSION_FIELD_AUDIT.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps({'races':sum(r['races'] for r in rows),'participants':sum(r['participants'] for r in rows)}))

if __name__=='__main__':main()
