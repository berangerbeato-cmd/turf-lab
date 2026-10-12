"""Quality diagnostics over historical evidence; no training or imputation."""
import collections
import statistics


def horse_id(runner):
    """Exact official composite, also usable when older archives lack idCheval."""
    if runner.get('idCheval'):
        return runner['idCheval']
    parts=[runner.get(k) for k in ('nom','nomMere','nomPere')]
    return '-'.join(parts) if all(isinstance(p,str) and p.strip() for p in parts) else None


def assess(records):
    issues=[];warnings=[];counts=collections.Counter();time_errors=[];runner_count=0
    for race in records:
        runners=race['participants'];runner_count+=len(runners)
        numbers=[r.get('numPmu') for r in runners]
        ids=[horse_id(r) for r in runners]
        if len(numbers)!=len(set(numbers)):issues.append({'race_id':race['race_id'],'issue':'duplicate_runner_number'})
        if None in ids or len(ids)!=len(set(ids)):issues.append({'race_id':race['race_id'],'issue':'missing_or_duplicate_horse_identity'})
        detail=race.get('detail') or {}
        expected=race['course'].get('nombreDeclaresPartants')
        if expected is not None and expected!=len(runners):
            issues.append({'race_id':race['race_id'],'issue':'declared_count_mismatch','expected':expected,'observed':len(runners)})
        winners=sorted(r['numPmu'] for r in runners if r.get('ordreArrivee')==1)
        arrival=detail.get('ordreArrivee') or []
        detail_winners=sorted(arrival[0]) if arrival and isinstance(arrival[0],list) else None
        if detail_winners is None or winners!=detail_winners:
            issues.append({'race_id':race['race_id'],'issue':'winner_disagreement','participants':winners,'detail':detail_winners})
        if not (detail.get('arriveeDefinitive') or detail.get('isArriveeDefinitive')):
            issues.append({'race_id':race['race_id'],'issue':'result_not_definitive'})
        counts['single_winner_races']+=len(winners)==1
        counts['dead_heat_races']+=len(winners)>1
        for r in runners:
            incident=r.get('incident')
            dq=str(incident or '').startswith('DISQUALIFIE') or incident=='DISTANCE'
            np=r.get('statut')=='NON_PARTANT'
            counts['disqualified']+=dq;counts['non_runners']+=np
            counts['distanced']+=incident=='DISTANCE'
            counts['stopped']+=incident=='ARRETE'
            counts['composite_id_reconstructed']+=not bool(r.get('idCheval')) and horse_id(r) is not None
            counts['missing_rank_without_dq_or_np']+=r.get('ordreArrivee') is None and not dq and not np
            if r.get('ordreArrivee') is None and not incident and not np:
                warnings.append({'race_id':race['race_id'],'number':r['numPmu'],'issue':'unclassified_finisher_without_incident'})
            if dq and r.get('ordreArrivee')==1:
                issues.append({'race_id':race['race_id'],'issue':'disqualified_winner','number':r['numPmu']})
            # Check the hypothesized millisecond units against the travelled distance.
            if all(isinstance(r.get(k),(int,float)) and r[k]>0 for k in ('tempsObtenu','reductionKilometrique','handicapDistance')):
                error=abs(r['tempsObtenu']/1000-r['reductionKilometrique']/1000*r['handicapDistance']/1000)
                time_errors.append(error)
    return {'races':len(records),'participants_including_non_runners':runner_count,'counts':dict(counts),
            'issues':issues,'warnings':warnings,
            'status':'REVIEW_REQUIRED' if issues else ('PASS_WIN_LABELS_WITH_WARNINGS' if warnings else 'PASS'),
            'time_unit_check':{'n':len(time_errors),'hypothesis':'tempsObtenu and reductionKilometrique in milliseconds',
              'median_absolute_error_seconds':statistics.median(time_errors) if time_errors else None,
              'max_absolute_error_seconds':max(time_errors) if time_errors else None}}
