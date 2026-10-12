"""Use explicit workflow inputs, or the versioned request for a push trigger."""
import json
import os
import subprocess
import sys
from pathlib import Path


def main():
    values=[os.environ.get(k,'') for k in ('RACE_DATE','RACE_MEETING','RACE_NUMBER')]
    if any(values) and not all(values):raise ValueError('All three explicit inputs required')
    if not any(values):
        data=json.loads(Path('config/prediction_request.json').read_text())
        values=[str(data[k]) for k in ('date','reunion','course')]
    subprocess.run([sys.executable,'-m','scripts.predict_race','--date',values[0],'--reunion',values[1],'--course',values[2]],check=True)

if __name__=='__main__':main()
