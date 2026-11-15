"""Bind current plans to explicit selected RTL, with source-matched full assembly evidence."""
from pathlib import Path
from hashlib import sha256
import argparse,json,subprocess,sys,shutil
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'hardware'),str(ROOT/'compiler')]
from native_selected_endpoint_bindings import build
from native_static_wiring_union import merge
def materialize(plans,out,hardware_path,receipt_path):
 out=Path(out);out.mkdir(parents=True,exist_ok=False)
 hardware=json.loads(Path(hardware_path).read_text())
 for p in plans:
  base=dict(p['hardware']);base.pop('native_dispatch_overlay',None)
  if base!=hardware:raise ValueError('plan differs from specified base')
 wiring=merge([build(p) for p in plans]);known=out/'selected-compute-endpoints.json'
 known.write_text(json.dumps(wiring,indent=2)+'\n')
 subprocess.run([sys.executable,str(ROOT/'hardware/build_nine_control_plane.py'),str(known)],check=True)
 subprocess.run([sys.executable,str(ROOT/'hardware/build_selected_nine_assembly.py'),str(known),str(hardware_path)],check=True)
 assembly=json.loads((ROOT/'hardware/selected-nine-assembly.json').read_text())
 proof=json.loads(Path(receipt_path).read_text())
 # A different selected wiring must be elaborated again, never blessed using
 # another product's passing fixture. Hash comparison includes both assemblies.
 for name,h in proof['source_sha256'].items():
  p=Path(name)
  if not p.is_file() or sha256(p.read_bytes()).hexdigest()!=h:
   raise ValueError('selected RTL differs from assembly evidence; elaborate this product: '+name)
 if not proof.get('elaboration_accepted'):raise ValueError('assembly not structurally admitted')
 if proof['functional_instances']!=assembly['functional_instances']:raise ValueError('macro set changed')
 assembly['elaboration_accepted']=True
 assembly['elaboration_receipt_sha256']=sha256(Path(receipt_path).read_bytes()).hexdigest()
 (ROOT/'hardware/selected-nine-assembly.json').write_text(json.dumps(assembly,indent=2)+'\n')
 control=assembly['parent_assembly']
 full={'schema':'native-product-wiring/1','plan_sha256':wiring['plan_sha256'],
  'base_id':hardware['base_id'],'base_rtl_contract_sha256':hardware['base_rtl_contract_sha256'],
  'functional_instances':assembly['functional_instances'],
  'selected_macro_connections':assembly['selected_data_connections'],
  'selected_memory_connections':control['selected_memory_links'],
  'declared_constants':assembly['declared_constants'],'inactive_product_inputs':assembly['inactive_product_inputs'],
  'fixed_control_implementation':{'module':'native_nine_control_plane','sources':control['sources'],
    'scope':'nine actual LC identities, packet switch, descriptor transport, finite PM and shared read/write ownership'},
  'RTL_sources':proof['source_sha256'],'elaboration_receipt_sha256':sha256(Path(receipt_path).read_bytes()).hexdigest(),
  'rtl_binding_complete':True,'physical_binding_complete':False,'numerical_execution_accepted':False,
  'scope':'same-plan selected RTL connectivity; physical views/timing and joined execution are separate'}
 (out/'candidate-wiring.json').write_text(json.dumps(full,indent=2)+'\n')
 for rel in ('rtl/control/native_nine_control_plane.sv','rtl/native_selected_nine_assembly.sv',
             'hardware/nine-control-plane.json','hardware/selected-nine-assembly.json'):
  p=out/rel;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/rel,p)
 return full
def main():
 p=argparse.ArgumentParser();p.add_argument('--plan',action='append',type=Path,required=True)
 p.add_argument('--hardware',type=Path,required=True);p.add_argument('--assembly-receipt',type=Path,required=True)
 p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 result=materialize([json.loads(x.read_text()) for x in a.plan],a.output,a.hardware,a.assembly_receipt)
 print(json.dumps({'plans':result['plan_sha256'],'base_id':result['base_id'],'rtl_binding_complete':True,
 'physical_binding_complete':False}))
if __name__=='__main__':main()
