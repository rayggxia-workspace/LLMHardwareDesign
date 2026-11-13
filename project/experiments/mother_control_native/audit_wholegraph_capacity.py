"""Exact control-capacity lowering over exported scopes, not native coverage.

No graph/data/timing simulation. The input preserves unsupported E/N/dynamic
providers. Generated argument operations are a countable lowering template;
deployment descriptor addresses/CRCs remain unbound and no legal hardware
mapping is implied by the instruction counts.
"""
import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path


def image_bytes(instructions, events=9):
    return 128 + 16*((instructions+1)//2) + 16*events


def lower(scopes, distributed):
    # r1=constant descriptor-table high address; r2=len/version, r4=capacity,
    # r5=topology,r6=ABI,r7=zero. r0 pointer_low and r3 expectedCRC change per
    # launch. All six constant loads are paid; no implicit register initial values.
    program=[{'op':'G_MOVI','register':r,'value':'bound_at_deployment'} for r in (1,2,4,5,6,7)]
    calls=0
    for scope in scopes:
        multi=distributed and (scope['kind']=='FFN_candidate_composite' or
              (scope['kind']=='Dot' and scope['op']['layout']==0))
        targets=[0,1,2] if multi else [0]
        for target in targets:
            program += [{'op':'G_MOVI','register':0,'scope':scope['scope_id'],'target':target,'value':'descriptor_pointer_low_UNBOUND'},
                        {'op':'G_MOVI','register':3,'scope':scope['scope_id'],'target':target,'value':'CRC_UNBOUND'},
                        {'op':'G_CALL','scope':scope['scope_id'],'target':target,'token':target}]
            calls+=1
        program += [{'op':'G_WAIT','mask':sum(1<<t for t in targets)}]
    program += [{'op':'G_END'}]
    n=len(program)
    return dict(instructions=n,CALLs=calls,WAITs=len(scopes),GPR_initializations=6,
                PM_image_bytes_9events=image_bytes(n),fits_16KiB=image_bytes(n)<=16384,
                program_template=program,
                hardware_executable=False,
                blockers=['target bindings intentionally unqualified for capacity lower bound',
                          'descriptor pointers and CRC not deployed',
                          'whole FFN and projection outer-scope FSM still required',
                          'dynamic Dot and remaining E/N services not registered'])


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--input',type=Path,required=True);parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    raw=args.input.read_bytes();doc=json.loads(raw);scopes=doc['scopes']
    assert doc['original_op_count']==1086 and doc['fused_FFNs']==36
    assert doc['trace_SHA256']=='6ed2129e2f13842dc53b4ba2135ea41886d1c126d842661dc7d5ac38ffb26f1d'
    lower_bound_calls=doc['fused_FFNs']*58*3
    minimum_gate_up_instructions=doc['fused_FFNs']*58*(3+1) # 3 CALL+one WAIT, even FREE args
    result=dict(schema='issue250-control-capacity-audit/1',input_SHA256=hashlib.sha256(raw).hexdigest(),trace_SHA256=doc['trace_SHA256'],
                original_ops=doc['original_op_count'],exported_scopes=len(scopes),kind_counts=dict(Counter(s['kind'] for s in scopes)),
                capacity=dict(PM_bytes=16384,header_bytes=128,event_records=9,event_record_bytes=16,max_instructions_9events=2014,max_instructions_noevents=2032),
                serial_one_target_optimistic=lower(scopes,False),distributed_static_and_FFN_assumed_outer=lower(scopes,True),
                explicit_58tile_gate_up_only=dict(CALLs=lower_bound_calls,instructions_even_with_zero_argument_cost=minimum_gate_up_instructions,
                    image_bytes_9events=image_bytes(minimum_gate_up_instructions+1),fits_16KiB=False,
                    omitted_real_costs=['G128','quantizer','copy/scatter','Down','all other layer operators','actual MOVI parameters']),
                conclusion='Whole-model straight-line MC does not fit even optimistic unqualified scope templates. A real outer scope, registered graph service fusion, bounded loop ISA or explicitly measured program reload is required; a larger instruction counter alone is insufficient.',
                native_program_compiled=False,whole_system_qualified=False)
    args.out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
    print(json.dumps({k:v for k,v in result.items() if k not in ('serial_one_target_optimistic','distributed_static_and_FFN_assumed_outer')},indent=2))
    for k in ('serial_one_target_optimistic','distributed_static_and_FFN_assumed_outer'):
        print(k,json.dumps({a:b for a,b in result[k].items() if a!='program_template'}))


if __name__=='__main__':main()
