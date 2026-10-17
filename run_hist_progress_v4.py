import subprocess,sys,json
from pathlib import Path
R=Path(__file__).resolve().parent;records=[]
for name,script in [('hist_progress_v4_tests','tests/test_hist_progress_v4.py'),('hist_progress_v4_lifecycle','tests/test_hist_lifecycle.py'),('hist_progress_v4_replay','src/verify_hist_progress_v4.py')]:
    r=subprocess.run([sys.executable,str(R/script)],capture_output=True,text=True,encoding='utf-8',errors='replace')
    (R/f'logs/{name}.log').write_text(r.stdout+r.stderr,encoding='utf-8')
    records.append(dict(step=name,exit_code=r.returncode))
    (R/'logs/hist_progress_v4_status.json').write_text(json.dumps(records,indent=2))
    print(name,'PASS' if r.returncode==0 else 'FAIL',flush=True)
    if r.returncode:print(r.stdout+r.stderr);sys.exit(r.returncode)
