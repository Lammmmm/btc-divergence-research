"""Reproduce only the practical-reference extension; do not rerun 500 old groups."""
from pathlib import Path
import subprocess,sys,json,datetime
R=Path(__file__).resolve().parent
steps=[('reference_tests',['-m','unittest','discover','-s','tests','-p','test_reference_use.py','-v']),
       ('reference_events',['src/reference_use.py']),('reference_verify',['src/verify_reference_use.py']),('reference_report',['src/build_reference_report.py'])]
status=[]
for name,args in steps:
    result=subprocess.run([sys.executable,*args],cwd=R,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,encoding='utf-8',errors='replace')
    (R/'logs'/f'{name}.log').write_text(result.stdout,encoding='utf-8')
    status.append(dict(step=name,returncode=result.returncode,utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))
    (R/'logs/reference_run_status.json').write_text(json.dumps(status,indent=2))
    if result.returncode:print(result.stdout);raise SystemExit(result.returncode)
    print(name,'PASS',flush=True)
