"""Bind fresh physical source files to the reviewed Git hardware manifest."""
import hashlib,json,sys
from pathlib import Path
root, lock_path = map(Path,sys.argv[1:])
lock=json.loads(lock_path.read_text())
def digest(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
actual={p:digest(root/'source'/p) for p in lock['files']}
assert actual==lock['files'],'physical hardware differs from reviewed files'
archive=root/'source/source.tar.gz'
# source is a symlink into the immutable upload; its archive is its sibling.
archive=(root/'source').resolve().parent/'source.tar.gz'
assert digest(archive)==lock['physical_source_tar_sha256']
result=dict(physical_source_matches_committed_hardware=True,source_lock=lock,
 physical_source=str((root/'source').resolve()),physical_source_tar_sha256=digest(archive),actual_files=actual)
(root/'hardware-source-verified.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(dict(passed=True,files=len(actual),physical_source_tar_sha256=digest(archive))))
