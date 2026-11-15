"""Execute every generated instruction using PR260 services and real DRAMsim3.

Only the explicitly selected diagnostic-zero scene is presently materialized.
It is a control/data-movement diagnostic, not numerical model acceptance.
"""
import argparse,json,importlib.util
from pathlib import Path
from functools import lru_cache
from collections import Counter
from hashlib import sha256
from native_package_runtime import load,execute
from native_provider_registry import build
from diagnostic_memory import DiagnosticMemory
from configured_sram import ConfiguredSram,profiles
from native_tlm_timing import Clock,Dram,S128,Scheduler
import native_tlm_projection as projection_module

def main():
    a=argparse.ArgumentParser()
    a.add_argument('package',type=Path);a.add_argument('library',type=Path)
    a.add_argument('config',type=Path);a.add_argument('g_reference',type=Path)
    a.add_argument('output',type=Path)
    a.add_argument('--scene',choices=['diagnostic-zero'],required=True)
    a.add_argument('--core-ps',type=int,required=True)
    a.add_argument('--sram-config',type=Path)
    args=a.parse_args()
    manifest,payloads,pages=load(args.package)
    hardware=json.loads(payloads['hardware.json'])
    if hardware['topology_id']!=manifest['topology']:raise ValueError('hardware topology mismatch')
    args.output.mkdir(parents=True,exist_ok=False)
    clock=Clock();memory=DiagnosticMemory(manifest,payloads,json.loads(payloads['storage.json']))
    dram=Dram(clock,args.library,args.config,args.output,credits=hardware['virtual_memory']['credits'])
    sram_profiles,sram_config_sha=profiles(hardware,manifest['payloads']['hardware.json']['sha256'],args.sram_config)
    srams={g:ConfiguredSram(clock,core_ps=args.core_ps,profile=row) for g,row in sram_profiles.items()}
    spec=importlib.util.spec_from_file_location('block_g_reference',args.g_reference)
    g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
    # Exact memoization of pure arithmetic contributions. All DDR, SRAM, and
    # service timing events still execute. This does not cache any schedule.
    original=projection_module.accumulate
    @lru_cache(maxsize=512)
    def contribution(weights,activation,shift,head16):
        result=[0]*8;original(weights,activation,shift,result,head16)
        return tuple(result)
    def cached(weights,activation,shift,prefix,head16):
        if head16:return original(weights,activation,shift,prefix,head16)
        for i,value in enumerate(contribution(weights,tuple(activation),shift,head16)):
            prefix[i]+=value
            if not -(1<<31)<=prefix[i]<1<<31:raise ValueError('native projection overflow')
    projection_module.accumulate=cached
    providers,models=build(hardware,json.loads(payloads['candidate-wiring.json']),
                          clock=clock,dram=dram,memory=memory,srams=srams,
                          g_packet=g.packet,core_ps=args.core_ps)
    scheduler=Scheduler(clock,dram,memory,core_ps=args.core_ps)
    stats=Counter();durations=Counter()
    def timing(key,issued,dispatched,done):
        stats[str(key)]+=1;durations[str(key)]+=done-issued
        total=sum(stats.values())
        if total%1000==0:print(json.dumps({'calls_completed':total,'time_ps':clock.now,'ddr':dict(dram.stats)}),flush=True)
    report={'scene':args.scene,'plan_sha256':manifest['plan_sha256'],
            'hardware_sha256':manifest['payloads']['hardware.json']['sha256'],
            'package_manifest_sha256':sha256((args.package/'manifest.json').read_bytes()).hexdigest(),
            'timing_calibrated':False,'numerically_accepted':False,'delivery_accepted':False,
            'sram_config_sha256':sram_config_sha,
            'sram_parameters':{g:vars(p) for g,p in sram_profiles.items()},
            'service_access_bits':128,
            'sram_width_scope':'external port widths; individual 128-bit service requests are not coalesced'}
    try:
        result=execute(args.package,scheduler=scheduler,providers=providers,timing=timing)
        dram.close()
        report.update(result,status='all_instructions_executed',time_ps=clock.now,
                      completed_calls=sum(stats.values()),service_calls=dict(stats),
                      service_elapsed_ps=dict(durations),ddr=dict(dram.stats),
                      sram={g:dict(s.stats) for g,s in srams.items()})
    except Exception as e:
        report.update(status='failed',error=repr(e),completed_calls=sum(stats.values()),time_ps=clock.now)
        (args.output/'receipt.json').write_text(json.dumps(report,indent=2)+'\n')
        raise
    (args.output/'receipt.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report),flush=True)
if __name__=='__main__':main()
