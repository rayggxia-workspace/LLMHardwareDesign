"""Parameterized input tasks and raw data; contains no encoded instructions or expected images."""
def pack(values,width=16):return sum((v&((1<<width)-1))<<(width*i) for i,v in enumerate(values))

def example(target,variant=0):
    family,kind=target.split('/');offset=(0,80,200)[variant]
    task=dict(schema='bounded-native-tasks/1',name=target.lower().replace('/','_')+'_'+str(variant),target=target,
              epoch=variant+1,generation=11+variant,job=71+variant,sequence=21+variant,
              image_ids=[197000+variant*100+i for i in range(3)],tokens=[2,3] if variant!=1 else [5,1],
              call_order=[0,1] if variant!=2 else [1,0],buffers=[],tasks=[],transfers=[])
    inputs=[]
    def recipe(block,type_name):
        ops=[];names={}
        def buf(short,base,words=1,initial=False,space='S',values=None):
            name=f'b{block}_{short}';names[short]=name
            task['buffers'].append(dict(name=name,block=block,base_bytes=(base+offset)*16,words=words,space=space,format='RAW128',initial=initial))
            if values is not None:inputs.append(dict(buffer=name,words=values))
            return name
        def ucf(lane,meta,src=(),dst=None):ops.append(dict(op='ucf',lane=lane,meta=meta,src=list(src),dst=dst))
        v=variant+block
        if type_name=='U':
            eps=buf('eps',21,initial=True,values=[1]);gamma=buf('gamma',20,initial=True,values=[pack([1024]*8)])
            raw=buf('raw',40,initial=True,values=[pack([1024,-1024]*4)])
            norm=buf('norm',41);stats=buf('stats',42)
            aa=buf('a',23,initial=True,values=[pack([2+v]*8)]);bb=buf('b',24,initial=True,values=[pack([3+v]*8)]);out=buf('out',25)
            ucf('N',0x100,[eps]);ucf('N',0x81,[raw]);ucf('N',2);ucf('N',0x85,[raw,gamma],norm);ucf('N',7,(),stats);ucf('E',3,[aa,bb],out)
        elif type_name in ('F','C'):
            aa=buf('a',12,initial=True,values=[0]);bb=buf('b',13,initial=True,values=[pack([1024*(v+1)]*2)])
            gate=buf('gate',14);out=buf('out',15);ucf('G',9,[aa,bb],gate);ucf('E',0,[gate,bb],out)
            if type_name=='C':
                state=buf('state',43,initial=True,values=[pack([i+1+v for i in range(4)],32)]);out=buf('rout',44)
                ucf('R',0,[state]);ucf('R',2,(),out)
        elif type_name=='P':
            aa=buf('a',0,4,True,values=[2+v,0,0,0]);bb=buf('b',4,4,True,values=[0xfb0000000000000003,0,0,0]);mm=buf('mat',8)
            gx=buf('gx',12,initial=True,values=[0xd8f02710]);gg=buf('gg',13,initial=True,values=[0x04000200]);out=buf('out',14)
            ops.extend([dict(op='p_load',a=aa,b=bb),dict(op='p_config0'),dict(op='p_config1'),dict(op='p_store',dst=mm),dict(op='p_gate',a=gx,b=gg,dst=out)])
        else:
            count=4
            left=buf('left',0,count,True,'J_FRAGMENT0',values=[pack([100+3*i+7*l+7*v for l in range(8)]) for i in range(count)])
            right=buf('right',8,count,True,'J_FRAGMENT1',values=[pack([-40+i-5*l+7*v for l in range(8)]) for i in range(count)])
            out=buf('out',32,count,False,'J_OUTPUT');ops.extend([dict(op='join',left=left,right=right,dst=out,tag=7),dict(op='release')])
        return ops,out
    source,out=recipe(0,kind)
    if family=='five':sink,_=recipe(1,kind)
    else:
        words=4 if kind=='J' else 1;recv='b1_recv';zero='b1_zero';dest='b1_out'
        task['buffers'].extend([dict(name=recv,block=1,base_bytes=(60+offset)*16,words=words,space='S',format='RAW128',initial=False),
                               dict(name=zero,block=1,base_bytes=(13+offset)*16,words=1,space='S',format='RAW128',initial=True),
                               dict(name=dest,block=1,base_bytes=(14+offset)*16,words=1,space='S',format='RAW128',initial=False)])
        inputs.append(dict(buffer=zero,words=[0]));sink=[dict(op='p_gate',a=recv,b=zero,dst=dest)]
        task['transfers']=[dict(source=out,destination=recv,words=words,format='RAW128')]
    task['tasks']=[dict(block=0,operations=source),dict(block=1,operations=sink)]
    return task,inputs

TARGETS=[f'five/{k}' for k in ('U','F','C','P','J')]+[f'recovery/{k}' for k in ('U','F','C','J')]
