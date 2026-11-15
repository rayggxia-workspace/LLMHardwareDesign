"""Reject sealed-image changes that the fixed TLM LC semantics cannot execute."""
from pathlib import Path
import json
from native_package_runtime import load
from native_local_kernel import validate
base=Path('evidence/architecture-revision-185/shared-memory-bound-packages-114908')
counts=[];negative=[]
for stage in ('prefill','decode'):
 manifest,payloads,pages=load(base/(stage+'-package'))
 deployment=json.loads(payloads['deployment.json']);raw=payloads['local-kernel.bin']
 validate(raw,topology=manifest['topology'],image_id=deployment['local_program_image_id'])
 counts.append({'stage':stage,'calls':manifest['native_calls'],'local_program_bytes':len(raw)})
 for name,offset in [('EXEC',135),('WAIT',143),('RETURN',151),('service_descriptor',224),('ABI',68),('image_id',60)]:
  bad=bytearray(raw);bad[offset]^=1
  try:validate(bytes(bad),topology=manifest['topology'],image_id=deployment['local_program_image_id'])
  except ValueError:negative.append(stage+':'+name)
  else:raise AssertionError('unsupported local program admitted')
print(json.dumps({'packages':counts,'negative_cases':negative,'scope':'LC program admission only; no new execution/timing claim'}))
