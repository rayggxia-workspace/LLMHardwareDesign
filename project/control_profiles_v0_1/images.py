"""Pack existing ISA records; separately validate the explicit candidate ABI."""
import hashlib,json,pathlib,sys
HERE=pathlib.Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'control_isa_v0_1'))
import codec
SPEC=json.loads((HERE/'profiles.json').read_text(encoding='utf-8'))
ABI=SPEC['research_native_abi_id']; TOPOLOGY=SPEC['topology_id']
RES=codec.SCHEMA['resources']; TYPES=codec.SCHEMA['block_types']
SECTIONS=[('instruction',16),('task',64),('object',64),('execution',128),('transfer',64),('event_binding',16)]
def need(v,m):
    if not v: raise ValueError(m)
def sha(b): return hashlib.sha256(b).hexdigest()
def assemble(role,program,records,number,mask=0):
    words=codec.check_program(program,role); payload=bytearray(); h=dict(role=int(role=='local'),entry_pc=0,max_steps=256,
        resource_mask=mask,program_image_id=number,topology_id=TOPOLOGY,native_abi_id=ABI,capacity_profile_id=ABI,scalar_parameter_words=8 if role=='mother' else 0)
    for name,size in SECTIONS:
        rows=[x.to_bytes(16,'little') for x in words] if name=='instruction' else [codec.pack_record(name,x) for x in records.get(name,[])]
        h[name+'_count']=len(rows); h[name+'_offset']=128+len(payload) if rows else 0; payload.extend(b''.join(rows))
    h['total_bytes']=128+len(payload); data=codec.pack_record('image_header',h)+payload
    return bytes(data)
def parse(data,kind=None):
    h=codec.unpack_record('image_header',data[:128]); need(h['native_abi_id']==h['capacity_profile_id']==ABI and h['topology_id']==TOPOLOGY,'candidate ABI/capacity/topology')
    need(h['total_bytes']==len(data) and len(data)%16==0 and h['instruction_offset']==128 and 0<h['instruction_count']<=256,'image size/count')
    role='local' if h['role'] else 'mother'; records={}; pos=128
    for name,size in SECTIONS:
        count=h[name+'_count']; need(h[name+'_offset']==(pos if count else 0),'contiguous sections')
        rows=[data[pos+i*size:pos+(i+1)*size] for i in range(count)]; need(all(len(x)==size for x in rows),'truncated record')
        records[name]=[int.from_bytes(x,'little') for x in rows] if name=='instruction' else [codec.unpack_record(name,x) for x in rows]; pos+=count*size
    need(pos==len(data) and not records['transfer'] and not records['event_binding'],'candidate section capability')
    program=[codec.decode_instruction(w,role) for w in records['instruction']]; codec.check_program(program,role)
    if role=='local':
        need(kind in SPEC['profiles'] and h['resource_mask']==SPEC['profiles'][kind]['resource_mask'] and h['scalar_parameter_words']==0,'local profile mask')
        need(1<=len(records['task'])<=2 and len(records['object'])==1,'local capacities')
        obj=records['object'][0]; need(obj['base_bytes']==0 and obj['length_bytes']==obj['capacity_bytes']==16 and obj['native_abi_id']==ABI,'scratch object')
        for t in records['task']:
            need(t['block_type']==TYPES[kind] and t['program_image_id']==h['program_image_id'] and t['native_abi_id']==ABI and t['topology_id']==TOPOLOGY and
                t['argument_mask']==255 and t['required_resources']==h['resource_mask'] and t['input_object_mask']==t['output_object_mask']==1 and
                t['parameter_base']==4096 and t['parameter_bytes']==32 and t['retained_object_mask']==t['retained_context_mask']==0 and t['max_steps']==128 and
                0<=t['entry_pc']<len(program),'task capability/entry')
        for e in records['execution']:
            r=e['resource']; need(h['resource_mask']&(1<<r) and r!=RES['S'] and e['native_abi_id']==ABI,'unreachable candidate execution')
            publish=e['service']==5
            need((publish and kind=='C' and r==RES['R'] and e['native_op']==0xf1ff and e['native0']==3) or
                (not publish and e['service']==0 and e['native_op']==0xf100+r and e['native0'] in (0,1,2,4)),'unregistered candidate service')
            need(e['count']==1 and e['stride_bytes']==16 and e['src0'] in (0,255) and e['dst']==0 and e['src1']==e['src2']==255 and e['context_id']==0 and
                e['completion']==(0 if publish else 1) and all(e[k]==255 for k in ['count_reg','src0_offset_reg','src1_offset_reg','src2_offset_reg','dst_offset_reg','parameter_index_reg']) and
                all(e[k]==0 for k in ['src0_offset','src1_offset','src2_offset','dst_offset','native2','native3','native4','native5','native6','native7']), 'candidate static descriptor')
            need((e['native0']==1 and kind=='C' and r==RES['R'] or e['native0']!=1) and
                 (e['native0']==2 and r==RES['E'] and e['native1'] in (1,2) or e['native0']==4 and kind in ('U','F') and r==RES[SPEC['profiles'][kind]['compute_order'][0]] and e['src0']==255 and e['native1'] in (1,2) or e['native0'] not in (2,4) and e['native1']==0),'candidate action/profile')
            need((e['parameter_ref'],e['parameter_bytes'])==((4096,32) if e['native0'] else (0,0)),'declared immutable parameters')
        need(all(ins['op'] in ['L_OPEN','L_EXEC','L_WAIT','L_ARG','L_MOVI','L_ADDI','L_LOOP','L_BRANCH','L_DROP','L_END','L_FAIL','NOP'] and
            (ins['op']!='L_FAIL' or ins['x']<=65535) for ins in program),'local instruction capability')
    else:
        need(h['resource_mask']==0 and h['scalar_parameter_words']==8 and not any(records[n] for n in ['task','object','execution']),'mother capability')
        need(all(ins['op'] in ['G_PARAM','G_MOVI','G_BRANCH','G_LOOP','G_CALL','G_WAIT','G_END','G_FAIL','NOP'] and
            (ins['op']!='G_FAIL' or ins['x']<=65535) for ins in program),'mother instruction capability')
    return dict(header=h,records=records,program=program,kind=kind,bytes=data)
