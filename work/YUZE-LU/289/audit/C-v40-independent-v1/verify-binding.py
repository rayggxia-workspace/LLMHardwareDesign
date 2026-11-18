from pathlib import Path
import hashlib,json,sys
p=Path(sys.argv[1]);data=json.loads(p.read_text())
assert data['source_frozen_for_independent_audit'] and not data['accepted']
for name,h in dict(data['files_sha256'],**data['audit_code_sha256']).items():
 q=hashlib.sha256()
 with Path(name).open('rb') as f:
  for part in iter(lambda:f.read(4*1024*1024),b''):q.update(part)
 assert q.hexdigest()==h, ('Frozen audit input changed',name)
print('FROZEN_SOURCE_AND_CODE_HASHES_MATCH')
