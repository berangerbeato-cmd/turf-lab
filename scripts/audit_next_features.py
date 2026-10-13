"""Availability audit only: 2024/25 development, no new model selection."""
import gzip
import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from itertools import groupby
from pathlib import Path
from scripts.backtest_connections import PROTOCOL, verify_frozen
from scripts.backtest_extension import load_sources
from turf_lab.connections import entity
from turf_lab.month_history import identity
from turf_lab.opposition import is_dq
from turf_lab.evidence import dump, races


def positive(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0


def ceiling(conditions):
    text = str(conditions or '').lower().replace('’', "'").replace('\u00a0', ' ')
    matches = re.findall(r"n'ayant pas gagné\s+(\d+(?:[ .]\d{3})*)(?=[.,\s]|$)", text)
    # A narrow diagnostic parser, not an assertion of complete eligibility rules.
    return int(re.sub(r'[ .]', '', matches[0])) if len(matches) == 1 else None


def timed(p):
    return (p.get('statut') != 'NON_PARTANT' and not is_dq(p)
            and isinstance(p.get('ordreArrivee'), int) and p['ordreArrivee'] > 0
            and positive(p.get('reductionKilometrique')))


def audit(records, ranges):
    speed = defaultdict(list)
    pairs = defaultdict(list)
    seen_horse = defaultdict(list)
    stats = Counter()
    sexes = Counter()
    ages = Counter()
    raw_fields = Counter()
    months = defaultdict(Counter)
    source_hash = hashlib.sha256(json.dumps(records, sort_keys=True).encode()).hexdigest()
    for day, group in groupby(sorted(records, key=lambda r: (r['date'], r['race_id'])), key=lambda r: r['date']):
        batch = list(group)
        cutoff = (date.fromisoformat(day) - timedelta(days=60)).isoformat()
        selected = any(bounds['from'] <= day <= bounds['to'] for bounds in ranges)
        if selected:
            for race in batch:
                active = [p for p in race['participants'] if p.get('statut') != 'NON_PARTANT']
                stats['races'] += 1
                months[day[:7]]['races'] += 1
                age_values = {p.get('age') for p in active if positive(p.get('age'))}
                sex_values = {p.get('sexe') for p in active if p.get('sexe') in ('MALES', 'FEMELLES', 'HONGRES')}
                stats['races_age_varies'] += len(age_values) > 1
                stats['races_sex_varies'] += len(sex_values) > 1
                cap = ceiling(race['course'].get('conditions'))
                stats['races_simple_gain_ceiling'] += cap is not None
                for p in active:
                    stats['runners'] += 1
                    months[day[:7]]['runners'] += 1
                    ages[str(p.get('age'))] += 1
                    sexes[str(p.get('sexe'))] += 1
                    for field in ('age', 'sexe', 'driver', 'engagement', 'driverChange', 'reductionKilometrique', 'tempsObtenu'):
                        raw_fields[field] += field in p and p[field] not in (None, '')
                    stats['age_valid'] += positive(p.get('age'))
                    stats['sex_valid'] += p.get('sexe') in ('MALES', 'FEMELLES', 'HONGRES')
                    stats['engagement_true'] += p.get('engagement') is True
                    stats['career_gains_numeric'] += positive((p.get('gainsParticipant') or {}).get('gainsCarriere'))
                    gains = (p.get('gainsParticipant') or {}).get('gainsCarriere')
                    stats['career_gains_zero'] += gains == 0 and not isinstance(gains, bool)
                    stats['career_gains_invalid'] += not (positive(gains) or (gains == 0 and not isinstance(gains, bool)))
                    key = identity(p)
                    driver = entity(p.get('driver'))
                    prior_speed = [d for d in speed[key] if cutoff <= d < day]
                    prior_pair = [d for d in pairs[(key, driver)] if cutoff <= d < day] if driver else []
                    prior_horse = [(d, who) for d, who in seen_horse[key] if cutoff <= d < day]
                    for name, value in [('past_chrono_one', len(prior_speed) >= 1),
                                        ('past_chrono_three', len(prior_speed) >= 3),
                                        ('past_pair_one', len(prior_pair) >= 1),
                                        ('past_pair_three', len(prior_pair) >= 3),
                                        ('last_driver_known', bool(prior_horse) and driver is not None and prior_horse[-1][1] is not None)]:
                        stats[name] += value
                        months[day[:7]][name] += value
                    if timed(p):
                        stats['classified_chrono'] += 1
                        distance = p.get('handicapDistance') or race.get('distance_m')
                        if positive(p.get('tempsObtenu')) and positive(distance):
                            stats['chrono_joint_check'] += 1
                            ratio = p['reductionKilometrique'] / (p['tempsObtenu'] * 1000 / distance)
                            stats['chrono_joint_within_one_percent'] += abs(ratio - 1) <= .01
        # Day-batched updates prevent current race and same-day leakage.
        for race in batch:
            for p in race['participants']:
                if p.get('statut') == 'NON_PARTANT':
                    continue
                key = identity(p)
                driver = entity(p.get('driver'))
                if timed(p):
                    speed[key].append(day)
                if driver:
                    pairs[(key, driver)].append(day)
                seen_horse[key].append((day, driver))
    return {'source_races': len(records), 'source_sha256': source_hash, 'evaluated': dict(stats),
            'by_month': dict(months), 'raw_field_presence': dict(raw_fields), 'ages': dict(ages), 'sexes': dict(sexes)}


def prospective_availability(folder):
    manifest = json.loads((folder / 'manifest.json').read_text())
    def read(key):
        meta = manifest[key]
        raw = gzip.decompress((folder / meta['file']).read_bytes())
        if meta['status'] != 200 or hashlib.sha256(raw).hexdigest() != meta['sha256']:
            raise ValueError('Prospective evidence mismatch')
        return json.loads(raw), datetime.fromisoformat(meta['fetched_at_utc']).timestamp()
    programme_key = next(k for k in manifest if k.endswith('_programme'))
    programme, programme_time = read(programme_key)
    day = programme_key[:10]
    counts = Counter()
    for meeting, course in races(programme):
        key = f"{day}_R{meeting['numOfficiel']}C{course['numOrdre']}_participants"
        if key not in manifest:
            continue
        data, fetched = read(key)
        if max(programme_time, fetched) >= course['heureDepart'] / 1000:
            raise ValueError('Snapshot not before departure')
        counts['races'] += 1
        counts['races_simple_gain_ceiling'] += ceiling(course.get('conditions')) is not None
        for p in data['participants']:
            if p.get('statut') != 'PARTANT':
                continue
            counts['runners'] += 1
            counts['age_valid'] += positive(p.get('age'))
            counts['sex_valid'] += p.get('sexe') in ('MALES', 'FEMELLES', 'HONGRES')
            counts['driver_known'] += entity(p.get('driver')) is not None
            counts['career_gains_numeric'] += positive((p.get('gainsParticipant') or {}).get('gainsCarriere'))
            counts['current_chrono_positive'] += positive(p.get('reductionKilometrique'))
    return {'evidence_folder': str(folder), 'counts': dict(counts),
            'limit': 'Current field availability only; does not prove original historical publication or historical gains timing.'}


def main():
    p = json.loads(PROTOCOL.read_text())
    verify_frozen(p)
    if any(m.startswith('2026') for m in p['development_months']):
        raise ValueError('Test outcomes forbidden in feature audit')
    records, _ = load_sources({'months': p['development_months'], 'minimum_retained_fraction_per_month': .98})
    result = audit(records, [p['train'], p['validation']])
    result['prospective'] = prospective_availability(Path('evidence/v5_shadow/20261013T185651800684Z'))
    result.update(status='AVAILABILITY_ONLY_NO_BET', new_model_fitted=False,
                  historical_2026_outcomes_loaded=False, raw_inputs_changed=False)
    dump('reports/next_features_audit.json', result)
    s = result['evaluated']
    def rate(key, denominator='runners'):
        return f"{s.get(key, 0)}/{s[denominator]} ({s.get(key, 0)/s[denominator]:.1%})"
    lines = ['# Audit des prochaines variables', '',
        f"Sources : {result['source_races']} courses de janvier–mai 2024/2025. Mesures sur {s['races']} courses et {s['runners']} participations actives de mars–mai. Historique strictement antérieur, fenêtre 60 jours.",
        '', '| Contrôle | Couverture |', '|---|---:|',
        '| Âge présent et positif | '+rate('age_valid')+' |',
        '| Sexe reconnu | '+rate('sex_valid')+' |',
        '| Courses avec des âges différents | '+rate('races_age_varies', 'races')+' |',
        '| Courses avec des sexes différents | '+rate('races_sex_varies', 'races')+' |',
        '| Gains carrière positifs | '+rate('career_gains_numeric')+' |',
        '| Gains carrière égaux à zéro (pas nécessairement absents) | '+rate('career_gains_zero')+' |',
        '| Gains carrière absents ou invalides | '+rate('career_gains_invalid')+' |',
        '| Plafond de gains reconnu par expression stricte | '+rate('races_simple_gain_ceiling', 'races')+' |',
        '| Champ engagement = vrai | '+rate('engagement_true')+' |',
        '| Au moins un chrono antérieur exploitable | '+rate('past_chrono_one')+' |',
        '| Au moins trois chronos antérieurs | '+rate('past_chrono_three')+' |',
        '| Au moins une sortie du même tandem | '+rate('past_pair_one')+' |',
        '| Au moins trois sorties du même tandem | '+rate('past_pair_three')+' |',
        '', '## Contrôles et décisions', '',
        f"Chronos de chevaux classés avec temps et distance : {s.get('chrono_joint_within_one_percent', 0)}/{s.get('chrono_joint_check', 0)} concordent à 1 % avec temps × 1000 / distance. Cohérence empirique, pas preuve de comparabilité entre hippodromes.",
        '- Âge/sexe : candidats à tester. Un effet identique à tous les chevaux de la course ne les départage pas ; contrôler la variation intra-course.',
        '- Engagement : le booléen PMU est presque toujours faux. Le plafond textuel ne suffit pas : conditions annexes, recul et temporalité des gains restent à valider. Aucune conversion monétaire ou variable de ratio encore adoptée.',
        '- Chronos : utiliser seulement les courses antérieures classées. Corriger le contexte sans données futures ; ne jamais utiliser le chrono de la course cible. Aucun chrono corrigé encore implémenté.',
        '- Tandem : compter les sorties communes et régulariser fortement les petits effectifs ; noms de drivers potentiellement ambigus. Couverture ne signifie pas gain prédictif.',
        '', '## Vérification avant-course', '',
        json.dumps(result['prospective'], ensure_ascii=False), '',
        'Les captures du 14 octobre servent uniquement à vérifier la présence des champs avant départ. Aucun résultat 2026 chargé pour cet audit.',
        '', '## Prochain essai proposé, non exécuté', '',
        'Comparer V5 inchangé à V5 + âge/sexe, puis V5 + tandem, puis leur combinaison sur les données de développement. Ne pas retoucher V5 ni sélectionner avec mai–juin 2026.',
        'Un protocole spécifique doit être figé avant calcul. Validation déjà consultée : résultats exploratoires. Réserver une nouvelle période indépendante avant toute conclusion de gain.',
        'Différer les gains/engagement jusqu’à validation des unités et de leur temporalité ; différer les chronos corrigés jusqu’à définition et vérification de la normalisation.',
        'Aucun modèle nouveau entraîné. Aucun changement aux prédictions V5. Aucun pari.']
    Path('reports/NEXT_FEATURES_AUDIT.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps({'evaluated': s, 'prospective': result['prospective']}, ensure_ascii=False))


if __name__ == '__main__':
    main()
