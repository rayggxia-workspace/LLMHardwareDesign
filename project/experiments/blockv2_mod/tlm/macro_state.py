"""Preserve committed DDR bytes and validity for a subsequent request phase."""
import struct,json
from pathlib import Path
from macro_memory import Data
from macro_assets import filehash
def save(memory,path,*,plan_sha256,asset_manifest_sha256):
 path=Path(path)
 if memory.pending:raise ValueError('cannot publish state with pending DDR writes')
 with path.open('xb') as f:
  f.write(b'NSTATE01'+struct.pack('<Q',len(memory.words)))
  for address,data in sorted(memory.words.items()):
   if address%64 or len(data)!=64:raise ValueError('invalid committed DDR word')
   f.write(struct.pack('<QQ',address,data.known));f.write(data.payload)
 metadata={'schema':'native-committed-DDR-state/1','plan_sha256':plan_sha256,
  'asset_manifest_sha256':asset_manifest_sha256,'file':path.name,'sha256':filehash(path),
  'committed_beats':len(memory.words),'semantics':'only actual completed writes; unknown padding retains byte validity'}
 path.with_suffix('.json').write_text(json.dumps(metadata,indent=2)+'\n')
 return metadata
def load(path):
 path=Path(path);metadata=json.loads(path.with_suffix('.json').read_text())
 if metadata['schema']!='native-committed-DDR-state/1' or filehash(path)!=metadata['sha256']:
  raise ValueError('invalid committed state seal')
 result={}
 with path.open('rb') as f:
  if f.read(8)!=b'NSTATE01':raise ValueError('state format')
  count,=struct.unpack('<Q',f.read(8))
  if count!=metadata['committed_beats']:raise ValueError('state length')
  for _ in range(count):
   address,known=struct.unpack('<QQ',f.read(16));payload=f.read(64)
   if address%64 or address in result or len(payload)!=64:raise ValueError('state address/payload')
   result[address]=Data(payload,known)
  if f.read(1):raise ValueError('trailing state bytes')
 return metadata,result
