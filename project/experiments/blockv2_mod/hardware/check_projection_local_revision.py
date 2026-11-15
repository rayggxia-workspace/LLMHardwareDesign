"""Index the completed full-K M/S_P projection regression without graph claims."""
from pathlib import Path
from hashlib import sha256
import json,shutil,xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'evidence/architecture-revision-185'
def main():
 job=114576;run=OUT/f'projection-local-{job}'
 log=(run/'run.log').read_text()
 assert log.count('PROJECTION_CASE_PASS')==4
 assert 'PROJECTION_LOCAL_PASS cases=4 output_values=512 rejected=3 reset_between_cases=0' in log
 xml=ET.parse(OUT/'projection-selected-114553.xml').getroot()
 paths=set()
 for f in xml.findall('./files/file'):
  name=f.get('filename')
  if name.startswith('<'):continue
  p=Path(name)
  if not p.is_absolute():p=ROOT/p
  if p.suffix in ('.sv','.svh','.v'):paths.add(p)
 for name in ('rtl/control/macro_service_dispatch.sv',
  'hardware/build_projection_selected_fixture.py','hardware/build_projection_local_header.py',
  'hardware/projection_local_service_body.svh.in','compiler/projection_local_descriptor.py',
  'evidence/architecture-revision-185/tb_projection_local.sv',
  'evidence/architecture-revision-185/make_projection_local_vectors.py',
  'evidence/architecture-revision-185/projection-local.sbatch'):
  paths.add(ROOT/name)
 hashes={}
 for p in sorted(paths):
  key=str(p);data=p.read_bytes();hashes[key]=sha256(data).hexdigest()
  try:relative=p.relative_to(ROOT)
  except ValueError:relative=Path('external')/str(p).lstrip('/')
  dest=run/'validated-source'/relative;dest.parent.mkdir(parents=True,exist_ok=True)
  if dest.exists():assert dest.read_bytes()==data,'validated input changed: '+str(p)
  else:shutil.copyfile(p,dest)
 receipt={'schema':'projection-local-functional-evidence/1','job':job,
  'sources':hashes,'log_sha256':sha256((run/'run.log').read_bytes()).hexdigest(),
  'cases':json.loads((run/'cases.json').read_text()),'output_values':512,'rejected_cases':3,
  'real_macros':['m_native_leaf_s32','local_s_p'],'reset_between_cases':False,
  'ddr_model':'finite shared 32-entry read queue, one admitted request and one response at a time',
  'numerical_scope':'complete K projection tiles with independent signed integer reference',
  'whole_qwen_accepted':False,'timing_calibrated':False,'physical_accepted':False}
 (OUT/'projection-local-functional-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
 print('Full-K projection + dispatch verified; 512 values, three rejected commands; no full-Qwen claim')
if __name__=='__main__':main()
