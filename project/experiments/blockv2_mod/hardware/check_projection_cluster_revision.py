"""Freeze actual SRAM/DDR completion and numeric evidence for the service assembly."""
from pathlib import Path
from hashlib import sha256
import json,shutil,xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'evidence/architecture-revision-185'
def main():
 job=114578;run=OUT/f'projection-cluster-{job}';log=(run/'run.log').read_text()
 assert 'PROJECTION_CLUSTER_PASS cases=4 output_values=512 segmented_rows=1 load_store_projection_calls=40' in log
 assert log.count('PROJECTION_CASE_PASS')==4
 paths=set()
 for xml in ('projection-selected-114553.xml','projection-service-cluster-114577.xml'):
  for f in ET.parse(OUT/xml).getroot().findall('./files/file'):
   name=f.get('filename')
   if name.startswith('<'):continue
   p=Path(name);p=p if p.is_absolute() else ROOT/p
   if p.suffix in ('.sv','.svh','.v'):paths.add(p)
 paths.discard(OUT/'projection_selected_fixture.sv')
 for name in ('hardware/build_projection_service_cluster.py','hardware/build_projection_cluster_fixture.py',
  'evidence/architecture-revision-185/projection_cluster_fixture.sv',
  'evidence/architecture-revision-185/tb_projection_cluster.sv',
  'evidence/architecture-revision-185/make_projection_local_vectors.py',
  'evidence/architecture-revision-185/make_projection_cluster_vectors.py',
  'evidence/architecture-revision-185/projection-cluster.sbatch','compiler/projection_local_descriptor.py'):
  paths.add(ROOT/name)
 hashes={}
 for p in sorted(paths):
  data=p.read_bytes();hashes[str(p)]=sha256(data).hexdigest()
  try:relative=p.relative_to(ROOT)
  except ValueError:relative=Path('external')/str(p).lstrip('/')
  dest=run/'validated-source'/relative;dest.parent.mkdir(parents=True,exist_ok=True)
  if dest.exists():assert dest.read_bytes()==data,'validated source changed'
  else:shutil.copyfile(p,dest)
 result={'schema':'projection-service-assembly-evidence/1','job':job,'sources':hashes,
  'log_sha256':sha256((run/'run.log').read_bytes()).hexdigest(),
  'cases':json.loads((run/'cases.json').read_text()),'calls':40,'numerical_outputs':512,
  'segmented_input':{'segments':16,'source_spacing_bytes':1024,'destination_spacing_bytes':512,
    'method':'real DRL1 SRAM load and DWS1 DDR store before MPR1'},
  'result_checks':['real SRAM content','DDR committed payload','SRAM write ACK count',
    'DDR input and weight request/response counts','DDR write commit count','completion after drain'],
  'whole_qwen_accepted':False,'timing_calibrated':False,'physical_accepted':False}
 (OUT/'projection-service-assembly-receipt.json').write_text(json.dumps(result,indent=2)+'\n')
 print('Projection service assembly evidence frozen')
if __name__=='__main__':main()
