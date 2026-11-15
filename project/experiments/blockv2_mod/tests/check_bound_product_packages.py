from pathlib import Path
from hashlib import sha256
import sys,json,copy
ROOT=Path.cwd();sys.path[:0]=[str(ROOT/'compiler'),str(ROOT/'hardware')]
from native_package_runtime import load
from native_product_binding import validate
from verify_loop_dp import verify
folder=Path(sys.argv[1]);graphs=Path(sys.argv[2]);rows=[];negative=[]
for stage in ('prefill','decode'):
 manifest,payloads,pages=load(folder/(stage+'-package'))
 plan=json.loads((graphs/(stage+'-plan')/'plan.json').read_text())
 expected=sha256(json.dumps({k:v for k,v in plan.items() if k!='plan_sha256'},sort_keys=True,separators=(',',':')).encode()).hexdigest()
 assert expected==plan['plan_sha256']==manifest['plan_sha256']
 hardware=json.loads(payloads['hardware.json']);wiring=json.loads(payloads['candidate-wiring.json'])
 assert hardware==plan['hardware'] and manifest['rtl_wiring_complete']
 assert wiring['rtl_binding_complete'] and not wiring['physical_binding_complete']
 assert len(plan['calls'])==manifest['native_calls']
 assert json.loads(payloads['selected-compute-requirements.json'])==plan['wiring']
 verify(plan['search_tasks'],plan['search_hardware'],plan['search_plan'])
 # Adding a resolved wiring bundle must not rewrite the actual issued binaries.
 old=graphs/(stage+'-package')
 for name,data in payloads.items():
  if name.endswith('.bin'):assert data==(old/name).read_bytes(),name
 rows.append({'stage':stage,'plan_sha256':plan['plan_sha256'],'base_id':hardware['base_id'],
  'calls':manifest['native_calls'],'MC_pages':len(pages),'local_kernel_bytes':len(payloads['local-kernel.bin']),
  'binary_programs_unchanged_by_wiring_binding':True,'RTL_binding_complete':True,'execution_accepted':False})
 if stage=='prefill':
  for case in ('wrong_base','wrong_plan','extra_macro','wrong_source','incomplete'):
   bad=copy.deepcopy(wiring)
   if case=='wrong_base':bad['base_id']='foreign'
   elif case=='wrong_plan':bad['plan_sha256']=['foreign']
   elif case=='extra_macro':bad['functional_instances']['P0.hidden']='g_s32'
   elif case=='wrong_source':bad['RTL_sources'][next(iter(hardware['base_rtl_contract']['RTL_sources']))]='0'*64
   else:bad['rtl_binding_complete']=False
   try:validate(bad,manifest['plan_sha256'],hardware)
   except ValueError:negative.append(case)
   else:raise AssertionError('bad product admitted: '+case)
result={'packages':rows,'negative_checks':negative,'whole_base_accepted':False,'TLM_executed':False}
(folder/'verification.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
