"""Verify release snapshot without changing files."""
import hashlib,json
from pathlib import Path
R=Path(__file__).resolve().parents[1]
entries=json.loads((R/'manifest.sha256.json').read_text(encoding='utf-8'))['files']
bad=[]
for rel,info in entries.items():
    p=R/rel
    if not p.exists() or hashlib.sha256(p.read_bytes()).hexdigest()!=info['sha256']:bad.append(rel)
print('Files checked:',len(entries),'mismatches:',len(bad))
if bad:
    print('\n'.join(bad));raise SystemExit(1)
