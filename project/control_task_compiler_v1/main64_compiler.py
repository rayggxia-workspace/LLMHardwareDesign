"""Compile bounded two-endpoint native tasks to v2/64-bit controller images."""
from pathlib import Path
import argparse, hashlib, json, os, re, sys, tempfile, zlib
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'control_image_v0_1'))
from image import pack_image

ABI=0x01930001
CAPACITY=0x17630001
KINDS={'U':0,'F':1,'C':2,'P':3,'J':4}
ROLES=('mother','local0','local1')
SCHEMA='main64-native-tasks/1'

class CompileError(ValueError):
    pass

def require(ok,path,why):
    if not ok: raise CompileError(f'{path}: {why}')

def fields(obj,names,path):
    require(type(obj) is dict and set(obj)==set(names.split()),path,'expected fields: '+names)

def uint(value,low,high,path):
    require(type(value) is int and low<=value<=high,path,f'integer {low}..{high} required')
    return value

def identifier(s,path):
    require(type(s) is str and re.fullmatch(r'[a-z][a-z0-9_]{0,47}',s),path,'identifier required')

def decode(raw):
    def unique(pairs):
        out={}
        for k,v in pairs:
            require(k not in out,'$','duplicate JSON key '+k);out[k]=v
        return out
    try:return json.loads(raw,object_pairs_hook=unique)
    except (TypeError,json.JSONDecodeError) as e:raise CompileError('$: invalid JSON') from e

def target(name):
    require(type(name) is str,'$.target','target name required')
    import importlib.util
    path=HERE.parent/'control_main64_boot_v1/contract.py'
    spec=importlib.util.spec_from_file_location('main64_capability_contract',path)
    caps=importlib.util.module_from_spec(spec);spec.loader.exec_module(caps)
    parts=name.split('/')
    require(len(parts)==3 and parts[0]=='main64' and all(p in KINDS for p in parts[1:]),'$.target','main64/type0/type1 required')
    kinds=[KINDS[p] for p in parts[1:]]
    require(tuple(kinds) in caps.PAIRS,'$.target','pair not qualified')
    c=caps.contract()
    return dict(name=name,family='main64',kind=kinds[0],kinds=kinds,types=parts[1:],topology=caps.topology(*kinds),
                abi=caps.ABI,capacity=caps.CAPACITY,pm_bytes=c['pm_bytes_each'],instruction_bits=c['instruction_bits'],image_version=c['image_version'],
                contract_sha256=hashlib.sha256(canonical(c)).hexdigest())


