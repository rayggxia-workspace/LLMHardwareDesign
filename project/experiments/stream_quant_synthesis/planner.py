"""DP/greedy share one state-dependent service transition.

Exact only for the documented additive estimator and one persistent A object
per P. Whole-operator barriers permit an empty resource calendar at each step.
The resulting choices are replayed by the finite-resource SystemC model.
"""
from dataclasses import dataclass
import json
from pathlib import Path


def div(a,b):return (a+b-1)//b


def graph(path):
    lines=Path(path).read_text().splitlines();nt,no,tokens=map(int,lines[0].split())
    tensors=[tuple(map(int,l.split())) for l in lines[1:nt+1]]
    ops=[]
    for index,line in enumerate(lines[nt+1:]):
        p=line.split();kind=p[1]
        if kind!='Dot':continue
        out,elements,r,n,k,batches,shift,layout,ni=map(int,[p[0]]+p[2:10])
        inputs=list(map(int,p[10:]))
        assert len(inputs)==ni
        ops.append(dict(index=index,out=out,rows=r,cols=n,k=k,batches=batches,layout=layout,
                        aid=inputs[0],abytes=div(tensors[inputs[0]][1]*tensors[inputs[0]][2],8)))
    assert len(lines)==1+nt+no
    return ops


@dataclass(frozen=True)
class State:
    cache:int=-1


def transition(state, op, action, tensors, bw_mb=17100,pcount=2):
    """Return (new state, integer cycle cost, auditable ledger), or illegal."""
    kt,ctx,keep=action
    if kt not in (64,128,256) or ctx not in (1,8) or keep not in (0,1,2):raise ValueError('bad service')
    eligible=op['layout']==0 and op['rows']==1 and op['batches']==1
    prior_bytes=tensors.get(state.cache,0)
    hit=eligible and state.cache==op['aid']
    reserved=prior_bytes if state.cache!=op['aid'] else 0
    capacity=16384-reserved
    workspace=1536+96
    abytes=op.get('abits',32)//8
    a=op['k']*abytes
    b=2*kt*8
    if capacity<workspace+2*kt*abytes+b:return None
    resident=eligible and a+b+workspace<=capacity
    groups=div(div(op['cols'],8),pcount)
    blocks=div(op['k'],kt)
    # Context reuse is selected only when full A cannot reside, as in #247.
    repeats=1 if resident else div(groups,ctx)
    aload=0 if hit else op['k']*abytes*repeats*op['rows']*op['batches']
    weights=op['k']*op['cols']*op['batches'] if op['layout']==0 else op['k']*op['cols']*4*op['batches']
    dma=div((weights+aload*pcount)*300,bw_mb)
    mac=div(op['k'],8)*groups*op['rows']*op['batches']
    sread=div(aload,64)
    controls=blocks*groups*20+groups*12
    # A retention changes a descriptor. It is charged and replayed, never a bonus.
    descriptor=1 if keep else 0
    if keep==0:target=-1
    elif keep==1:target=state.cache
    else:
        if not resident or not eligible or op['abytes']>12288:return None
        target=op['aid']
    cost=max(dma,mac+sread+controls)+descriptor
    return State(target),cost,dict(cache_hit=hit,A_DDR_bytes=aload*pcount,weight_bytes=weights,
                                 reserved_bytes=reserved,estimated_cycles=cost)


def compile_plan(ops,method='dp',bw_mb=17100,pcount=2,abits=0):
    if method not in ('dp','greedy'):raise ValueError('bad method')
    ops=[dict(o) for o in ops]
    if abits:
        for o in ops:
            if o['layout']==0 and o['rows']==1:
                o['abytes']=div(o['abytes']*abits,32);o['abits']=abits
    tensors={o['aid']:o['abytes'] for o in ops}
    last={o['aid']:i for i,o in enumerate(ops)}
    frontier={State():(0,[])};peaks=[]
    for i,op in enumerate(ops):
        future={}
        for state,(cost,history) in frontier.items():
            for k in (64,128,256):
                for ctx in (1,8):
                    for keep in (0,1,2):
                        action=(k,ctx,keep);step=transition(state,op,action,tensors,bw_mb,pcount)
                        if step is None:continue
                        target,delta,ledger=step
                        # Drop dead cache objects. Future transitions cannot observe them.
                        if target.cache!=-1 and last.get(target.cache,-1)<=i:target=State()
                        row=dict(action=list(action),op_index=op['index'],aid=op['aid'],before=state.cache,after=target.cache,**ledger)
                        candidate=(cost+delta,history+[row])
                        if target not in future or candidate[0]<future[target][0]:future[target]=candidate
        if not future:raise ValueError('no legal finite-S service')
        if method=='greedy':
            winner=min(future,key=lambda s:(future[s][0],s.cache));future={winner:future[winner]}
        frontier=future;peaks.append(len(frontier))
    state,(cost,rows)=min(frontier.items(),key=lambda p:(p[1][0],p[0].cache))
    return dict(method=method,estimated_cycles=cost,peak_frontier=max(peaks,default=0),rows=rows,
                state='one immutable full-A object per private P S; common symmetric allocation; operator barriers',
                optimality='exact additive estimator only; independent SystemC replay decides actual performance')


