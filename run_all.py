"""Offline reproduction. Stop on failure; keep every command's output."""
from pathlib import Path
import subprocess,sys,json,datetime
R=Path(__file__).resolve().parent
commands=[('unit_tests',['-m','unittest','discover','-s','tests','-v']),('research',['src/research.py']),('accounting',['src/verify_results.py']),('report',['src/build_report.py'])]
events=[]
for name,args in commands:
    print('Running',name,flush=True)
    result=subprocess.run([sys.executable,*args],cwd=R,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,encoding='utf-8',errors='replace')
    (R/'logs'/f'{name}.log').write_text(result.stdout,encoding='utf-8')
    events.append(dict(step=name,returncode=result.returncode,finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))
    (R/'logs/run_status.json').write_text(json.dumps(events,indent=2))
    if result.returncode:
        print(result.stdout);raise SystemExit(result.returncode)
    print(name,'PASS',flush=True)
print('All offline steps complete; TradingView and future forward checks remain pending.')
