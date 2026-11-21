"""Full-size native peer compilation / RTL timing, not a reduced model.

A zero data image qualifies only data-independent dense timing. Real-checkpoint
numerical quality and measured board power remain separate required evidence.
"""
import argparse
import dataclasses
import hashlib
import json
from pathlib import Path
import sys
import time


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser()
    for name in ('peer','checkpoint','reference','output'):p.add_argument(name,type=Path)
    p.add_argument('--format',choices=['int8','fp4'],required=True)
    p.add_argument('--cores',type=int,default=10)
    p.add_argument('--compile-only',action='store_true')
    a=p.parse_args()
    if a.cores<1:raise ValueError('positive CPU allocation required')
    a.output.mkdir(exist_ok=False);sys.path.insert(0,str(a.peer))
    import numpy as np
    from opentpu.llm import load_spec
    from opentpu.target import config,load,sim_uarch,arch_hash
    ref=json.loads((a.reference/'receipt.json').read_text())
    tokens=json.loads((a.reference/'tokens.json').read_text())
    if ref['checkpoint_files_sha256']['config.json']!=sha(a.checkpoint/'config.json'):
        raise ValueError('peer and HF reference checkpoint differ')
    pos=ref['prompt_tokens']; cfg=config('ypcb-00338:m4');target=load('ypcb-00338:m4')
    spec=load_spec(a.checkpoint)
    if (spec.layers,spec.hidden,spec.vocab)!=(36,2048,151936):
        raise ValueError('not complete pinned Qwen2.5-3B')
    if cfg.DRAM_BYTES!=4<<30 or not cfg.PAIR or not cfg.SEQ_WC:
        raise ValueError('native target capacity/features unexpectedly downgraded')
    cap=((pos+ref['generated_tokens']+255)//256)*256
    image=spec.image(cfg,cap,rows=16,wformat=a.format,head_format='int8',lookup=True)
    progs=image.compile_step(pos,tok=tokens['generated'][0])
    prog_files=[]
    for i,program in enumerate(progs):
        path=a.output/('program-%d.npy'%i)
        np.save(path,np.array([ins.w for ins in program],dtype=np.uint32))
        prog_files.append({'file':path.name,'instructions':len(program),'sha256':sha(path)})
    receipt={'scope':'complete native peer compile; optional zero-data RTL dense timing only',
        'checkpoint_config_sha256':sha(a.checkpoint/'config.json'),
        'reference_receipt_sha256':sha(a.reference/'receipt.json'),
        'reference_tokens_sha256':sha(a.reference/'tokens.json'),
        'source_sha256':sha(Path(__file__)),
        'overlay_receipt_sha256':sha(a.peer/'qwen2-overlay.json'),
        'target_sha256':sha(a.peer/'targets/ypcb-00338.toml'),
        'target_config':dataclasses.asdict(cfg),'target_arch_hash':format(arch_hash(cfg),'08x'),
        'uarch':sim_uarch('ypcb-00338:m4'),'model':dataclasses.asdict(spec),
        'position':pos,'query_tokens':1,'cache_capacity_tokens':cap,
        'format':a.format,'head_format':'int8','image_bytes':image.nbytes,
        'programs':prog_files,'native_program_compiled':True,
        'zero_data_timing':not a.compile_only,'full_model_numeric_qualified':False,
        'energy_qualified':False,'board_execution_qualified':False}
    path=a.output/'receipt.json';path.write_text(json.dumps(receipt,indent=2)+'\n')
    print('COMPILED '+json.dumps({k:receipt[k] for k in ['position','format','image_bytes','programs']}),flush=True)
    if a.compile_only:return
    from opentpu import rtlsim
    from opentpu.profile import ddr3_plusargs
    flags=list(rtlsim.VFLAGS); rtlsim.VFLAGS=list(flags)
    rtlsim.VFLAGS[rtlsim.VFLAGS.index('-j')+1]=str(a.cores)
    mhz=target.platform['core_mhz']
    plus=rtlsim.ldc_plusargs(1066,mhz)+ddr3_plusargs(3200/3,mhz)[2:]
    before=time.monotonic()
    # This allocation is the actual image size, with actual four-GiB addressing
    # in cfg. No two-GiB co-sim helper cap excludes the stronger int8 candidate.
    dram=np.zeros(image.nbytes,np.uint8)
    _,_,stats=rtlsim.run(cfg,progs,[dram],uarch=sim_uarch('ypcb-00338:m4'),
        axi=True,boot=True,stall=0,bw=100,lat=round(.3*mhz),max_cycles=1<<40,ldc=1066,
        plusargs=['+axi_dram=1','+axi_map=1']+plus)
    cycles=int(stats['cycles'])
    if cycles<=0 or stats.get('error'):raise ValueError('native RTL run failed')
    receipt.update(rtl_cycles=cycles,assumed_target_mhz=mhz,
        seconds=cycles/(mhz*1e6),tokens_per_second=mhz*1e6/cycles,
        host_wall_seconds_not_device=time.monotonic()-before,
        build_flags_before=flags,build_flags_actual=rtlsim.VFLAGS,
        stats=stats,verilator_version=rtlsim.verilator_version(),
        timing_boundary='one full decode step including embedding/rotary device gathers and final logits; no host argmax',
        physical_frequency_independently_verified_by_this_task=False)
    path.write_text(json.dumps(receipt,indent=2,default=str)+'\n')
    print(json.dumps(receipt,default=str))

if __name__=='__main__':main()
