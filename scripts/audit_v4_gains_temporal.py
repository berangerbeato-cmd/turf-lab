"""Audit historic PMU career gains: are stored values plausibly as-of each race?

Never train on target-field archived gain figures unless their chronology is
confirmed. This diagnostic is not a proof of capture-time publication.
"""
import gzip,hashlib,json,math
from pathlib import Path
from collections import defaultdict,Counter
from statistics import median
from turf_lab.month_history import identity
from turf_lab.evidence import dump

def run():
    profiles=defaultdict(list);totals=Counter()
    for manifest in sorted(Path("data").glob("month_*/manifest.json")):
        month=manifest.parent.name[6:]
        if not "2022-01"<=month<="2026-09":continue
        for entry in json.loads(manifest.read_text())["partitions"]:
            raw=gzip.decompress(Path(entry["file"]).read_bytes())
            if hashlib.sha256(raw).hexdigest()!=entry["sha256"]:raise ValueError("Raw participant SHA mismatch")
            obj=json.loads(raw)
            for p in obj["participants"]:
                if p.get("statut")=="NON_PARTANT":continue
                money=(p.get("gainsParticipant") or {}).get("gainsCarriere")
                totals["participants"]+=1
                if isinstance(money,(int,float)) and not isinstance(money,bool) and math.isfinite(money) and money>=0:
                    totals["valid"]+=1
                    profiles[identity(p)].append((obj["date"],float(money),int(p.get("ordreArrivee")==1)))
                else:totals["unknown"]+=1
    sequence=Counter();samples=[]
    for ident,points in profiles.items():
        points.sort()
        if len(points)<3:continue
        sequence["horses_three_snapshots"]+=1
        distinct={g for _,g,_ in points}
        has_wins=any(w for _,g,w in points[:-1])
        if len(distinct)==1:
            sequence["constant_gains"]+=1
            if has_wins:sequence["constant_despite_prior_win"]+=1
        if any(points[i+1][1]<points[i][1]-1e-6 for i in range(len(points)-1)):
            sequence["decreases"]+=1
        if any(points[i+1][1]>points[i][1] for i in range(len(points)-1)):
            sequence["increases"]+=1
        if len(samples)<10 and has_wins:
            samples.append({"horse_sha":hashlib.sha256(ident.encode()).hexdigest()[:10],
                "first":points[0][:2],"last":points[-1][:2],"snapshots":len(points),
                "different_amounts":len(distinct)})
    report={"status":"TEMPORAL_AVAILABILITY_AUDIT_NOT_A_TRAINING_ASSERTION",
            "counts":dict(totals),"sequence":dict(sequence),"examples_hashed":samples,
            "money_asof_proven":False,
            "policy":"Do not inject career euro gains into historical model without independent point-in-time validation; use prior-only performance class proxy instead."}
    dump("reports/v4_multifeature/gains_temporal_audit.json",report)
    print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=="__main__":run()
