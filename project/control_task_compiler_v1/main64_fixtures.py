"""Semantic main64 fixtures; no instruction or descriptor encodings."""
from fixtures import example as old_example,pack
PAIRS=[('U','U'),('F','F'),('C','C'),('P','P'),('J','J'),('U','P'),('F','P'),('C','P'),('J','P')]

def example(pair,variant=0):
    left,right=pair
    if right=='P' and left in ('U','F','C'):
        task,inputs=old_example('recovery/'+left,variant)
        task['call_order']=[0,1]
    else:
        task,inputs=old_example('five/'+left,variant)
        if left!=right:
            other,ii=old_example('five/'+right,variant)
            task['buffers']=[b for b in task['buffers'] if b['block']==0]+[b for b in other['buffers'] if b['block']==1]
            inputs=[x for x in inputs if x['buffer'].startswith('b0_')]+[x for x in ii if x['buffer'].startswith('b1_')]
            task['tasks'][1]=other['tasks'][1]
    task['schema']='main64-native-tasks/1';task['target']='main64/'+left+'/'+right
    task['name']='main64_'+left.lower()+right.lower()+'_'+str(variant)
    offset=(0,80,200)[variant]
    for block,kind in enumerate(pair):
        ops=task['tasks'][block]['operations']
        if kind=='U' and variant:
            name=f'b{block}_c'
            task['buffers'].append(dict(name=name,block=block,base_bytes=(26+offset)*16,words=1,space='S',format='RAW128',initial=True))
            inputs.append(dict(buffer=name,words=[pack([5+variant+block]*8)]))
            next(o for o in ops if o['op']=='ucf' and o['lane']=='E')['src'].append(name)
            if variant==2:
                ops[:]=[o for o in ops if not (o['op']=='ucf' and o['lane']=='N' and o['meta']==133)]
                ops.append(dict(op='u_direct',n_src=[f'b{block}_raw',f'b{block}_gamma'],n_meta=133,
                                e_src=[f'b{block}_a',f'b{block}_b'],e_meta=3,dst=f'b{block}_out'))
        if kind in ('F','C') and variant:
            ops += [dict(op='ucf',lane='G',meta=(1<<63)|9,src=[f'b{block}_a',f'b{block}_b'],dst=None),
                    dict(op='ucf',lane='E',meta=1<<63,src=[f'b{block}_a',f'b{block}_b'],dst=f'b{block}_out')]
        if kind=='P' and variant and not task['transfers']:
            ops += [dict(op='p_route'),dict(op='p_gate_direct',a=f'b{block}_gx',b=f'b{block}_gg',dst=f'b{block}_out')]
    return task,inputs

