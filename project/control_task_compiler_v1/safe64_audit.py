"""Independent byte-level specification model: no compiler/codec/assembler imports."""
import hashlib,json,zlib,re
from pathlib import Path

def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
def check(ok,why):
    if not ok:raise ValueError('independent audit: '+why)

def record(size,values,defaults=()):
    b=bytearray(size)
    for offset,width,value in [*defaults,*values]:b[offset:offset+width]=value.to_bytes(width,'little')
    return bytes(b)

def admit(task):
    def keys(x,n):check(type(x) is dict and set(x)==set(n.split()),'field set')
    def integer(x,lo,hi):check(type(x) is int and lo<=x<=hi,'integer bound')
    keys(task,'schema name target epoch generation job sequence image_ids tokens call_order buffers tasks transfers')
    check(task['schema']=='safe64-native-tasks/1','task schema')
    check(type(task['name']) is str and re.fullmatch(r'[a-z][a-z0-9_]{0,47}',task['name']),'task identifier')
    check(task['target'] in ['safe64/'+a+'/'+b for a,b in [('U','U'),('F','F'),('C','C'),('P','P'),('J','J'),('U','P'),('F','P'),('C','P'),('J','P')]],'target pair')
    types=task['target'].split('/')[1:]
    for f in ('epoch','generation','job','sequence'):integer(task[f],1,4294967295)
    if 'J' in types:integer(task['epoch'],1,255)
    check(type(task['image_ids']) is list and len(task['image_ids'])==3 and len(set(task['image_ids']))==3,'three image IDs')
    for x in task['image_ids']:integer(x,1,4294967295)
    check(type(task['tokens']) is list and len(task['tokens'])==2 and len(set(task['tokens']))==2,'tokens')
    for x in task['tokens']:integer(x,0,7)
    check(type(task['call_order']) is list and all(type(x) is int for x in task['call_order']) and sorted(task['call_order'])==[0,1],'call order')
    buffers={};ranges=[[],[]];valid=set()
    check(type(task['buffers']) is list and 1<=len(task['buffers'])<=32,'buffers')
    for b in task['buffers']:
        keys(b,'name block base_bytes words space format initial')
        check(type(b['name']) is str and re.fullmatch(r'[a-z][a-z0-9_]{0,47}',b['name']) and b['name'] not in buffers,'buffer identifier')
        integer(b['block'],0,1);integer(b['base_bytes'],0,16368);integer(b['words'],1,1024)
        check(b['base_bytes']%16==0 and b['base_bytes']+b['words']*16<=16384,'S extent')
        check(b['format']=='RAW128' and type(b['initial']) is bool,'buffer format')
        check(b['space'] in (('J_FRAGMENT0','J_FRAGMENT1','J_OUTPUT') if types[b['block']]=='J' else ('S',)),'buffer space')
        check(b['space']!='J_OUTPUT' or not b['initial'],'J output ownership')
        check(not b['space'].startswith('J_FRAGMENT') or b['initial'],'J fragment ownership')
        lo=b['base_bytes'];hi=lo+16*b['words']
        check(all(hi<=a or z<=lo for a,z in ranges[b['block']]),'overlap')
        ranges[b['block']].append((lo,hi));buffers[b['name']]=b
        if b['initial']:valid.update((b['name'],i) for i in range(b['words']))
    check(type(task['tasks']) is list and len(task['tasks'])==2,'two tasks')
    ops={}
    for item in task['tasks']:
        keys(item,'block operations');integer(item['block'],0,1)
        check(item['block'] not in ops,'duplicate task');ops[item['block']]=item['operations']
    def buf(name,block,read=False,space='S',count=1):
        check(type(name) is str and name in buffers,'unknown buffer')
        b=buffers[name];check(b['block']==block and b['space']==space and b['words']>=count,'buffer binding')
        if read:check(all((name,i) in valid for i in range(count)),'read before producer')
        return b
    check(type(task['transfers']) is list and len(task['transfers'])<=2,'one passive route')
    for block in (0,1):
        if block==1 and task['transfers'] and types!=['U','U']:
            e=task['transfers'][0];keys(e,'source destination words format')
            check(types[0] in ('U','F','C','J') and types[1]=='P' and task['call_order']==[0,1] and e['format']=='RAW128','route admission')
            integer(e['words'],1,4);s=buf(e['source'],0,True,space='J_OUTPUT' if types[0]=='J' else 'S',count=e['words']);v=buf(e['destination'],1,count=e['words'])
            check(not v['initial'] and s['words']==v['words']==e['words'],'route extent')
            valid.update((v['name'],i) for i in range(e['words']))
        check(type(ops[block]) is list and 1<=len(ops[block])<=16,'operations')
        kind=types[block];ns=0;rs=0;ps=0;joined=False;released=False;direct=False;p_direct=False;nused=False
        for op in ops[block]:
            check(type(op) is dict,'operation')
            name=op.get('op');dst=None
            if name=='ucf':
                keys(op,'op lane meta src dst');integer(op['meta'],0,2**64-1)
                check(type(op['lane']) is str and type(op['src']) is list,'native fields')
                lane=op['lane'];meta=op['meta'];m=meta&((1<<63)-1);late=bool(meta>>63)
                check(kind in ('U','F','C'),'native type')
                if kind=='U':
                    check(not late and (lane,m) in [('N',256),('N',129),('N',2),('N',133),('N',7),('E',3)],'U recipe')
                    count=([2,3] if lane=='E' else [1] if m in (256,129) else [2] if m==133 else [0])
                    store=lane=='E' or m in (133,7)
                    if lane=='N':
                        check(ns=={256:0,129:1,2:2,133:3,7:3}[m],'N context')
                        if m in (256,129,2):ns+=1
                        if m==133:check(not nused,'N replay window consumed');nused=True
                elif lane=='R':
                    check(kind=='C' and not late and m in (0,2) and rs==(0 if m==0 else 1),'R context')
                    count=[1 if m==0 else 0];store=m==2;rs=1
                else:
                    check((lane,m) in [('G',9),('E',0)],'CF recipe');count=[2];store=True
                    if late and lane=='G':check(not direct,'direct slot live');direct=True;store=False
                    if late and lane=='E':check(direct,'missing direct producer');direct=False
                check(len(op['src']) in count and (op['dst'] is not None)==store,'native arity')
                for n in op['src']:buf(n,block,True)
                if store:dst=buf(op['dst'],block);check(dst['name'] not in op['src'],'in-place output')
            elif name=='u_direct':
                keys(op,'op n_src n_meta e_src e_meta dst')
                check(kind=='U' and ns==3 and not nused and op['n_meta']==133 and op['e_meta']==3,'paired context')
                nused=True
                check(type(op['n_src']) is list and len(op['n_src'])==2 and type(op['e_src']) is list and len(op['e_src'])==2,'paired arity')
                for n in op['n_src']+op['e_src']:buf(n,block,True)
                dst=buf(op['dst'],block);check(dst['name'] not in op['n_src']+op['e_src'],'paired output alias')
            elif name=='p_load':
                keys(op,'op a b');check(kind=='P' and ps==0,'P load')
                for n in (op['a'],op['b']):check(buf(n,block,True,count=4)['base_bytes']%64==0,'P alignment')
                ps=1
            elif name in ('p_config0','p_config1'):
                keys(op,'op');check(kind=='P' and ps==(1 if name=='p_config0' else 2),'P configuration');ps+=1
            elif name=='p_store':
                keys(op,'op dst');check(kind=='P' and ps==3,'P store');ps=4;dst=buf(op['dst'],block)
            elif name=='p_route':
                keys(op,'op');check(kind=='P' and ps in (3,4) and not p_direct,'P direct M context');p_direct=True
            elif name=='p_gate_direct':
                keys(op,'op a b dst');check(kind=='P' and p_direct,'P direct input')
                for n in (op['a'],op['b']):buf(n,block,True)
                dst=buf(op['dst'],block);check(dst['name'] not in (op['a'],op['b']),'P direct alias');p_direct=False
            elif name=='p_gate':
                keys(op,'op a b dst');check(kind=='P','P gate')
                for n in (op['a'],op['b']):buf(n,block,True)
                dst=buf(op['dst'],block);check(dst['name'] not in (op['a'],op['b']),'P alias')
            elif name=='join':
                keys(op,'op left right dst tag');check(kind=='J' and not joined,'JOIN count')
                dst=buf(op['dst'],block,space='J_OUTPUT');integer(dst['words'],1,4);integer(op['tag'],0,2**24-1)
                for n,space in ((op['left'],'J_FRAGMENT0'),(op['right'],'J_FRAGMENT1')):
                    check(buf(n,block,True,space,count=dst['words'])['words']==dst['words'],'JOIN length')
                joined=True;valid.update((dst['name'],i) for i in range(dst['words']))
            elif name=='release':
                keys(op,'op');check(kind=='J' and joined and not released,'J lease');released=True
            else:raise ValueError('independent audit: unsupported semantic operation')
            if dst:valid.add((dst['name'],0))
        check(not direct and not p_direct and (kind!='J' or released),'dangling direct/lease')
    if types==['U','U'] and task['transfers']:
        check(len(task['transfers'])==2,'two U echo edges')
        seen=set()
        for e in task['transfers']:
            keys(e,'source destination words format')
            check(type(e['words']) is int and e['words']==1 and e['format']=='RAW128','U route word')
            check(e['source'] in buffers and e['destination'] in buffers,'U route buffers')
            side=buffers[e['source']]['block'];check(side not in seen and buffers[e['destination']]['block']==1-side,'U direction')
            seen.add(side);src=buf(e['source'],side,True);dst=buf(e['destination'],1-side,count=2)
            check(src['words']==1 and dst['words']==2 and not dst['initial'],'U echo extent')
    else:check(len(task['transfers'])<=1,'one passive route')
    tables=expected_rows(task)
    check(all(len(x)<=16 for x in tables),'execution count')

