"""Create a checksummed ZIP beside this project, excluding runtime caches."""
from pathlib import Path
import hashlib,json,zipfile
R=Path(__file__).resolve().parents[1]
def eligible(p):
    return p.is_file() and not any(k in p.relative_to(R).parts for k in ['__pycache__','.venv','.git','node_modules'])
files=sorted(p for p in R.rglob('*') if eligible(p) and p.name!='manifest.sha256.json')
manifest={'hash_algorithm':'SHA256','files':{p.relative_to(R).as_posix():{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in files}}
(R/'manifest.sha256.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
files.append(R/'manifest.sha256.json')
dest=R.parent/'btc-divergence-research.zip'
with zipfile.ZipFile(dest,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for p in files:z.write(p,Path(R.name)/p.relative_to(R))
with zipfile.ZipFile(dest) as z:
    assert z.testzip() is None
    assert len(z.namelist())==len(files)
    for rel,entry in manifest['files'].items():
        assert hashlib.sha256(z.read(R.name+'/'+rel)).hexdigest()==entry['sha256']
digest=hashlib.sha256(dest.read_bytes()).hexdigest()
dest.with_suffix('.zip.sha256').write_text(digest+'  '+dest.name+'\n')
print(json.dumps({'zip':str(dest),'files':len(files),'uncompressed_bytes':sum(p.stat().st_size for p in files),'zip_bytes':dest.stat().st_size,'largest_file_bytes':max(p.stat().st_size for p in files),'sha256':digest},indent=2))
