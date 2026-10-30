"""Index this independent documentation package, excluding the index itself."""
from pathlib import Path
import hashlib,json,sys
out=Path(sys.argv[1]);p=out/'data/evidence_manifest.json'
index={f.relative_to(out).as_posix():{'bytes':f.stat().st_size,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()} for f in sorted(out.rglob('*')) if f.is_file() and f!=p}
p.write_text(json.dumps(index,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
print('INDEXED_DOCUMENTATION_FILES',len(index))