def execution(r,action=0,receipt=0,publish=False,read=True):
    return dict(resource=RES[r],service=5 if publish else 0,native_op=0xf1ff if publish else 0xf100+RES[r],src0=0 if read else 255,dst=0,
        context_id=0,completion=0 if publish else 1,count=1,stride_bytes=16,parameter_ref=4096 if action else 0,parameter_bytes=32 if action else 0,
        native_abi_id=ABI,native0=action,native1=receipt)
def local_image(kind,number,state=False,receipt=0):
    order=SPEC['profiles'][kind]['compute_order']; execs=[execution(r,1 if state and r=='R' else 4 if receipt and i==0 else 2 if receipt and i==len(order)-1 else 0,
        receipt if receipt and i in (0,len(order)-1) else 0,read=i!=0) for i,r in enumerate(order)]
    p=[dict(op='L_OPEN',a=0),dict(op='L_ARG',a=0,b=5),dict(op='L_MOVI',a=7,x=0x1234),dict(op='L_EXEC',a=RES[order[0]],b=0,c=0),dict(op='L_WAIT',x=1),dict(op='L_ARG',a=4,b=6),
       dict(op='L_BRANCH',a=4,x=7,y=9),dict(op='L_EXEC',a=RES[order[1]],b=0,c=1),dict(op='L_WAIT',x=1)]
    for i,r in enumerate(order[2:],2): p.extend([dict(op='L_EXEC',a=RES[r],b=0,c=i),dict(op='L_WAIT',x=1)])
    p.extend([dict(op='L_ADDI',a=7,x=1),dict(op='L_LOOP',a=0,x=3),dict(op='L_DROP',a=0),dict(op='L_END')]); entries=[0]
    if state:
        entries.append(len(p)); idx=len(execs); execs.append(execution('R',3,publish=True,read=False))
        p.extend([dict(op='L_OPEN',a=0),dict(op='L_EXEC',a=RES['R'],b=0,c=idx),dict(op='L_WAIT',x=1),dict(op='L_DROP',a=0),dict(op='L_END')])
    mask=SPEC['profiles'][kind]['resource_mask']
    tasks=[dict(block_type=TYPES[kind],argument_mask=255,entry_pc=e,max_steps=128,required_resources=mask,program_image_id=number,
        topology_id=TOPOLOGY,parameter_base=4096,parameter_bytes=32,native_abi_id=ABI,input_object_mask=1,output_object_mask=1) for e in entries]
    objects=[dict(base_bytes=0,capacity_bytes=16,length_bytes=16,format=4,object_version=1,native_abi_id=ABI)]
    data=assemble('local',p,dict(task=tasks,object=objects,execution=execs),number,mask); parse(data,kind); return data
def build(kind,state=False):
    params=[dict(op='G_PARAM',a=i,x=i) for i in range(8)]
    if state:
        kinds={0:'C',1:'U',2:'F'}; p=params+[dict(op='G_CALL',a=0,b=0,c=0),dict(op='G_WAIT',x=1),dict(op='G_CALL',a=1,b=0,c=0),dict(op='G_CALL',a=2,b=1,c=0),
            dict(op='G_WAIT',x=3),dict(op='G_CALL',a=0,b=0,c=1),dict(op='G_WAIT',x=1),dict(op='G_END')]
    else:
        kinds={0:kind}; p=params+[dict(op='G_BRANCH',a=4,x=9,y=12),dict(op='G_CALL',a=0,b=0,c=0),dict(op='G_WAIT',x=1),dict(op='G_LOOP',a=7,x=9),dict(op='G_END')]
    result={'mother':assemble('mother',p,{},900)}
    for b,k in kinds.items(): result['local'+str(b)]=local_image(k,100+b,state=state and b==0,receipt=(1 if b==1 else 2 if b==2 else 0) if state else 0)
    return result,kinds
