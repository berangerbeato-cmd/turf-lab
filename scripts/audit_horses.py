"""Five representative runners selected using pre-race attributes, not outcomes."""
import argparse
import collections
import json
from pathlib import Path
from urllib.parse import quote

from collect import BASE
from turf_lab.evidence import EvidenceStore, dump
from turf_lab.history import before_target, summarize_run


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--evidence", default="evidence/horse_audit_2026-10-12")
    args = p.parse_args()
    store = EvidenceStore(args.evidence, max_requests=20)
    target = "2026-10-05"
    # Reuse archived participants when the main audit has already reached them.
    base_store = EvidenceStore("evidence/phase_a_2026-10-12", max_requests=0)
    def runners(rn, cn):
        key = f"{target}_R{rn}C{cn}_participants"
        data = (base_store if key in base_store.manifest else store).race(target, rn, cn, "participants")
        if not data or not data.get("participants"):
            raise ValueError("Missing runner list")
        return data["participants"]
    regulars = runners(1,1)
    selections = [
        (next(r for r in regulars if r['nom']=="FABIUS ORS"),"Importé, historique français court",1,1),
        (next(r for r in regulars if r['nom']=="LORD ON WAY"),"5 ans, plusieurs victoires dans la musique",1,1),
        (min(runners(1,2), key=lambda r:r['numPmu']),"2 ans, jeune cheval en autostart",1,2),
        (max(runners(1,5), key=lambda r:(r.get('handicapDistance',0),r.get('age',0),-r['numPmu'])),"Cheval âgé, recul",1,5),
        (max(runners(8,5), key=lambda r:(r.get('musique','').count('Da'),-r['numPmu'])),"Jument de province, disqualifications fréquentes",8,5),
    ]
    report = {"as_of_exclusive":target,"selection_method":"Attributes known before the target race; outcomes not used for selection", "horses":[]}
    for runner, reason, rn, cn in selections:
        horse_id = runner["idCheval"]
        history = store.get(BASE.rsplit('/',1)[0] + '/program/' + quote(horse_id,safe='') + '/light-performances',
                            f"history_R{rn}C{cn}_{runner['numPmu']}")
        if history is None:
            report['horses'].append({"horse_id":horse_id,"name":runner['nom'],"reason":reason,"error":"history_unavailable"})
            continue
        prior, excluded, available = before_target(history,target)
        normalized = [summarize_run(r) for r in prior]
        field_counts = collections.Counter()
        for row in normalized:
            for k,v in row.items():
                if v is not None and v != "" and v != {}:
                    field_counts[k] += 1
        observed_speeds = [r['seconds_per_km'] for r in normalized if r['seconds_per_km']]
        report['horses'].append({"horse_id":horse_id,"name":runner['nom'],"reason":reason,
             "target_race":f"{target}_R{rn}C{cn}", "target_number":runner['numPmu'],
             "age":runner.get('age'),"sex":runner.get('sexe'),"music":runner.get('musique'),
             "career_earnings_raw":runner.get('gainsParticipant',{}).get('gainsCarriere'),
             "career_earnings_eur":runner.get('gainsParticipant',{}).get('gainsCarriere',0)/100,
             "career_earnings_unit":"centimes in gainsParticipant; /100 verified in official PMU formatter module 75704",
             "raw_history_rows":len(history.get('runner',{}).get('racesRun',[])),
             "prior_rows_available":available,"last_ten_returned":len(normalized),"excluded":excluded,
             "ten_rows_available":len(normalized)==10,
             "coverage_caveat":"Available source history only; exhaustiveness is not guaranteed, especially abroad",
             "best_seconds_per_km_in_sample":min(observed_speeds) if observed_speeds else None,
             "lifetime_personal_record":None,"field_nonempty_counts":dict(field_counts),"runs":normalized})
        print(runner['nom'], 'history',len(normalized),'available before',target,flush=True)
        dump('reports/five_horse_histories.json',report)
    dump('reports/five_horse_histories.json',report)


if __name__ == '__main__': main()