def analyze(task):
    fields(task,'schema name target epoch generation job sequence image_ids tokens call_order buffers tasks transfers','$')
    require(task['schema']==SCHEMA,'$.schema','unsupported task version');identifier(task['name'],'$.name')
    t=target(task['target'])
    for n in ('epoch','generation','job','sequence'):uint(task[n],1,0xffffffff,'$.'+n)
    require('J' not in t['types'] or task['epoch']<=255,'$.epoch','J epoch is 1..255 without wrap')
    require(type(task['image_ids']) is list and len(task['image_ids'])==3,'$.image_ids','three image IDs required')
    for x in task['image_ids']:uint(x,1,0xffffffff,'$.image_ids')
    require(len(set(task['image_ids']))==3,'$.image_ids','IDs must differ')
    require(type(task['tokens']) is list and len(task['tokens'])==2,'$.tokens','two tokens required')
    for x in task['tokens']:uint(x,0,7,'$.tokens')
    require(len(set(task['tokens']))==2,'$.tokens','completion tokens must differ')
    require(type(task['call_order']) is list and all(type(x) is int for x in task['call_order']) and
            sorted(task['call_order'])==[0,1],'$.call_order','both CALLs precede the common WAIT')
    buffers={};by_block=[{},{}]
    require(type(task['buffers']) is list and 1<=len(task['buffers'])<=32,'$.buffers','bounded buffer table required')
    for i,b in enumerate(task['buffers']):
        p=f'$.buffers[{i}]';fields(b,'name block base_bytes words space format initial',p);identifier(b['name'],p+'.name')
        require(b['name'] not in buffers,p+'.name','duplicate buffer');block=uint(b['block'],0,1,p+'.block')
        base=uint(b['base_bytes'],0,16368,p+'.base_bytes');count=uint(b['words'],1,1024,p+'.words')
        require(base%16==0 and base+count*16<=16384,p,'aligned private-S range required')
        require(b['format']=='RAW128' and type(b['initial']) is bool,p,'RAW128 and boolean initial required')
        spaces=('J_FRAGMENT0','J_FRAGMENT1','J_OUTPUT') if t['types'][block]=='J' else ('S',)
        require(b['space'] in spaces,p+'.space','buffer space not available for this type')
        require((b['space']!='J_OUTPUT' or not b['initial']) and
                (not b['space'].startswith('J_FRAGMENT') or b['initial']),p+'.initial','J ownership/initialization mismatch')
        for other in by_block[block].values():
            require(base+count*16<=other['base_bytes'] or other['base_bytes']+other['words']*16<=base,p,'physical S ranges overlap')
        buffers[b['name']]=b;by_block[block][b['name']]=b
    require(type(task['tasks']) is list and len(task['tasks'])==2,'$.tasks','exactly two resident tasks required')
    rows=[None,None];valid=[set(),set()];states=[{},{}]
    for block in (0,1):valid[block]={(n,i) for n,b in by_block[block].items() if b['initial'] for i in range(b['words'])}
    def buffer(name,block,p,read=False,space='S',words=1):
        require(type(name) is str and name in by_block[block],p,'buffer absent from this endpoint')
        b=buffers[name];require(b['space']==space and b['words']>=words,p,'buffer space or capacity mismatch')
        if read:require(all((name,i) in valid[block] for i in range(words)),p,'read before complete per-word initialization/production')
        return b
    def lower(block,ops):
        kind=t['types'][block];out=[];state=states[block]
        require(type(ops) is list and 1<=len(ops)<=16,f'$.tasks[{block}].operations','1..16 operations required')
        for i,op in enumerate(ops):
            p=f'$.tasks[{block}].operations[{i}]';require(type(op) is dict and type(op.get('op')) is str,p,'operation required')
            name=op['op'];n0=n1=n2=n3=n4=n5=0;code=0
            if name=='ucf':
                fields(op,'op lane meta src dst',p);require(kind in ('U','F','C'),p,'U/F/C service required')
                require(type(op['src']) is list and len(op['src'])<=(3 if kind=='U' and op.get('lane')=='E' else 2),p+'.src','source arity exceeds main profile')
                meta=uint(op['meta'],0,(1<<64)-1,p+'.meta')
                require(type(op['lane']) is str,p+'.lane','macro lane name required')
                shapes={'U':{('N',0x100):(1,False),('N',0x81):(1,False),('N',2):(0,False),('N',0x85):(2,True),('N',7):(0,True),('E',3):(2,True)},
                        'F':{('G',9):(2,True),('E',0):(2,True)},
                        'C':{('G',9):(2,True),('E',0):(2,True),('R',0):(1,False),('R',2):(0,True)}}
                base_meta=meta&~(1<<63)
                direct=meta!=base_meta
                require(not direct or kind in ('F','C') and op['lane'] in ('G','E'),p,'direct bit unavailable')
                key=(op['lane'],base_meta);require(key in shapes[kind],p,'native lane/metadata outside admitted recipe')
                ns,store=shapes[kind][key]
                if kind=='U' and op['lane']=='E':ns=len(op['src']);require(ns in (2,3),p,'U FMA requires two or three inputs')
                if direct and op['lane']=='G':
                    require(not state.get('direct'),p,'unconsumed G direct output');store=False;state['direct']=True
                if direct and op['lane']=='E':
                    require(state.get('direct'),p,'E direct input has no producer');state['direct']=False
                require(len(op['src'])==ns and (op['dst'] is not None)==store,p,'source/store arity mismatch')
                src=[buffer(n,block,p+'.src',read=True) for n in op['src']]
                dst=buffer(op['dst'],block,p+'.dst') if store else None
                require(dst is None or all(s['name']!=dst['name'] for s in src),p,'in-place native output is not admitted')
                if op['lane']=='N':
                    stage=state.get('N',0)
                    need={0x100:0,0x81:1,2:2,0x85:3,7:3}[meta]
                    require(stage==need,p,'N context order invalid')
                    if meta in (0x100,0x81,2):state['N']=stage+1
                    if meta==0x85:
                        require(not state.get('Nreplayed'),p,'N replay window already consumed')
                        state['Nreplayed']=True
                if op['lane']=='R':
                    require(state.get('R',0)==(0 if meta==0 else 1),p,'R load/read order invalid');state['R']=1
                lane={'E':0,'N':1,'G':1,'R':2}[op['lane']]
                n0=lane|ns<<2|int(store)<<4|((dst['base_bytes']//16)<<5 if dst else 0)
                n1=sum((s['base_bytes']//16)<<(10*j) for j,s in enumerate(src));n2=meta&0xffffffff;n3=meta>>32;code=0x100
                if dst:valid[block].add((dst['name'],0))
            elif name=='u_direct':
                fields(op,'op n_src n_meta e_src e_meta dst',p)
                require(kind=='U' and state.get('N')==3 and not state.get('Nreplayed'),p,'configured, unconsumed U N context required')
                require(op['n_meta']==0x85 and op['e_meta']==3,p,'bounded RMS-to-FMA direct recipe required')
                require(type(op['n_src']) is list and len(op['n_src'])==2 and type(op['e_src']) is list and len(op['e_src'])==2,p,'direct RMS/FMA arity')
                ns=[buffer(n,block,p+'.n_src',read=True) for n in op['n_src']]
                es=[buffer(n,block,p+'.e_src',read=True) for n in op['e_src']]
                dst=buffer(op['dst'],block,p+'.dst')
                require(all(s['name']!=dst['name'] for s in ns+es),p,'direct output aliases input')
                n0=2;n1=sum((s['base_bytes']//16)<<(10*j) for j,s in enumerate(ns));n2=0x85
                n4=3|(dst['base_bytes']//16)<<9;n5=sum((s['base_bytes']//16)<<(10*j) for j,s in enumerate(es));code=0x104
                valid[block].add((dst['name'],0))
                state['Nreplayed']=True
            elif name=='p_load':
                fields(op,'op a b',p);require(kind=='P' and not state.get('loaded'),p,'one P load per task')
                aa=buffer(op['a'],block,p+'.a',True,words=4);bb=buffer(op['b'],block,p+'.b',True,words=4)
                require(aa['base_bytes']%64==0 and bb['base_bytes']%64==0,p,'P feeder spans must be 64-byte aligned')
                n0=34|(aa['base_bytes']//16)<<11|(bb['base_bytes']//16)<<21;code=0x110;state['loaded']=True;state['config']=0
            elif name in ('p_config0','p_config1'):
                fields(op,'op',p);required=0 if name=='p_config0' else 1
                require(kind=='P' and state.get('loaded') and state['config']==required,p,'P configuration order invalid')
                n0=10;n1=0x9214 if required==0 else 0x9210;code=0x111;state['config']+=1
            elif name=='p_store':
                fields(op,'op dst',p);require(kind=='P' and state.get('config')==2 and not state.get('stored'),p,'P store requires both configurations')
                dst=buffer(op['dst'],block,p+'.dst');n0=5|1<<10|(dst['base_bytes']//16)<<12;n1=0x101;code=0x111
                # The one-row/one-tile recipe consumes the complete A/B spans before storing.
                state['stored']=True;valid[block].add((dst['name'],0))
            elif name=='p_route':
                fields(op,'op',p);require(kind=='P' and state.get('config')==2 and not state.get('Pdirect'),p,'P M context/direct slot')
                n0=5|1<<22;n1=0x101;code=0x111;state['Pdirect']=True
            elif name=='p_gate_direct':
                fields(op,'op a b dst',p);require(kind=='P' and state.get('Pdirect'),p,'M direct result required')
                aa=buffer(op['a'],block,p+'.a',True);bb=buffer(op['b'],block,p+'.b',True);dst=buffer(op['dst'],block,p+'.dst')
                require(dst['name'] not in (aa['name'],bb['name']),p,'direct gate output alias')
                n0=aa['base_bytes']//16|(bb['base_bytes']//16)<<10|(dst['base_bytes']//16)<<20|1<<30
                code=0x112;state['Pdirect']=False;valid[block].add((dst['name'],0))
            elif name=='p_gate':
                fields(op,'op a b dst',p);require(kind=='P',p,'P gate required')
                aa=buffer(op['a'],block,p+'.a',True);bb=buffer(op['b'],block,p+'.b',True);dst=buffer(op['dst'],block,p+'.dst')
                require(dst['name'] not in (aa['name'],bb['name']),p,'P gate destination aliases an input')
                n0=aa['base_bytes']//16|(bb['base_bytes']//16)<<10|(dst['base_bytes']//16)<<20;code=0x112;valid[block].add((dst['name'],0))
            elif name=='join':
                fields(op,'op left right dst tag',p);require(kind=='J' and not state.get('joined'),p,'one JOIN per J task')
                left=buffer(op['left'],block,p+'.left',True,'J_FRAGMENT0');right=buffer(op['right'],block,p+'.right',True,'J_FRAGMENT1')
                dst=buffer(op['dst'],block,p+'.dst',space='J_OUTPUT');count=dst['words'];uint(count,1,4,p+'.dst.words')
                require(left['words']==right['words']==count,p,'JOIN fragment/output lengths differ')
                tag=uint(op['tag'],0,(1<<24)-1,p+'.tag');n0=dst['base_bytes']//16|count<<10;n1=task['epoch']<<24|tag;code=0x120
                state['joined']=dst['name'];state['released']=False;state['tag']=tag
                valid[block].update((dst['name'],i) for i in range(count))
            elif name=='release':
                fields(op,'op',p);require(kind=='J' and state.get('joined') and not state.get('released'),p,'RELEASE requires one JOIN')
                state['released']=True;code=0x121
            else:raise CompileError(p+': unsupported semantic operation')
            out.append(dict(resource=0,service=0,native_op=code,native_abi_id=ABI,native0=n0,native1=n1,native2=n2,native3=n3,native4=n4,native5=n5))
        require(not state.get('direct') and not state.get('Pdirect'),f'$.tasks[{block}]','unconsumed G direct output')
        if kind=='J':require(state.get('released'),f'$.tasks[{block}]','J lease must be released')
        return out
    task_ops={}
    for item in task['tasks']:
        fields(item,'block operations','$.tasks');block=uint(item['block'],0,1,'$.tasks.block')
        require(block not in task_ops,'$.tasks','duplicate endpoint');task_ops[block]=item['operations']
    require(set(task_ops)=={0,1},'$.tasks','missing endpoint')
    rows[0]=lower(0,task_ops[0])
    require(type(task['transfers']) is list and len(task['transfers'])<=1,'$.transfers','at most one passive source0-to-P1 edge')
    if task['transfers']:
        require(t['types'][0] in ('U','F','C') and t['types'][1]=='P','$.transfers','only main U/F/C passive write to P admitted; J requires R8.4')
        edge=task['transfers'][0];fields(edge,'source destination words format','$.transfers[0]')
        count=uint(edge['words'],1,4,'$.transfers[0].words');require(edge['format']=='RAW128','$.transfers[0].format','no implicit conversion')
        src=buffer(edge['source'],0,'$.transfers[0].source',True,'S',count)
        dst=buffer(edge['destination'],1,'$.transfers[0].destination',space='S',words=count)
        require(src['words']==dst['words']==count and not dst['initial'],'$.transfers[0]','exact lengths and uninitialized destination')
        for i in range(count):
            rows[0].append(dict(resource=0,service=0,native_abi_id=ABI,native_op=0x101,native0=(src['base_bytes']//16+i)|(dst['base_bytes']//16+i)<<10))
        valid[1].update((dst['name'],i) for i in range(count))
    rows[1]=lower(1,task_ops[1])
    for block,rr in enumerate(rows):
        require(len(rr)<=16,f'$.tasks[{block}]','expanded execution table exceeds16 entries')
        require(all(r['native_op'] in ({0x100,0x101,0x104} if t['types'][block]=='U' else {0x100,0x101} if t['types'][block] in ('F','C') else {0x110,0x111,0x112} if t['types'][block]=='P' else {0x120,0x121}) for r in rr),f'$.tasks[{block}]','operation outside main capability table')
    return t,rows,buffers,states

def compile_task(task):
    t,rows,buffers,states=analyze(task);programs=[];images={}
    if task['transfers']:
        require(task['call_order']==[0,1],'$.call_order','passive P sink must start after source terminal/commit')
        mother=[dict(op='G_CALL',a=0,b=task['tokens'][0],c=0),dict(op='G_WAIT',x=1<<task['tokens'][0]),
                dict(op='G_CALL',a=1,b=task['tokens'][1],c=0),dict(op='G_WAIT',x=1<<task['tokens'][1]),dict(op='G_END')]
    else:
        mother=[dict(op='G_CALL',a=b,b=task['tokens'][b],c=0) for b in task['call_order']]
        mother.extend([dict(op='G_WAIT',x=sum(1<<x for x in task['tokens'])),dict(op='G_END')])
    programs.append(mother)
    for rr in rows:programs.append([ins for i in range(len(rr)) for ins in (dict(op='L_EXEC',a=0,b=0,c=i),dict(op='L_WAIT',x=1))]+[dict(op='L_END')])
    entries={}
    for index,(role,prog,image_id) in enumerate(zip(ROLES,programs,task['image_ids'])):
        header=dict(entry_pc=0,max_steps=len(prog),program_image_id=image_id,topology_id=t['topology'],native_abi_id=ABI,capacity_profile_id=CAPACITY,resource_mask=int(index!=0))
        records={} if index==0 else dict(task=[dict(block_type=KINDS[t['types'][index-1]],entry_pc=0,max_steps=len(prog),required_resources=1,program_image_id=image_id,topology_id=t['topology'],native_abi_id=ABI)],execution=rows[index-1])
        data=pack_image('mother' if index==0 else 'local',prog,records,header,instruction_version=2)
        require(len(data)<= (4736 if index==0 else 8320) and len(data)<=t['pm_bytes'],role,'image exceeds target bound')
        images[role]=data;entries[role]=dict(bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),crc32=zlib.crc32(data),image_id=image_id,instructions=len(prog),execution_records=0 if index==0 else len(rows[index-1]))
    return dict(schema='main64-native-bundle/1',task_sha256=hashlib.sha256(canonical(task)).hexdigest(),target=t,images=entries,
                images_hex={k:v.hex() for k,v in images.items()},schedule=dict(call_order=task['call_order'],tokens=task['tokens']),
                limits=['main64 two resident tasks; no dynamic shapes or loops','fixed qualified native recipes and RAW128 routes','compiler does not establish numeric format compatibility or physical timing'])

def canonical(obj):return json.dumps(obj,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode('utf-8')

def write_bundle(path,bundle):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent,delete=False) as f:
        tmp=Path(f.name);f.write(json.dumps(bundle,indent=2,sort_keys=True).encode()+b'\n')
    try:os.replace(tmp,path)
    finally:tmp.unlink(missing_ok=True)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('input',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    try:
        require(a.input.resolve()!=a.output.resolve(),'--output','must differ from input')
        bundle=compile_task(decode(a.input.read_bytes()));write_bundle(a.output,bundle)
    except (ValueError,OSError) as e:p.exit(2,str(e)+'\n')
    print('PASS compiled',bundle['target']['name'],bundle['task_sha256'])
if __name__=='__main__':main()
