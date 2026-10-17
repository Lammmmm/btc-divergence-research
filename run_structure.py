"""Run only the no-duration-expiry structure experiment, preserving older studies."""
from pathlib import Path
import subprocess,sys,json,datetime
R=Path(__file__).resolve().parent
steps=[('structure_tests',['-m','unittest','discover','-s','tests','-p','test_structure_reversal.py','-v']),
       ('structure_events',['src/structure_reversal.py']),('structure_verify',['src/verify_structure_reversal.py']),('structure_report',['src/build_structure_report.py'])]
status=[]
for name,args in steps:
    result=subprocess.run([sys.executable,*args],cwd=R,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,encoding='utf-8',errors='replace')
    (R/'logs'/f'{name}.log').write_text(result.stdout,encoding='utf-8')
    status.append(dict(step=name,returncode=result.returncode,utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))
    (R/'logs/structure_run_status.json').write_text(json.dumps(status,indent=2))
    if result.returncode:print(result.stdout);raise SystemExit(result.returncode)
    print(name,'PASS',flush=True)
