"""Verify a fixed Git source tree plus exact official BCR overlays.

This does not accept the mismatching registry archive. A supported repository
override uses independently verified source from the same pinned commit.
"""
from pathlib import Path
import hashlib,json,base64
COMMIT='f04e81565793c768b747a8fd058f3e7aeceee1b5'
TREE='beb091db6b9db2ecba0d74733748e52cc5043d5c'
SOURCE_JSON='918163d219b8fbeb010a1c9263bd49d5f937ff5797493799ad284209936158f6'

def git_hash(kind,data):
 return hashlib.sha1(kind.encode()+b' '+str(len(data)).encode()+b'\0'+data).hexdigest()

def verify(root,proof):
 sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
 commit=json.loads((proof/'git-commit.json').read_text());tree=json.loads((proof/'git-tree.json').read_text())
 assert commit['sha']==COMMIT and commit['tree']['sha']==TREE and tree['sha']==TREE and not tree['truncated']
 entries={r['path']:r for r in tree['tree']};children={}
 for name,row in entries.items():
  path=Path(name);assert not path.is_absolute()and '..'not in path.parts
  parent=str(path.parent).replace('\\','/');parent=''if parent=='.'else parent
  children.setdefault(parent,[]).append((path.name,row))
 def tree_hash(name):
  data=b''
  for base,row in sorted(children.get(name,[]),key=lambda v:v[0]+('/'if v[1]['type']=='tree'else'')):
   mode=row['mode'].lstrip('0');digest=row['sha']
   if row['type']=='tree':assert tree_hash((name+'/'if name else'')+base)==digest
   else:assert row['type']=='blob'and mode in ['100644','100755']
   data+=mode.encode()+b' '+base.encode()+b'\0'+bytes.fromhex(digest)
  return git_hash('tree',data)
 assert tree_hash('')==TREE
 prefix='slang-'+COMMIT;source=root/prefix;files={}
 for name,row in entries.items():
  if row['type']!='blob':continue
  path=source/name;assert path.is_file()and not path.is_symlink()
  assert git_hash('blob',path.read_bytes())==row['sha'],name
  assert bool(path.stat().st_mode&0o111)==(row['mode']=='100755'),name
  files[prefix+'/'+name]=sha(path)
 assert len(files)==560 and {str(p.relative_to(source)).replace('\\','/')for p in source.rglob('*')if p.is_file()}=={n for n,r in entries.items()if r['type']=='blob'}
 assert sha(proof/'source.json')==SOURCE_JSON
 definition=json.loads((proof/'source.json').read_text())
 for name,integrity in definition['overlay'].items():
  path=root/name;assert path.is_file()and not path.is_symlink()
  assert hashlib.sha256(path.read_bytes()).digest()==base64.b64decode(integrity.split('-',1)[1])
  files[name]=sha(path)
 assert {str(p.relative_to(root)).replace('\\','/')for p in root.rglob('*')if p.is_file()}==set(files)
 return dict(passed=True,repository='MikePopoloski/slang',commit=COMMIT,tree_sha=TREE,verified_git_files=560,official_overlay_files=len(definition['overlay']),source_json_sha256=SOURCE_JSON,original_archive_integrity=definition['integrity'],registry_archive_accepted=False,files=files,scope='Exact Git blob/mode/path/tree verification of the same pinned commit and official integrity-checked build overlays; original archive mismatch not waived.')
