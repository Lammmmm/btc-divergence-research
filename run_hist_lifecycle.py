"""Reproduce offline lifecycle checks; TradingView compilation is a separate UI check."""
import subprocess,sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
jobs=[('hist_lifecycle_tests','tests/test_hist_lifecycle.py'),('hist_lifecycle_reconciliation','src/verify_hist_lifecycle.py')]
records=[]
for name,script in jobs:
    r=subprocess.run([sys.executable,str(ROOT/script)],capture_output=True,text=True,encoding='utf-8',errors='replace')
    (ROOT/f'logs/{name}.log').write_text(r.stdout+r.stderr,encoding='utf-8')
    records.append(dict(step=name,exit_code=r.returncode,status='PASS' if r.returncode==0 else 'FAIL'))
    (ROOT/'logs/hist_lifecycle_run_status.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
    print(name,records[-1]['status'])
    if r.returncode:sys.exit(r.returncode)
