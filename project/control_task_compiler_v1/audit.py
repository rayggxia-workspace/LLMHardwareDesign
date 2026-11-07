"""Independent byte-level specification model: no compiler/codec/assembler imports."""
import hashlib,json,zlib

def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
def check(ok,why):
    if not ok:raise ValueError('independent audit: '+why)

def record(size,values,defaults=()):
    b=bytearray(size)
    for offset,width,value in [*defaults,*values]:b[offset:offset+width]=value.to_bytes(width,'little')
    return bytes(b)

def expected_rows(task):
    """Specification equations intentionally separate from compiler analysis/lowering."""
    buffers={b['name']:b for b in task['buffers']}
    address=lambda n:buffers[n]['base_bytes']//16
    programs={t['block']:t['operations'] for t in task['tasks']}
    tables=[]
    for block in (0,1):
        table=[]
        for op in programs[block]:
            name=op['op'];args=[0,0,0,0]
            if name=='ucf':
                native=256
                args[0]={'E':0,'N':1,'G':1,'R':2}[op['lane']]+4*len(op['src'])
                if op['dst'] is not None:args[0]+=16+32*address(op['dst'])
                args[1]=sum(address(n)*1024**i for i,n in enumerate(op['src']))
                args[2]=op['meta']%2**32;args[3]=op['meta']//2**32
            elif name=='p_load':native=272;args[0]=34+2048*address(op['a'])+2097152*address(op['b'])
            elif name in ('p_config0','p_config1'):native=273;args[:2]=[10,37396 if name=='p_config0' else 37392]
            elif name=='p_store':native=273;args[:2]=[1029+4096*address(op['dst']),257]
            elif name=='p_gate':native=274;args[0]=address(op['a'])+1024*address(op['b'])+1048576*address(op['dst'])
            elif name=='join':native=288;args[:2]=[address(op['dst'])+1024*buffers[op['dst']]['words'],task['epoch']*16777216+op['tag']]
            elif name=='release':native=289
            else:raise ValueError('unknown specification operation')
            table.append((native,args))
        tables.append(table)
    if task['transfers']:
        e=task['transfers'][0];sequence=len(tables[0]);prefix=[]
        for i in range(e['words']):
            src=i if task['target']=='recovery/J' else address(e['source'])+i
            dst=address(e['destination'])+i
            tables[0].append((257,[src+1024*dst,0,0,0]))
            prefix.extend([(259,[dst,sequence+i,0,0]),(258,[0,0,0,0])])
        tables[1]=prefix+tables[1]
    return tables

def expected_images(task):
    family,type_name=task['target'].split('/');kind={'U':0,'F':1,'C':2,'P':3,'J':4}[type_name]
    topology=(26411025 if family=='five' else 26412288)+kind
    # Explicit decimal bases above correspond to the two published native profile registries.
    check(topology==((0x01930011 if family=='five' else 0x01930500)+kind),'registry constants')
    tables=expected_rows(task);result={}
    for index,name in enumerate(('mother','local0','local1')):
        local=index!=0;kind_here=kind if index!=2 or family=='five' else 3
        words=([0x10*2**56+b*2**48+task['tokens'][b]*2**40 for b in task['call_order']]+
               [0x11*2**56+sum(2**t for t in task['tokens']),0x1f*2**56]) if not local else [w for i in range(len(tables[index-1])) for w in (0x41*2**56+i*2**32,0x44*2**56+1)]+[0x4f*2**56]
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

def audit(task,bundle):
    check(bundle['schema']=='bounded-native-bundle/1','bundle version')
    check(bundle['task_sha256']==hashlib.sha256(canonical(task)).hexdigest(),'task binding')
    family,type_name=task['target'].split('/');kind={'U':0,'F':1,'C':2,'P':3,'J':4}[type_name]
    check(bundle['target']==dict(name=task['target'],family=family,kind=kind,types=[type_name,type_name if family=='five' else 'P'],topology=(0x01930011 if family=='five' else 0x01930500)+kind,abi=0x01930001,capacity=0x17630001,pm_bytes=16384,instruction_bits=64,image_version=2),'target identity/ABI/capacity')
    check(bundle['schedule']==dict(call_order=task['call_order'],tokens=task['tokens']),'schedule')
    expected=expected_images(task)
    check(set(bundle['images_hex'])==set(bundle['images'])==set(expected),'image roles')
    for index,(name,gold) in enumerate(expected.items()):
        data=bytes.fromhex(bundle['images_hex'][name]);check(data==gold,name+' noncanonical header/program/task/native record or identity')
        e=bundle['images'][name]
        check(e==dict(bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),crc32=zlib.crc32(data),image_id=task['image_ids'][index],instructions=int.from_bytes(data[20:24],'little'),execution_records=int.from_bytes(data[32:34],'little')),name+' manifest')
    return {'passed':True,'images':3,'scope':'independent equations and complete canonical byte comparison; no compiler/assembler imports'}
