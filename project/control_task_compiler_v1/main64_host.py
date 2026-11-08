"""Audited host load plan; commands are management operations, not 64-bit ISA words."""
import hashlib,json,zlib
from main64_audit import audit

def request(op,target,address=0,data=0,status=0,mask=0,value=0,mode=0):
    return dict(mode=mode,op=op,target=target,address=address,data=data,status=status,mask=mask,value=value)

def load_plan(task,bundle):
    audit(task,bundle);gen=task['generation'];epoch=task['epoch']
    plan=[request(8,3,data=task['job']|epoch<<32|task['sequence']<<64|gen<<96,status=0x105),request(0,3,data=gen|epoch<<32)]
    for who,name in enumerate(('mother','local0','local1')):
        data=bytes.fromhex(bundle['images_hex'][name]);entry=bundle['images'][name]
        image_id=int.from_bytes(data[60:64],'little');topology=int.from_bytes(data[64:68],'little');abi=int.from_bytes(data[68:72],'little');capacity=int.from_bytes(data[84:88],'little')
        manifest=gen|len(data)<<32|image_id<<48|topology<<80|abi<<112|capacity<<144
        # Reject a wrong ABI BEGIN without revoking correct images, then perform the real BEGIN.
        plan.extend([request(1,who,data=manifest^(1<<112),status=3),request(1,who,data=manifest)])
        for offset in range(0,len(data),16):plan.append(request(2,who,offset,int.from_bytes(data[offset:offset+16],'little')))
        for offset in range(0,len(data),16):plan.append(request(3,who,offset,mask=(1<<128)-1,value=int.from_bytes(data[offset:offset+16],'little')))
        crc=zlib.crc32(data);plan.extend([request(4,who,mask=(1<<64)-1,value=crc|crc<<32),request(5,who)])
    return plan

def replay_plan(task,bundle,inputs,reference):
    plan=load_plan(task,bundle);buffers={b['name']:b for b in task['buffers']};types=task['target'].split('/')[1:]
    operations={t['block']:t['operations'] for t in task['tasks']}
    seen=set()
    for item in inputs:
        if set(item)!={'buffer','words'} or item['buffer'] not in buffers or item['buffer'] in seen:raise ValueError('invalid input binding')
        b=buffers[item['buffer']];seen.add(item['buffer'])
        if not b['initial'] or len(item['words'])!=b['words']:raise ValueError('input length/ownership')
        for i,value in enumerate(item['words']):
            if type(value) is not int or not 0<=value<(1<<128):raise ValueError('input word')
            op=12
            if b['space'].startswith('J_FRAGMENT'):
                join=next(x for x in operations[b['block']] if x['op']=='join');tag=task['epoch']<<24|join['tag']
                value|=tag<<128|int(b['space'][-1])<<160|int(i==b['words']-1)<<162;op=14
            plan.append(request(op,b['block']+1,b['base_bytes']+16*i,value))
    if seen!={n for n,b in buffers.items() if b['initial']}:raise ValueError('missing initialized input')
    # Poison outputs independently of the logical initial-valid set.
    for b in buffers.values():
        if not b['initial'] and b['space']=='S':
            for i in range(b['words']):plan.append(request(12,b['block']+1,b['base_bytes']+i*16,(1<<128)-1))
    gen,epoch=task['generation'],task['epoch'];start=task['job']|epoch<<32|task['sequence']<<64|gen<<96
    plan.append(request(7,3,data=gen))
    plan.extend([request(8,3,data=start^(1<<96),status=0x107),request(8,3,data=start),request(9,3,mode=1,mask=1<<18,value=1<<18)])
    mask=(1<<112)-1|((1<<32)-1)<<248
    value=task['job']|epoch<<32|task['sequence']<<64|reference['write_bytes']<<248
    plan.append(request(10,3,mask=mask,value=value))
    for c in reference['checks']:plan.append(request(c['op'],c['target'],c['address'],mask=c['mask'],value=c['value']))
    for who,kind in enumerate(types,1):
        if kind=='J':plan.append(request(13,who,status=0x105))
    plan.append(request(10,3,status=0x105));return plan

def word(cmd):
    widths={'mode':4,'op':4,'target':2,'address':14,'data':256,'status':16,'mask':512,'value':512}
    value=0
    for k,bits in widths.items():
        v=cmd[k]
        if type(v) is not int or not 0<=v<1<<bits:raise ValueError('host field '+k)
        value=(value<<bits)|v
    return value

def save(folder,task,bundle,inputs,reference):
    from pathlib import Path
    p=Path(folder);p.mkdir(parents=True,exist_ok=True);commands=replay_plan(task,bundle,inputs,reference)
    (p/'replay.mem').write_text(''.join(f'{word(c):0330x}\n' for c in commands),encoding='ascii')
    (p/'count.mem').write_text(f'{len(commands):08x}\n{reference["commits"]:08x}\n',encoding='ascii')
    for name,obj in (('task',task),('bundle',bundle),('inputs',inputs),('reference',reference),('host-plan',commands)):
        (p/(name+'.json')).write_text(json.dumps(obj,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    for name,hex_data in bundle['images_hex'].items():(p/(name+'.bin')).write_bytes(bytes.fromhex(hex_data))
    return len(commands)
