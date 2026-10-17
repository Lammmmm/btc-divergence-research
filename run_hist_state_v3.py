"""Reproduce and save v3 coordinate tests. Pine compilation remains a separate UI check."""
import subprocess,sys,json
from pathlib import Path
R=Path(__file__).resolve().parent
records=[]
for name,script in [('hist_state_v3_tests','tests/test_hist_state_v3.py'),('hist_state_v3_lifecycle_regression','tests/test_hist_lifecycle.py'),('hist_state_v3_coordinates','src/verify_hist_state_v3.py')]:
    r=subprocess.run([sys.executable,str(R/script)],capture_output=True,text=True,encoding='utf-8',errors='replace')
    (R/f'logs/{name}.log').write_text(r.stdout+r.stderr,encoding='utf-8')
    records.append(dict(step=name,exit_code=r.returncode,status='PASS' if r.returncode==0 else 'FAIL'))
    (R/'logs/hist_state_v3_run_status.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
    print(name,records[-1]['status'])
    if r.returncode:sys.exit(r.returncode)
