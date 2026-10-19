"""Reproduce only v4.3.2 focused tests; old studies and indicator stay unchanged."""
from pathlib import Path
import subprocess,sys,json
R=Path(__file__).resolve().parent
steps=[('v432_lifecycle_tests',['-m','unittest','discover','-s','tests','-p','test_hist_lifecycle.py','-v']),
       ('v432_structure_tests',['-m','unittest','discover','-s','tests','-p','test_structure_reversal.py','-v']),
       ('v432_engine_tests',['-m','unittest','discover','-s','tests','-p','test_engine.py','-v']),
       ('v432_backtest',['src/backtest_hist_v432.py']),('v432_independent',['src/verify_hist_v432_backtest.py']),
       ('v432_report',['src/build_hist_v432_report.py'])]
status=[]
for name,args in steps:
    p=subprocess.run([sys.executable,*args],cwd=R,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,encoding='utf-8',errors='replace')
    (R/'logs'/f'{name}.log').write_text(p.stdout,encoding='utf-8')
    status.append(dict(step=name,returncode=p.returncode))
    (R/'logs/v432_backtest_run_status.json').write_text(json.dumps(status,indent=2))
    if p.returncode:print(p.stdout);raise SystemExit(p.returncode)
    print(name,'PASS',flush=True)
