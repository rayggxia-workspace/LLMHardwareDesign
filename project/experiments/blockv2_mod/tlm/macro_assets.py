"""Sealed runtime image reads at the plan's exact DDR allocations."""
import json
from pathlib import Path
from bisect import bisect_right
from mmap import mmap,ACCESS_READ
from hashlib import sha256
from macro_memory import Memory
def filehash(p):
 h=sha256()
 with p.open('rb') as f:
  for block in iter(lambda:f.read(1<<20),b''):h.update(block)
 return h.hexdigest()
class Assets:
 def __init__(self,path,manifest,payloads):
  path=Path(path);self.root=path.parent;self.manifest=json.loads(path.read_text())
  if self.manifest['schema']!='macro-runtime-assets/1':raise ValueError('asset schema')
  if self.manifest['plan_sha256']!=manifest['plan_sha256']:raise ValueError('assets target another plan')
  if self.manifest['hardware_sha256']!=manifest['payloads']['hardware.json']['sha256']:
   raise ValueError('assets target another base')
  storage=json.loads(payloads['storage.json'])
  expected={}
  for r in storage['runtime_asset_requirements']:
   value=r['region'] if r['kind']=='input_tensor' else r
   name=value['value'] if r['kind']=='input_tensor' else r['graph_value']
   expected[name]=(value['base'],(value['bytes']+63)//64*64)
  observed={r['name']:(r['base'],r['bytes']) for r in self.manifest['regions']}
  if observed!=expected or len(observed)!=len(self.manifest['regions']):
   raise ValueError('asset set differs from compiled requirements')
  self.rows=sorted(self.manifest['regions'],key=lambda r:r['base']);self.maps=[]
  for row in self.rows:
   p=(self.root/row['file']).resolve()
   if not p.is_relative_to(self.root.resolve()) or p.stat().st_size!=row['bytes'] or filehash(p)!=row['sha256']:
    raise ValueError('runtime asset seal failure '+row['name'])
   with p.open('rb') as f:self.maps.append(mmap(f.fileno(),0,access=ACCESS_READ))
  for a,b in zip(self.rows,self.rows[1:]):
   if a['base']+a['bytes']>b['base']:raise ValueError('overlapping initial assets')
  self.bases=[r['base'] for r in self.rows]
  self.descriptor_base=manifest['descriptor_base'];self.descriptors=payloads['descriptors.bin']
  self.memory=Memory(self.readonly,list(storage['regions'].values()))
 def readonly(self,address):
  if self.descriptor_base<=address and address+64<=self.descriptor_base+len(self.descriptors):
   offset=address-self.descriptor_base;return self.descriptors[offset:offset+64]
  i=bisect_right(self.bases,address)-1
  if i<0 or address+64>self.rows[i]['base']+self.rows[i]['bytes']:raise KeyError(address)
  offset=address-self.bases[i];return self.maps[i][offset:offset+64]
