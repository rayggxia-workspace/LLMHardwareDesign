"""Compile actual exported scope sequence into bounded image-v3 MC loops.

This is control representation/ordering evidence. Missing operator providers,
FFN outer FSMs and deployment descriptor contents remain explicit blockers.
No unimplemented service gains numeric/physical qualification from a peer.
"""
import argparse
import hashlib
import json
from pathlib import Path
from assemble_cases import image


def signature(s):
    if s['kind']=='FFN_candidate_composite':
        return ('FFN',s['hidden'],s['mid'],s['group_k'],s['projection_tile_columns'],tuple(s['RF_contexts_each_P'] for _ in range(1)))
    op=s['op']
    return tuple([s['kind']]+[op[k] for k in ('elements','rows','cols','k','batches','shift','layout')]+[len(op['inputs'])])


def targets(s):
    if s['kind']=='FFN_candidate_composite' or (s['kind']=='Dot' and s['op']['layout']==0):
        return [0,1,2]
    # Unqualified capacity/order placeholder, NOT a legal macro binding.
    return [3]


def find_repeat(keys):
    best=None
    for period in range(1,len(keys)//2+1):
        for begin in range(len(keys)-2*period+1):
            if keys[begin:begin+period]!=keys[begin+period:begin+2*period]:
                continue
            repeats=2
            while begin+(repeats+1)*period<=len(keys) and keys[begin:begin+period]==keys[begin+repeats*period:begin+(repeats+1)*period]:
                repeats+=1
            candidate=(period*repeats,repeats,-period,-begin)
            if best is None or candidate>best[0]:best=(candidate,begin,period,repeats)
    if best is None:raise ValueError('no repeated semantic/shape template; refuse assumed36-layer loop')
    return best[1:]


def expand(program,max_steps):
    regs=[0]*8;pc=0;steps=0;calls=[]
    while True:
        if steps>=max_steps:raise ValueError('compiler expansion exceeded true bounded step budget')
        op,a,b,c,x=program[pc];steps+=1
        if op=='MOVI':regs[a]=x
        elif op=='CALL':calls.append(dict(target=a,token=b,reference=regs[0]|regs[1]<<32))
        elif op=='ADDI64':
            value=(regs[a]|regs[a+1]<<32)+x
            assert value<1<<64
            regs[a]=value&0xffffffff;regs[a+1]=value>>32
        elif op=='LOOP':
            assert 0<regs[a]<=65535 and 0<=x<pc
            regs[a]-=1
            if regs[a]:pc=x;continue
        elif op=='WAIT':pass
        elif op=='END':break
        else:raise ValueError(op)
        pc+=1
    return calls,steps


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--input',type=Path,required=True);parser.add_argument('--out',type=Path,required=True);parser.add_argument('--cases',type=Path,required=True);parser.add_argument('--report',type=Path,required=True);args=parser.parse_args()
    raw=args.input.read_bytes();doc=json.loads(raw);scopes=doc['scopes'];keys=[signature(s) for s in scopes]
    begin,period,repeats=find_repeat(keys)
    assert repeats<=65535
    end=begin+period*repeats
    assert keys[begin:end]==keys[begin:begin+period]*repeats
    args.out.mkdir(parents=True,exist_ok=True)
    base=0x100000000
    program=[('MOVI',r,0,0,v) for r,v in enumerate([base&0xffffffff,base>>32,128|(1<<16),0x02510001,25001,0x02500002,0,0])]
    def emit(rows):
        for scope in rows:
            ts=targets(scope)
            for t in ts:program.extend([('CALL',t,t,0,0),('ADDI64',0,0,0,128)])
            program.append(('WAIT',0,0,0,sum(1<<t for t in ts)))
    emit(scopes[:begin]);program.append(('MOVI',7,0,0,repeats));loop_pc=len(program)
    emit(scopes[begin:begin+period]);program.append(('LOOP',7,0,0,loop_pc));emit(scopes[end:]);program.append(('END',0,0,0,0))
    oracle=[]
    for scope in scopes:
        for target in targets(scope):oracle.append(dict(target=target,token=target,reference=base+128*len(oracle),scope_id=scope['scope_id']))
    expanded,steps=expand(program,1_000_000)
    assert expanded==[{k:v for k,v in row.items() if k!='scope_id'} for row in oracle]
    data=image(program,version=3,max_steps=steps+16)
    assert len(data)<=16384, f'actual loop image still too large: {len(data)}'
    mem=args.out/'wholegraph.mem';mem.write_text(''.join(f'{int.from_bytes(data[i:i+16],"little"):032x}\n' for i in range(0,len(data),16)),encoding='ascii')
    target_mem=args.out/'targets.mem';target_mem.write_text(''.join(f'{row["target"]:02x}\n' for row in oracle),encoding='ascii')
    result=dict(schema='wholegraph-MC-control-loop-compile/1',input_SHA256=hashlib.sha256(raw).hexdigest(),trace_SHA256=doc['trace_SHA256'],original_ops=doc['original_op_count'],scopes=len(scopes),
                repeat=dict(prefix_scopes=begin,body_scopes=period,repeats=repeats,suffix_scopes=len(scopes)-end,identified_from_exact_semantic_shape_signatures=True),
                static_program_instructions=len(program),actual_dynamic_instructions_including_loops=steps,PM_image_bytes=len(data),descriptor_table_bytes=128*len(oracle),
                actual_CALLs=len(oracle),image_version=3,capacity_ID='0x02590003',per_CALL_target_reference_matches_unrolled=True,
                complete_control_oracle=oracle,program=program,program_image_SHA256=hashlib.sha256(data).hexdigest(),
                provider_binding='static Dot/FFN three-P target pattern; others unqualified target3 capacity fixture, NOT a hardware mapper result',
                descriptor_table_deployed=False,full_native_execution=False,
                blockers=['new FFN/projection outer-scope FSM','typed descriptor table payload/CRC/deployment image','E/N and dynamic Dot native services','actual LC/copy/quant/M/G programs','joint DDR global credits and physical'])
    args.report.write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
    cases=json.loads(args.cases.read_text());cases.append(dict(name='wholegraph_control_loop',image=str(mem.resolve()),WORDS=len(data)//16,CALLS=len(oracle),CHECK_PTR=1,PTR_START=base,PTR_STRIDE=128,TARGETS_FILE=str(target_mem.resolve()),MIN_ACTIVE=3,DELAY0=80,DELAY1=100,TIMING=1));args.cases.write_text(json.dumps(cases,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('complete_control_oracle','program')},indent=2))


if __name__=='__main__':main()