def expected_rows(task):
    """Specification equations intentionally separate from compiler analysis/lowering."""
    buffers={b['name']:b for b in task['buffers']}
    address=lambda n:buffers[n]['base_bytes']//16
    programs={t['block']:t['operations'] for t in task['tasks']}
    tables=[]
    for block in (0,1):
        table=[]
        for op in programs[block]:
            name=op['op'];args=[0,0,0,0,0,0]
            if name=='ucf':
                native=256
                args[0]={'E':0,'N':1,'G':1,'R':2}[op['lane']]+4*len(op['src'])
                if op['dst'] is not None:args[0]+=16+32*address(op['dst'])
                args[1]=sum(address(n)*1024**i for i,n in enumerate(op['src']))
                args[2]=op['meta']%2**32;args[3]=op['meta']//2**32
            elif name=='u_direct':
                native=260;args=[2,address(op['n_src'][0])+1024*address(op['n_src'][1]),133,0,
                    op['e_meta']+512*address(op['dst']),address(op['e_src'][0])+1024*address(op['e_src'][1])]
            elif name=='p_load':native=272;args[0]=34+2048*address(op['a'])+2097152*address(op['b'])
            elif name in ('p_config0','p_config1'):native=273;args[:2]=[10,37396 if name=='p_config0' else 37392]
            elif name=='p_store':native=273;args[:2]=[1029+4096*address(op['dst']),257]
            elif name=='p_route':native=273;args[:2]=[4194309,257]
            elif name=='p_gate_direct':
                native=274;args[0]=address(op['a'])+1024*address(op['b'])+1048576*address(op['dst'])+1073741824
            elif name=='p_gate':native=274;args[0]=address(op['a'])+1024*address(op['b'])+1048576*address(op['dst'])
            elif name=='join':native=288;args[:2]=[address(op['dst'])+1024*buffers[op['dst']]['words'],task['epoch']*16777216+op['tag']]
            elif name=='release':native=289
            else:raise ValueError('unknown specification operation')
            table.append((native,args))
        tables.append(table)
    if task['transfers']:
        types=task['target'].split('/')[1:]
        if types==['U','U']:
            edges={buffers[e['source']]['block']:e for e in task['transfers']}
            for side in (0,1):
                destination=address(edges[side]['destination']);incoming=address(edges[1-side]['destination']);source=address(edges[side]['source'])
                tables[side]=[(259,[incoming,0,0,0,0,0])]+tables[side]+[(257,[source+1024*destination,0,0,0,0,0]),(258,[0]*6),
                    (259,[incoming+1,0,0,0,0,0]),(257,[incoming+1024*(destination+1),0,0,0,0,0]),(258,[0]*6)]
        elif types[0]!='J':
            e=task['transfers'][0]
            for i in range(e['words']):tables[0].append((257,[address(e['source'])+i+1024*(address(e['destination'])+i),0,0,0,0,0]))
    return tables

