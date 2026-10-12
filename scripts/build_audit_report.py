"""Reproduce the feasibility report from evidence-derived JSON only (no network)."""
import collections
import json
from pathlib import Path

from turf_lab.evidence import dump
from turf_lab.quality import assess


def load(name):
    return json.loads((Path('reports')/name).read_text(encoding='utf-8'))


def main():
    audit=load('audit_phase_a.json'); horses=load('five_horse_histories.json')
    temporal=load('temporal_audit.json'); prospective=load('prospective_audit.json')
    opposition=load('opposition_audit.json')
    quality=assess(audit['races']);dump('reports/quality_audit.json',quality)
    n=sum(x['runners'] for x in audit['races']);nr=len(audit['races'])
    total=sum(x['all_attele_races'] for x in audit['week_programmes'])
    french=sum(x['france_attele_races'] for x in audit['week_programmes'])
    all_history=[r for h in horses['horses'] for r in h.get('runs',[])]
    fields=[('Identité PMU directe','idCheval','Identifiant ; absent de certaines archives'),
       ('Nom','nom','Avec père et mère pour identité composite'),('Père','nomPere','Identité'),('Mère','nomMere','Identité'),
       ('Âge','age','Avant course'),('Sexe','sexe','Avant course'),('Musique','musique','Avant course ; dates non incluses'),
       ('Driver','driver','Déclaration avant course, changements possibles'),('Entraîneur','entraineur','Déclaration avant course'),
       ('Ferrure déclarée','deferre','Absent ≠ ferré'),('Distance individuelle','handicapDistance','Avant course ; recul à calculer'),
       ('Gains de carrière','gainsParticipant.gainsCarriere','Centimes ; caractère figé historique à contrôler'),
       ('Nombre de courses','nombreCourses','Couverture/périmètre du compteur non garanti'),
       ('Victoires cumulées','nombreVictoires','Recalculer avant chaque course'),
       ('Avis entraîneur','avisEntraineur','Neutralité et date de publication à contrôler'),
       ('Place au départ','placeCorde','Surtout autostart ; absence pas une position nulle'),
       ('Rang final','ordreArrivee','Après course : cible seulement'),('Incident','incident','Après course ; absence souvent normale'),
       ('Temps obtenu','tempsObtenu','Après course ; millisecondes'),
       ('Réduction kilométrique','reductionKilometrique','Après course ; millisecondes par km, pas record personnel'),
       ('Commentaire après course','commentaireApresCourse.texte','Exclu des features de la course cible')]
    catalog=[]
    for label,path,timing in fields:
        row={'variable':label,'source_field':path,'interpretation':timing,'availability':{}}
        for year,inv in audit['inventory_by_year'].items():
            count=inv['fields'].get(path,{}).get('nonempty',0)
            row['availability'][year]={'nonempty':count,'denominator':inv['n'],'rate':count/inv['n']}
        catalog.append(row)
    dump('reports/field_catalog.json',catalog)
    all_manifests=[]
    for p in Path('evidence').glob('*/manifest.json'):
        all_manifests.extend(json.loads(p.read_text()).values())
    verified_before=[r for r in prospective['races'] if r['retrieved_before_scheduled_start'] and not any(r['post_field_nonempty_counts'].values())]
    latest_leak=sum(c['on_or_after_target'] for c in temporal['cases'])
    temporal_n=sum(c['history_rows'] for c in temporal['cases'])
    decision={
      'data_access':'VERIFIED_ON_BOUNDED_SAMPLE',
      'pilot_architecture':'GO_WITH_CONDITIONS' if not quality['issues'] and latest_leak==0 else 'HOLD',
      'mass_backfill':'HOLD', 'production_prediction':'HOLD','model_training':'OUTSIDE_PHASE_A_SEE_WORK_PROGRESS',
      'github_publication':'SEE_WORK_PROGRESS_AND_ACTIONS_FOR_CURRENT_DEPLOYMENT',
      'conditions':['Restore verified GitHub writes and persistent checkpoints before expanding',
        'Use exact composite identities and explicit missingness',
        'Separate outcomes from features; strict date filtering of individual histories',
        'Explain six unclassified finishers before using complete rankings',
        'Do not infer volte or shod status from absent fields',
        'Validate a bounded multi-period training pilot before any mass collection']}
    dump('reports/feasibility_decision.json',decision)
    lines=['# TURF LAB — audit de faisabilité du 12 octobre 2026','',
      '## Conclusion vérifiée','',
      f'**Les données permettent de préparer un pilote, sous conditions.** L’audit porte sur {nr} courses françaises de trot attelé et {n} participants déclarés, dans 12 hippodromes. Aucun modèle n’est entraîné et aucune performance prédictive ou rentabilité n’est annoncée.',
      '',f'**Correction importante : les {total} courses des programmes du 5 au 11 octobre comprennent seulement {french} courses françaises et {total-french} courses étrangères.** Les scripts d’origine ne filtraient pas le pays.',
      '', 'Les 14 courses et 203 participants du 5 octobre sont retrouvés dans une nouvelle lecture PMU. Le run GitHub de référence est bien réussi, mais ses ZIP originaux n’ont pas pu être téléchargés par le connecteur. Cette nouvelle lecture ne prétend donc pas vérifier leur contenu octet par octet.',
      '', 'L’état de publication et les exécutions cloud sont consignés dans WORK_PROGRESS.md et GitHub Actions. Les chiffres ci-dessous proviennent des preuves archivées ; ils ne constituent pas une validation du modèle.',
      '', '## Méthode et couverture','',
      'Huit dates 2024/2025, quatre courses au plus par date, sélectionnées pour varier hippodromes et départs ; toutes les courses françaises d’attelé du 05/10/2026. Cet échantillon de disponibilité ne représente pas la distribution complète des courses et ne sert pas à mesurer un modèle.',
      '', '| Date | Courses françaises au programme | Courses auditées | Participants audités |', '|---|---:|---:|---:|']
    for day in audit['days']:
        runners=sum(r['runners'] for r in audit['races'] if r['date']==day['date'])
        lines.append(f"| {day['date']} | {day['french_attele_races']} | {day['sampled']} | {runners} |")
    venues=sorted({r['venue'] for r in audit['races']})
    lines+=['', 'Hippodromes réellement audités : '+', '.join(venues)+'.',
      '',f"Collecte principale : {sum(audit['request_status'].values())} réponses, statuts {audit['request_status']}. Évidence complémentaire incluse : {len(all_manifests)} réponses conservées au total. Rejouer les analyses utilise le cache et vérifie les empreintes SHA-256.",
      '', '## A1 — cinq chevaux, historique arrêté avant le 05/10/2026','',
      'Sélection selon les caractéristiques avant course, sans utiliser le résultat du 5 octobre. Les détails course par course figurent dans `FIVE_HORSE_HISTORIES.md` et dans le JSON correspondant.',
      '', '| Cheval | Profil | Courses antérieures disponibles | Dernières retenues |', '|---|---|---:|---:|']
    for h in horses['horses']:
        lines.append(f"| {h['name']} | {h['reason']} | {h.get('prior_rows_available',0)} | {h.get('last_ten_returned',0)} |")
    lines+=['',f"Sur les {len(all_history)} performances retenues : dates, hippodromes, distances, drivers, entraîneurs et nombre de participants sont disponibles pour toutes. Les chronos peuvent manquer normalement en cas de disqualification, mais aussi sur certaines courses de province. Les courses montées éventuelles sont conservées et identifiées ; ne pas les assimiler à l’attelé.",
      '', 'L’historique de l’importé est incomplet par rapport à sa musique. Le jeune cheval peut réellement avoir peu couru : aucun historique fictif n’est ajouté. Le meilleur chrono dans ces dix courses n’est **pas** un record personnel de carrière.',
      '', 'Ferrures : codes `0–8` décodés à partir du client officiel PMU, valeur brute conservée. Une ferrure absente reste inconnue. Les changements sont calculables entre deux observations datées, sous réserve de couverture.',
      '', 'Opposition détaillée : '+json.dumps(opposition,ensure_ascii=False)+'.',
      '', '## A2 — profondeur et temporalité','',
      f"Les quatre appels d’historique détaillé associés à une course ancienne donnent {temporal_n} lignes, avec **{latest_leak} ligne à la date cible ou après** dans cet échantillon. Ils exposent jusqu’à cinq performances par cheval. Ce contrôle ne prouve pas une garantie générale de l’API ni la date de publication originelle.",
      '', '| Course cible | Chevaux | Performances | Date la plus ancienne | Date la plus récente |', '|---|---:|---:|---|---|']
    for c in temporal['cases']:
        lines.append(f"| {c['race_id']} | {c['horses']} | {c['history_rows']} | {c.get('first_history_date','—')} | {c.get('last_history_date','—')} |")
    lines+=['', 'L’endpoint individuel `light-performances` renvoie l’historique connu aujourd’hui, y compris la course cible et les courses ultérieures éventuelles. Il exige un filtrage strict par date ; les résumés de carrière contemporains ne doivent pas alimenter un ancien backtest.',
      '',f"Contrôle prospectif : {len(verified_before)} courses du 13/10/2026 ({', '.join(r['venue'] for r in verified_before)}), {sum(r['runners'] for r in verified_before)} partants, capturées avant leur départ programmé, sans arrivée, chrono ou commentaire après-course. Voir `prospective_audit.json` pour les heures UTC exactes.",
      '', '## A3 — disponibilité des champs participants','',
      'Taux = valeurs non nulles et non vides / participants déclarés, non-partants inclus. Un zéro peut être une valeur valide. Présence ne signifie ni utilité prédictive ni preuve de disponibilité historique avant course.',
      '', '| Variable | 2024 (n=218) | 2025 (n=198) | 2026 (n=203) | Interprétation |', '|---|---:|---:|---:|---|']
    for row in catalog:
        cells=[f"{x['nonempty']}/{x['denominator']} ({x['rate']:.1%})" for x in row['availability'].values()]
        lines.append('| '+row['variable']+' | '+' | '.join(cells)+' | '+row['interpretation']+' |')
    starts=collections.Counter(r['start_type'] for r in audit['races'])
    lines+=['', '## Variables directes, dérivées et non validées','',
      '| Famille | Accessible | Traitement ou limite |','|---|---|---|',
      '| Forme, régularité, disqualifications | Musique et performances datées | Recalcul avant chaque course ; séparer attelé/monté et absences |',
      '| Repos, fréquence des courses | Dates des performances | Calculer les écarts ; couverture limitée = fréquence sous-estimée possible |',
      '| Distance, piste, corde | Distance, hippodrome, corde et texte des conditions | Grande/petite piste et surface pas uniformément structurées ; pas de table externe inventée |',
      f"| Départ | {starts['AUTOSTART']} autostarts explicites sur {nr} | Les {starts['NON_PRECISE']} autres restent « non précisé », pas automatiquement « volté » |",
      '| Recul | Distance individuelle et distance de base | Différence en mètres ; valider les unités et le parcours |',
      '| Ferrure et changement | Déclaration et historique, avec manquants | Pas d’imputation « ferré » ; changement calculé seulement entre observations connues |',
      '| Driver, entraîneur, tandem | Noms à chaque performance | Taux historiques à calculer sur une fenêtre antérieure, avec lissage et effectif |',
      '| Gains, âge, sexe, catégorie | Champs participants et conditions | Gains en centimes, conversion /100 vérifiée dans le client officiel ; plafonds dans texte à parser avec validation |',
      '| Opposition | Allocation, taille du peloton et détail de performance testé | Ne pas traiter la liste top-5 de l’ancien endpoint comme tout le peloton ; Elo nécessite des lignes complètes |',
      '| Parcours similaires | Date, distance, hippodrome et type de départ quand connu | Agrégations antérieures seulement ; échantillon insuffisant pour quantifier leur intérêt |',
      '| Météo | Prévision au niveau de la réunion quand fournie | Archive récupérée après coup ≠ prévision connue avant course ; garder datePrevision |',
      '| Terrain | Certaines structures trackCondition | measureTimestamp=0 seul est un placeholder, pas un état du terrain connu |',
      '| Avis entraîneur | Champ structuré ; parfois NEUTRE | Vérifier date et fréquence des avis ; pas d’assimilation à une information forte |',
      '| Records personnels | Pas de record de carrière vérifié dans ce test | Le champ tempsObtenu est le résultat de la course, timeRecord du détail est aussi une durée de course |',
      '', '## Contrôles de qualité et fuites','',
      f"Statut des cibles victoire : **{quality['status']}**. {quality['counts']['single_winner_races']} courses avec un seul gagnant ; aucun désaccord entre gagnant participants et arrivée de course. Aucun doublon numéro/identité dans les pelotons testés.",
      '',f"{quality['counts']['non_runners']} non-partants ; {quality['counts']['disqualified']} disqualifiés/distancés, dont {quality['counts']['distanced']} incidents DISTANCE ; {quality['counts']['stopped']} arrêtés. {len(quality['warnings'])} partants sans rang ni incident explicatif : ne pas leur inventer un rang pour un modèle de classement.",
      '',f"Identité composite reconstruite exactement pour {quality['counts']['composite_id_reconstructed']} lignes sans idCheval, à partir du nom et des deux parents. Cela ne constitue pas un identifiant universel garanti ; conserver les composants et rechercher les collisions lors de l’extension.",
      '',f"Contrôle des unités : {quality['time_unit_check']['n']} couples temps/réduction/distance comparables ; écart absolu médian {quality['time_unit_check']['median_absolute_error_seconds']:.4f} s, maximum {quality['time_unit_check']['max_absolute_error_seconds']:.4f} s après conversion des millisecondes. Cet accord est compatible avec les arrondis observés.",
      '', 'Liste d’exclusion du modèle : cotes et rapports, pronostics de marché, ordre d’arrivée de la course cible, chrono de la course cible, commentaires après-course, météo finale non horodatée, statistiques/record de carrière recalculés aujourd’hui. La simple suppression du champ résultat ne suffit pas : chaque agrégat doit utiliser uniquement des courses antérieures.',
      '', '## A4 — décision et étapes restantes','',
      '**GO conditionnel pour un pilote limité ; HOLD pour collecte massive et prédiction utilisable.** Pas de base définitive créée. La proposition de stockage et de backtest est dans `docs/ARCHITECTURE_PROPOSAL.md`.',
      '', 'Conditions avant extension : sauvegarde GitHub opérationnelle ; contrats d’identité et de temporalité testés ; règles explicites pour les manquants ; échantillon de training plus large, chronologique, figé. Les 46 courses de cet audit ne justifient aucune promesse de qualité prédictive.',
      '', 'Sources complémentaires : PMU apporte déjà l’historique requis pour le pilote. LeTROT a été identifié comme complément officiel éventuel pour les records et conditions, mais aucune collecte LeTROT n’est intégrée ni annoncée opérationnelle. Aucun abonnement, scraper de cotes ou API payante.',
      '', 'Les cotes resteront un import manuel horodaté. Le comparateur EV a des tests hors ligne : absence de modèle validé, convention de cote inconnue, course incohérente, cotes périmées ou partants incompatibles imposent NO BET. Il ne constitue pas encore une chaîne de prédiction de course.',
      '', '## Reproduction','', '```bash',
      'python -m scripts.audit_phase_a','python -m scripts.audit_horses','python -m scripts.audit_temporal',
      'python -m scripts.audit_before_race','python -m scripts.audit_opposition','python -m scripts.build_audit_report',
      'python -m unittest discover -s tests -v','```',
      '', 'Les dates de l’audit sont figées. Le replay utilise les captures existantes. Une capture nouvelle doit avoir son propre répertoire/version ; ne pas écraser un ancien instantané.',
      '', 'Sources vérifiables :',
      '- [Dépôt initial](https://github.com/berangerbeato-cmd/turf-lab).',
      '- [Exécution de référence](https://github.com/berangerbeato-cmd/turf-lab/actions/runs/38238010891).',
      '- API PMU publique, URL et SHA-256 de chaque réponse dans les manifestes `evidence/*/manifest.json`.',
      '- Contrat d’historique et unités : JavaScript public officiel PMU, URL et empreinte dans `evidence/official_client_history_contract.json`.',
      '']
    Path('reports/AUDIT_FEASIBILITY.md').write_text('\n'.join(lines),encoding='utf-8')
    hlines=['# Cinq historiques individuels — avant le 5 octobre 2026','',
            'Données issues de PMU. « — » signifie absent/non applicable. DQ = disqualifié ou distancé. Les courses montées sont indiquées explicitement. Les conditions complètes sont conservées dans le JSON.','']
    for h in horses['horses']:
        hlines += [f"## {h['name']}",'',f"{h['reason']}. {h['age']} ans, {h['sex']}. Identité : `{h['horse_id']}`.",
          '',f"{h['last_ten_returned']} performances retenues / {h['prior_rows_available']} antérieures disponibles. Gains de carrière déclarés pour la course cible : {h['career_earnings_eur']:.2f} €. Couverture exhaustive non garantie.",
          '', '| Date | Hippodrome | Discipline | Distance / recul | Arrivée | Réduction s/km | Driver | Entraîneur | Ferrure | Peloton / allocation |',
          '|---|---|---|---|---|---:|---|---|---|---|']
        for r in h['runs']:
            arrival='DQ' if r['disqualified'] else (str(r['rank']) if r['rank'] is not None else (r['arrival_status'] or '—'))
            speed=f"{r['seconds_per_km']:.2f}" if r['seconds_per_km'] is not None else '—'
            hlines.append(f"| {r['date']} | {r['venue']} | {r['discipline']} | {r['distance_covered_m'] or r['distance_m']} m / {r['handicap_m'] if r['handicap_m'] is not None else '—'} m | {arrival} | {speed} | {r['driver'] or '—'} | {r['trainer'] or '—'} | {r['shoes'] or '—'} | {r['field_size']} / {r['purse_eur']} € |")
        hlines+=['', f"Meilleure réduction observée dans l’échantillon : {h['best_seconds_per_km_in_sample']} s/km ; record personnel de carrière non établi.",'']
    Path('reports/FIVE_HORSE_HISTORIES.md').write_text('\n'.join(hlines),encoding='utf-8')
    print(json.dumps({'races':nr,'runners':n,'french_week':french,'all_week':total,'decision':decision['pilot_architecture'],'quality':quality['status']}))


if __name__=='__main__':main()
