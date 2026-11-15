"""Execute the sealed Algo1 instruction package on its selected macro-bound base."""
import argparse,json,importlib.util,time
from pathlib import Path
from collections import Counter
from native_package_runtime import load,execute
from native_tlm_timing import Clock,Dram
from macro_assets import Assets,filehash
from macro_memory import profiles,MacroSram
from macro_memory_transport import SharedMemory
from macro_scheduler import MacroScheduler
from macro_provider_registry import build
def main():
 p=argparse.ArgumentParser()
 for n in ('package','assets','library','config','g_reference','output'):p.add_argument(n,type=Path)
 p.add_argument('--core-ps',type=int,required=True)
 p.add_argument('--sram-config',type=Path)
 p.add_argument('--batch-dram',action='store_true')
 p.add_argument('--result',action='append',required=True)
 a=p.parse_args();manifest,payloads,pages=load(a.package)
 hardware=json.loads(payloads['hardware.json']);wiring=json.loads(payloads['candidate-wiring.json'])
 a.output.mkdir(parents=True,exist_ok=False);clock=Clock()
 assets=Assets(a.assets,manifest,payloads);memory=assets.memory
 sram_profiles,sram_sha=profiles(hardware,manifest['payloads']['hardware.json']['sha256'],a.sram_config)
 srams={n:MacroSram(clock,core_ps=a.core_ps,profile=v) for n,v in sram_profiles.items()}
 spec=importlib.util.spec_from_file_location('native_G_reference',a.g_reference)
 g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
 from macro_dram_batch import BatchDram
 backend_type=BatchDram if a.batch_dram else Dram
 backend=backend_type(clock,a.library,a.config,a.output,credits=hardware['base_rtl_contract']['transport']['entries_per_channel'])
 transport=SharedMemory(clock,backend,hardware['base_rtl_contract'],core_ps=a.core_ps)
 providers,models,provider_stats=build(hardware,wiring,manifest['plan_sha256'],
  clock=clock,transport=transport,memory=memory,srams=srams,g_packet=g.packet,core_ps=a.core_ps)
 scheduler=MacroScheduler(clock,transport,memory,core_ps=a.core_ps)
 calls=Counter();elapsed=Counter();service_busy=Counter();dispatch_wait=Counter();started=time.monotonic()
 report={'plan_sha256':manifest['plan_sha256'],'base_id':hardware['base_id'],
  'asset_manifest_sha256':filehash(a.assets),
  'package_manifest_sha256':filehash(a.package/'manifest.json'),
  'source_sha256':{str(p):filehash(p) for p in [Path(__file__),*Path(__file__).parent.glob('macro_*.py'),
   Path('compiler/native_package_runtime.py'),a.g_reference]},
  'dram_library_sha256':filehash(a.library),'dram_config_sha256':filehash(a.config),'core_ps':a.core_ps,'sram_config_sha256':sram_sha,
  'scope':'all sealed mother CALL/WAIT instructions and hardware-backed macro service execution',
  'program_installation':'preinstalled certified MC page and LC kernel; PM loading time excluded',
  'timing_calibrated':False,'numerically_accepted':False,'delivery_accepted':False}
 def timing(key,issue,dispatch,done):
  calls[str(key)]+=1;elapsed[str(key)]+=done-issue
  service_busy[str(key)]+=done-dispatch;dispatch_wait[str(key)]+=dispatch-issue
  count=sum(calls.values())
  if count%500==0:print(json.dumps({'completed_calls':count,'of':manifest['native_calls'],
   'time_ps':clock.now,'wall_seconds':time.monotonic()-started,
   'service_active_ps_completed_calls':dict(service_busy),
   'dispatch_wait_ps_completed_calls':dict(dispatch_wait),
   'DDR':dict(backend.stats),'transport':dict(transport.stats),
   'SRAM':{n:dict(v.stats) for n,v in srams.items()}}),flush=True)
 try:
  result=execute(a.package,scheduler=scheduler,providers=providers,timing=timing)
  clock.until(transport.drained);transport.close()
  if scheduler.busy or scheduler.terminals:raise ValueError('local terminal not retired')
  regions=json.loads(payloads['storage.json'])['regions'];outputs=[]
  for i,name in enumerate(a.result):
   r=regions[name];path=a.output/f'result-{i:03d}.bin'
   with path.open('wb') as f:
    for offset in range(0,r['bytes'],64):
     f.write(memory(r['base']+offset).slice(0,min(64,r['bytes']-offset)).require())
   outputs.append({'value':name,'file':path.name,'sha256':filehash(path),'exponent':r['exponent'],'bytes':r['bytes']})
  from macro_state import save
  state=save(memory,a.output/'committed-state.bin',plan_sha256=manifest['plan_sha256'],
   asset_manifest_sha256=report['asset_manifest_sha256'])
  report.update(result,status='all_instructions_executed',outputs=outputs,committed_state=state)
 except Exception as e:
  report.update(status='failed',error=repr(e));raise
 finally:
  report.update(completed_calls=sum(calls.values()),time_ps=clock.now,wall_seconds=time.monotonic()-started,
   active_calls=scheduler.active,service_calls=dict(calls),service_elapsed_ps=dict(elapsed),service_active_ps=dict(service_busy),
   dispatch_wait_ps=dict(dispatch_wait),transport=dict(transport.stats),
   DDR=dict(backend.stats),SRAM={n:dict(s.stats) for n,s in srams.items()},memory=dict(memory.stats))
  (a.output/'receipt.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps(report),flush=True)
if __name__=='__main__':main()