def expected_images(task):
    _,left,right=task['target'].split('/')
    kinds={'U':0,'F':1,'C':2,'P':3,'J':4};kind=kinds[left];topology=26443776+kinds[left]*16+kinds[right]
    check(topology==0x01938000+kinds[left]*16+kinds[right],'cohort registry')
    tables=expected_rows(task);result={}
    for index,name in enumerate(('mother','local0','local1')):
        local=index!=0;kind_here=kinds[left if index==1 else right]
        if not local:
            if task['transfers'] and [left,right]!=['U','U']:
                words=[16*2**56+task['tokens'][0]*2**40,17*2**56+2**task['tokens'][0],
                       16*2**56+2**48+task['tokens'][1]*2**40,17*2**56+2**task['tokens'][1],31*2**56]
            else:
                words=[16*2**56+b*2**48+task['tokens'][b]*2**40 for b in task['call_order']]+[17*2**56+sum(2**v for v in task['tokens']),31*2**56]
        else:words=[v for i in range(len(tables[index-1])) for v in (65*2**56+i*2**32,68*2**56+1)]+[79*2**56]
        instructions=b''.join(w.to_bytes(8,'little') for w in words)
        instructions+=b'\0'*((-len(instructions))%16)
        count=len(tables[index-1]) if local else 0
        task_start=128+len(instructions) if local else 0
        exec_start=task_start+64 if local else 0
        body=instructions
        if local:
            body+=record(64,[(0,2,1),(2,1,kind_here),(16,4,len(words)),(20,4,1),(24,4,task['image_ids'][index]),(28,4,topology),(44,4,0x01930001)])
            for native,args in tables[index-1]:
                body+=record(128,[(0,2,1),(4,2,native),(56,4,0x01930001)]+[(64+4*i,4,v) for i,v in enumerate(args)],
                             [(i,1,255) for i in (8,9,10,11,20,21,22,23,24,25)])
        h=record(128,[(0,8,0x313041534943424c),(8,2,2),(10,1,int(local)),(11,1,8),(12,4,128+len(body)),
                     (20,4,len(words)),(24,4,128),(28,2,int(local)),(32,2,count),(36,4,task_start),(44,4,exec_start),
                     (52,4,len(words)),(56,4,int(local)),(60,4,task['image_ids'][index]),(64,4,topology),(68,4,0x01930001),(84,4,0x17630001)])
        result[name]=h+body
    return result

