from pathlib import Path
from hashlib import sha256
from collections import Counter
import json,shutil,xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'evidence/architecture-revision-185'
def main():
 run=OUT/'projection-gated-cluster-114602';log=(run/'run.log').read_text()
 assert 'PROJECTION_GATED_CLUSTER_PASS projection_cases=4 projection_values=512 gated_values=128 calls=44' in log
 xml=ET.parse(OUT/'projection-gated-selected-114624.xml').getroot()
 modules={m.get('name'):m.get('origName') for m in xml.findall('./netlist/module')}
 counts=Counter(modules[c.get('submodname')] for c in xml.findall('./cells//cell'))
 assert counts['m_native_leaf_s32']==counts['g_s32']==counts['local_s_p']==1
 for name in ('local_s_base','e_s32_native','n_s32_mod','dot_s32_core'):assert counts[name]==0,name
 paths=set()
 for f in xml.findall('./files/file'):
  name=f.get('filename')
  if name.startswith('<'):continue
  p=Path(name);p=p if p.is_absolute() else ROOT/p
  if p.suffix in ('.sv','.svh','.v'):paths.add(p)
 for name in ('hardware/build_projection_service_cluster.py','hardware/build_projection_cluster_fixture.py',
  'hardware/normalize_gated_service.py','evidence/architecture-revision-185/tb_projection_gated_cluster.sv',
  'evidence/architecture-revision-185/make_projection_local_vectors.py',
  'evidence/architecture-revision-185/make_projection_cluster_vectors.py',
  'evidence/architecture-revision-185/make_gated_cluster_vectors.py',
  'evidence/architecture-revision-185/projection-gated-cluster.sbatch'):
  paths.add(ROOT/name)
 ref=Path('/public/home/yuzelu/project-circuit/issue260-product-retirement-V6JR7Km4/source/project/experiments/w8a16_g')
 paths.update((ref/'reference.py',ref/'lut_q16.json'))
 hashes={}
 for p in sorted(paths):
  raw=p.read_bytes();hashes[str(p)]=sha256(raw).hexdigest()
  try:relative=p.relative_to(ROOT)
  except ValueError:relative=Path('external')/str(p).lstrip('/')
  dest=run/'validated-source'/relative;dest.parent.mkdir(parents=True,exist_ok=True)
  if dest.exists():assert dest.read_bytes()==raw
  else:shutil.copyfile(p,dest)
 result={'schema':'projection-gated-assembly-evidence/1','functional_job':114602,'structure_job':114624,
  'sources':hashes,'instances':dict(counts),'projection_values':512,'gated_values':128,'calls':44,
  'log_sha256':sha256((run/'run.log').read_bytes()).hexdigest(),
  'scope':'real M/G/S_P with routed control, finite memory and actual DDR commit; not whole Qwen',
  'full_ffn_execution_accepted':False,'whole_graph_accepted':False,'timing_calibrated':False}
 (OUT/'projection-gated-assembly-receipt.json').write_text(json.dumps(result,indent=2)+'\n')
 print('M/G/S_P assembly verified and source snapshots frozen')
if __name__=='__main__':main()
