from pathlib import Path
import os,json,sys,hashlib,datetime
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121')
initial=sorted(os.sched_getaffinity(0))
idle=[cpu for cpu in initial if cpu>=16]
assert idle,initial
os.sched_setaffinity(0,{16 if 16 in idle else min(idle)})
assert len(os.sched_getaffinity(0))==1 and set(os.sched_getaffinity(0)).isdisjoint(range(16))
root=b/'block-v1-20261030-568/src/project/experiments/block_v1'
sys.path.insert(0,str(root))
from native_escape import records
previous=b/'block-v1-20261030-562/tasks/revision300-v-marker-readback'
receipt=json.loads((previous/'receipt.json').read_text());assert receipt['passed']
path=previous/'original.def'
h=hashlib.sha256()
with path.open('rb')as stream:
 for chunk in iter(lambda:stream.read(1048576),b''):h.update(chunk)
assert h.hexdigest()==receipt['outputs']['original.def']
markers=json.loads((b/'block-v1-20261030-557/tasks/revision300-v-spacing-localize/revision300-v-physical-localization.json').read_text())['markers']
indices=[0,249,250]
wanted={markers[i]['marker']['net'].replace(chr(92),'')for i in indices}
found={}
for record in records(path):
 name=record.lstrip().split()[1].replace(chr(92),'')
 if name in wanted:
  assert name not in found and len(record)<100000
  found[name]=dict(def_record=record,sha256=hashlib.sha256(record.encode()).hexdigest())
  if len(found)==len(wanted):break
assert set(found)==wanted
print(json.dumps(dict(passed=True,read_only=True,physical_qualified=False,allocation_job='93555',initial_slurm_cpu_affinity=initial,cpu_affinity=sorted(os.sched_getaffinity(0)),captured_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),source_def_sha256=h.hexdigest(),source_def_receipt_sha256=hashlib.sha256((previous/'receipt.json').read_bytes()).hexdigest(),source_helper_sha256=hashlib.sha256((root/'native_escape.py').read_bytes()).hexdigest(),marker_indices=indices,records=found)))