def expected_transport(task):
    buffers={b['name']:b for b in task['buffers']};operations={x['block']:x['operations'] for x in task['tasks']}
    types=task['target'].split('/')[1:];rows=[]
    for e in task['transfers']:
        b=buffers[e['source']]['block'];dest=buffers[e['destination']]['base_bytes']//16
        if types==['U','U']:count,first,stride,tag=2,len(operations[b])+1,3,0
        elif types[b]=='J':
            first=next(i for i,x in enumerate(operations[b]) if x['op']=='join')
            count,stride,tag=e['words'],0,16777216*task['epoch']+operations[b][first]['tag']
        else:count,first,stride,tag=e['words'],len(operations[b]),1,0
        rows.append(dict(direction=b,base_rows=dest,count=count,first_sequence=first,stride=stride,tag=tag))
    return sorted(rows,key=lambda x:x['direction'])

def audit(task,bundle):
    admit(task)
    check(bundle['schema']=='safe64-native-bundle/1','bundle version')
    check(bundle['task_sha256']==hashlib.sha256(canonical(task)).hexdigest(),'task binding')
    _,left,right=task['target'].split('/');kinds={'U':0,'F':1,'C':2,'P':3,'J':4}
    c=json.loads((Path(__file__).resolve().parent.parent/'control_main64_boot_v1/contract.json').read_text())
    check(c['instruction_bits']==64 and c['mother_targets']==2 and c['global_tokens']==8 and
          [p['max_lane_sources'] for p in c['profiles']]==[[3,2],[2,2],[2,2,1],None,None],'machine capability registry')
    check(bundle['target']==dict(name=task['target'],family='safe64',kind=kinds[left],kinds=[kinds[left],kinds[right]],types=[left,right],
          topology=0x01938000+kinds[left]*16+kinds[right],abi=0x01930001,capacity=0x17630001,pm_bytes=16384,instruction_bits=64,image_version=2,
          contract_sha256=hashlib.sha256(canonical(c)).hexdigest(),
          transport_contract_sha256=hashlib.sha256(canonical(json.loads((Path(__file__).resolve().parent.parent/'control_main64_recovery_v1/contract.json').read_text()))).hexdigest()),'target identity and contract')
    check(bundle['transport_plan']==expected_transport(task),'transport route binding')
    check(bundle['schedule']==dict(call_order=task['call_order'],tokens=task['tokens']),'schedule')
    expected=expected_images(task)
    check(set(bundle['images_hex'])==set(bundle['images'])==set(expected),'image roles')
    for index,(name,gold) in enumerate(expected.items()):
        data=bytes.fromhex(bundle['images_hex'][name]);check(data==gold,name+' canonical bytes')
        e=bundle['images'][name]
        check(e==dict(bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),crc32=zlib.crc32(data),
              image_id=task['image_ids'][index],instructions=int.from_bytes(data[20:24],'little'),
              execution_records=int.from_bytes(data[32:34],'little')),name+' manifest')
    return {'passed':True,'images':3,'scope':'independent main64 semantic admission and complete canonical bytes; no compiler/codec imports'}