def emit(plan,path):
    Path(path).write_text(''.join(f"{r['action'][0]} {r['action'][1]} {r['action'][2]}\n" for r in plan['rows']))


def bundle(plan,path,pcount=2,abits=0,beat_bytes=64):
    """Same binding IDs in executable research IR and endpoint requirements.

    These are logical endpoint roles, not invented LEF pins or #180 binary ISA.
    Deployment is explicitly rejected until real views and lowering exist.
    """
    programs=[]
    for i,row in enumerate(plan['rows']):
        programs.append(dict(binding_id='dot-'+str(i),graph_op_index=row['op_index'],
                             opcode='DOT_SERVICE',P_instances=list(range(pcount)),
                             K_tile=row['action'][0],contexts=row['action'][1],cache_action=row['action'][2],
                             matrix_service='candidate_W8_K16_N8' if abits else 'legacy_S32_W8_K8_N8',
                             completion='final local S write ACK and output DMA ACK',depends_on=[] if not i else ['dot-'+str(i-1)]))
    nets=[]
    for p in range(pcount):
        for driver,sink,width in [(f'DMA.P{p}.rx',f'P{p}.Bfill_adapter.in',8*beat_bytes),
                                  (f'P{p}.Bfill_adapter.out',f'P{p}.Bbuffer.fill',512),
                                  (f'P{p}.Bbuffer.out',f'P{p}.M.B',1024 if abits else 512),
                                  (f'P{p}.S.A',f'P{p}.Aadapter.in',128),
                                  (f'P{p}.Aadapter.out',f'P{p}.M.A',(16 if abits else 8)*(abits or 32))]:
            nets.append(dict(driver=driver,sink=sink,data_width=width,protocol_signals=['VALID','READY'],
                             physical_pin_binding=None,prewire=False,binding_ids=[r['binding_id'] for r in programs]))
    result=dict(schema_version=1,program_ir=programs,connections=nets,
                private_S_bytes_per_P=16384,control_group_is_hard_box=False,
                deployment_qualified=False,binary_ISA_lowered=False,complete_static_net_set=False,
                connections_scope='operand-path research requirements only; result, clock, control and ACK lowering pending',
                hardware_note='wide DDR needs a prefabricated beat adapter; role names are not physical pins',
                missing=['new leaf pin/LEF/Liberty/ODB','native LC/MC binary lowering','whole S/DMA/ACK RTL integration','physical acceptance'])
    Path(path).write_bytes((json.dumps(result,indent=2)+'\n').encode('utf8'))
    return result


def test():
    # State dependence: same service, same op, a live A eliminates DDR work.
    op=dict(index=0,aid=4,abytes=8192,k=2048,cols=2048,rows=1,batches=1,layout=0)
    cold=transition(State(),op,(256,1,0),{4:8192})
    hot=transition(State(4),op,(256,1,0),{4:8192})
    assert hot[2]['A_DDR_bytes']==0 and cold[2]['A_DDR_bytes']>0
    # Exhaustive independent path enumeration on a small branching cache case.
    ops=[dict(op,index=i,aid=4 if i!=2 else 5) for i in range(3)]
    paths=[(State(),0)]
    for o in ops:
        expanded=[]
        for state,cost in paths:
            for k in (64,128,256):
                for c in (1,8):
                    for keep in (0,1,2):
                        step=transition(state,o,(k,c,keep),{4:8192,5:8192})
                        if step:expanded.append((step[0],cost+step[1]))
        paths=expanded
    dp=compile_plan(ops);greedy=compile_plan(ops,'greedy')
    assert dp['estimated_cycles']==min(c for _,c in paths)
    assert dp['estimated_cycles']<=greedy['estimated_cycles']
    return dict(passed=True,exhaustive_paths=len(paths),DP=dp['estimated_cycles'],greedy=greedy['estimated_cycles'],
                cold_A_bytes=cold[2]['A_DDR_bytes'],hot_A_bytes=hot[2]['A_DDR_bytes'])


if __name__=='__main__':print(json.dumps(test()))
