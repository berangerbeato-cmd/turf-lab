"""Bounded prospective prediction, manual invocation, no odds endpoint."""
import argparse
import hashlib
import html
import json
import re
from datetime import datetime,timezone
from pathlib import Path
from zoneinfo import ZoneInfo
from turf_lab.evidence import EvidenceStore,dump,races,start_type
from turf_lab.pilot import dated_history,features,norm_name,probabilities


def render(prediction):
    start_local=datetime.fromisoformat(prediction['scheduled_start']).astimezone(ZoneInfo('Europe/Paris')).strftime('%d/%m/%Y à %H:%M')
    calculated_local=datetime.fromisoformat(prediction['predicted_at']).astimezone(ZoneInfo('Europe/Paris')).strftime('%d/%m/%Y à %H:%M')
    cards=[]
    active=[r for r in prediction['runners'] if r['status']=='PARTANT']
    for rank,r in enumerate(sorted(active,key=lambda x:(-x['probability'],x['number'])),1):
        h=r['history'];n=len(h);wins=sum(x['rank']==1 for x in h);dq=sum(x['dq'] for x in h)
        description=f'{wins} victoire(s), {dq} disqualification(s) sur {n} sorties attelées disponibles.' if n else 'Historique antérieur indisponible : incertitude renforcée.'
        cards.append(f'<article><b>{rank}. N°{r["number"]} — {html.escape(r["name"])}</b><strong>{r["probability"]:.1%}</strong><p>{description}</p></article>')
    return f'''<!doctype html><html lang="fr"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Turf Lab {prediction['race_id']}</title><style>body{{font:17px system-ui;max-width:680px;margin:auto;padding:20px;background:#f4f6f8;color:#18212b}}article{{padding:16px;margin:12px 0;background:white;border-radius:12px}}strong{{display:block;font-size:26px;color:#12553c}}p{{line-height:1.5}}.alert{{background:#fff1ce;padding:16px;border-radius:12px}}</style><h1>{prediction['race_id']}</h1><p>{html.escape(prediction['venue'])} · {prediction['distance_m']} m · {prediction['start_type']}</p><p>Départ : {start_local} (Paris)<br>Calcul : {calculated_local} (Paris)</p><div class="alert"><b>EXPÉRIMENTAL — NO BET</b><p>Incertitude élevée. Les probabilités ne constituent pas un modèle validé. Aucune cote reçue, aucune EV disponible.</p></div><h2>Classement indicatif</h2>{''.join(cards)}<h2>Lecture prudente</h2><p>Le premier du classement est le favori du modèle. Les chevaux moins bien classés ne sont pas automatiquement des outsiders intéressants : il faut une cote vérifiée et un modèle fiable.</p><p>Scénarios conditionnels : un non-partant impose un nouveau calcul. Une disqualification peut modifier fortement l'arrivée ; l'historique décrit ce risque sans garantir qu'il se reproduira. Aucun déroulement tactique certain n'est prédit.</p><p>Historique limité à cinq sorties antérieures. Les conditions, la ferrure et les tandems ne sont pas encore intégrés au score. Aucun pari réel.</p></html>'''


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--date',required=True);parser.add_argument('--reunion',type=int,required=True);parser.add_argument('--course',type=int,required=True);args=parser.parse_args()
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}',args.date) or not 1<=args.reunion<=30 or not 1<=args.course<=30:raise ValueError('Invalid race parameters')
    day=datetime.fromisoformat(args.date).date();now=datetime.now(timezone.utc)
    if not 0<=(day-now.date()).days<=7:raise ValueError('Only today and next seven days')
    model_file=Path('models/pilot_v1.json');model=json.loads(model_file.read_text())
    batch=now.strftime('%Y%m%dT%H%M%S%fZ');rid=f'{args.date}_R{args.reunion}C{args.course}'
    store=EvidenceStore(f'evidence/predictions/{batch}_{rid}',max_requests=3)
    programme=store.programme(args.date)
    matches=[(r,c) for r,c in races(programme) if r['numOfficiel']==args.reunion and c['numOrdre']==args.course]
    if len(matches)!=1:raise ValueError('French harness race not uniquely found')
    meeting,course=matches[0];start=datetime.fromtimestamp(course['heureDepart']/1000,timezone.utc)
    if now>=start or course.get('arriveeDefinitive'):raise ValueError('Race started or finished')
    raw=store.race(args.date,args.reunion,args.course,'participants')
    if not raw or not raw.get('participants'):raise ValueError('No participants')
    ds=day.strftime('%d%m%Y');key=rid+'_performances_pretty'
    history=store.get(f'https://offline.turfinfo.api.pmu.fr/rest/client/7/programme/{ds}/R{args.reunion}/C{args.course}/performances-detaillees/pretty',key)
    if not history or not history.get('participants'):raise ValueError('History unavailable')
    by_number={h['numPmu']:h for h in history['participants']}
    if len(by_number)!=len(history['participants']):raise ValueError('Duplicate horse history')
    runners=[];ids=set();numbers=set()
    for p in raw['participants']:
        number=p['numPmu'];identity=p.get('idCheval') or '-'.join(p[k] for k in ('nom','nomMere','nomPere'))
        if number in numbers or identity in ids:raise ValueError('Duplicate identity')
        ids.add(identity);numbers.add(number)
        if p.get('statut') not in ('PARTANT','NON_PARTANT'):raise ValueError('Unknown runner status')
        if any(p.get(k) not in (None,'') for k in ('ordreArrivee','tempsObtenu','commentaireApresCourse')):raise ValueError('Post-race information present')
        h=by_number.get(number)
        if h is None and p['statut']=='PARTANT':raise ValueError('History identity missing')
        if h is not None and norm_name(h['nomCheval'])!=norm_name(p['nom']):raise ValueError('History identity mismatch')
        runs=dated_history(h,args.date) if h else []
        runners.append({'number':number,'horse_id':identity,'name':p['nom'],'status':p['statut'],'non_runner':p['statut']=='NON_PARTANT','features':features(runs,args.date),'history':runs})
    predicted=datetime.now(timezone.utc)
    if predicted>=start:raise ValueError('Race started during collection')
    probabilities_by_number=probabilities({'runners':runners},model)
    for r in runners:r['probability']=probabilities_by_number[r['number']]
    prediction={'race_id':rid,'venue':meeting['hippodrome']['libelleCourt'],'distance_m':course['distance'],'start_type':start_type(course),'scheduled_start':start.isoformat(),'predicted_at':predicted.isoformat(),'feature_cutoff':now.isoformat(),'validation_status':'experimental','uncertainty':'high','data_quality_pass':True,'status':'NO BET','model_sha256':hashlib.sha256(model_file.read_bytes()).hexdigest(),'evidence_manifest':str(store.manifest_path),'runners':runners}
    root=Path('predictions')/args.date/f'{rid}_{batch}';root.mkdir(parents=True,exist_ok=True)
    dump(root/'prediction.json',prediction);(root/'index.html').write_text(render(prediction))
    template={'race_id':rid,'source':'PMU_MANUAL_SCREENSHOT','transcription_verified':False,'image_sha256':None,'observed_at':None,'runners_verified_at':None,'odds_format':'DECIMAL_TOTAL_RETURN','quotes':[{'horse_id':r['horse_id'],'number':r['number'],'name':r['name'],'decimal_odds':None} for r in runners if r['status']=='PARTANT']}
    dump(root/'manual_quotes_template.json',template);print(root)

if __name__=='__main__':main()
