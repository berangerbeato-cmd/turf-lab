"""Append an honest machine-generated execution checkpoint, preserving the plan."""
import os
from datetime import datetime, timezone
from pathlib import Path


def main():
    if os.environ.get('GITHUB_ACTIONS')!='true':
        raise SystemExit('Only call this checkpoint writer from a real GitHub Actions run')
    run_id=os.environ['GITHUB_RUN_ID']
    status=os.environ['AUDIT_JOB_STATUS']
    path=Path('WORK_PROGRESS.md')
    text=path.read_text(encoding='utf-8')
    marker='<!-- CLOUD_CHECKPOINT -->'
    text=text.split(marker)[0].rstrip()+'\n\n'
    block=f'''{marker}
## Dernière exécution Actions observée automatiquement

- Horodatage UTC : {datetime.now(timezone.utc).isoformat()}.
- Run : https://github.com/berangerbeato-cmd/turf-lab/actions/runs/{run_id}
- Commit exécuté : `{os.environ['GITHUB_SHA']}`.
- Statut avant sauvegarde : **{status}**.
- La sauvegarde Git se fait à l'étape suivante ; confirmer son résultat dans le run.
- Une exécution d'audit réussie ne valide pas un modèle prédictif.
- En cas d'échec, les rapports précédents peuvent être périmés ; utiliser le journal
  et les manifestes pour reprendre au premier appel absent, sans répéter les autres.
'''
    path.write_text(text+block,encoding='utf-8')


if __name__=='__main__':main()
