"""Run only v4.2 display tests and diagnostics; preserve legacy results."""
import json,subprocess,sys
from pathlib import Path
R=Path(__file__).resolve().parent
steps=[('tests',[sys.executable,'-m','unittest','discover','-s','tests','-p','test_hist_line_v42.py']),('replay',[sys.executable,'src/verify_hist_line_v42.py'])]
status=[]
for name,cmd in steps:
    p=subprocess.run(cmd,cwd=R,capture_output=True,text=True,encoding='utf-8')
    (R/f'logs/hist_line_v42_{name}.log').write_text(p.stdout+p.stderr,encoding='utf-8')
    status.append(dict(step=name,exit_code=p.returncode))
    print(name,p.returncode)
    if p.returncode:raise SystemExit(p.returncode)
(R/'logs/hist_line_v42_status.json').write_text(json.dumps(status,indent=2),encoding='utf-8')
