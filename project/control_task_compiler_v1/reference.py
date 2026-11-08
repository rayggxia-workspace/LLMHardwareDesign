"""Independent small numeric oracle for the explicitly declared example domain."""
import math

def lanes(word,n=8,width=16):
    values=[(word>>(i*width))&((1<<width)-1) for i in range(n)]
    return [v-(1<<width) if v>>(width-1) else v for v in values]
def pack(values,width=16):return sum((v&((1<<width)-1))<<(i*width) for i,v in enumerate(values))
def clip(v):return min(32767,max(-32768,v))
def rne(v,bits):
    q,r=divmod(v,1<<bits);return q+int(r>1<<(bits-1) or r==1<<(bits-1) and q&1) if bits else v
def silu(x):
    if x< -8192:return 0
    if x>8192:return x
    low=x//32*32
    knot=lambda a:round(a/(1+math.exp(-a/1024)))
    return knot(low)+rne((knot(min(low+32,8192))-knot(low))*(x-low),5)

def evaluate(task,inputs):
    buffers={b['name']:b for b in task['buffers']};memory={};outputs={};changed=set();written=0;states=[{},{}]
    for item in inputs:
        b=buffers[item['buffer']]
        if len(item['words'])!=b['words']:raise ValueError('incomplete input buffer')
        for i,v in enumerate(item['words']):memory[(b['name'],i)]=v
    def get(name,i=0):return memory[name,i]
    def put(name,value,i=0):
        nonlocal written
        memory[name,i]=value;changed.add((name,i));written+=16
    ops={x['block']:x['operations'] for x in task['tasks']}
    for block in (0,1):
        if block==1 and task['transfers']:
            e=task['transfers'][0]
            for i in range(e['words']):put(e['destination'],get(e['source'],i),i)
        st=states[block]
        for op in ops[block]:
            if op['op']=='ucf':
                data=[get(n) for n in op['src']];lane=op['lane'];meta=op['meta']
                if lane=='N':
                    if meta==0x100:st['eps']=data[0]&0xffffffff
                    elif meta==0x81:st['raw']=lanes(data[0])
                    elif meta==2:st['factor']=math.isqrt(((sum(x*x for x in st['raw'])//8)+st['eps'])<<16)
                    elif meta==0x85:
                        # This oracle admits the exact RMS fixture domain, with gamma=1 and +/-1024.
                        raw,gamma=lanes(data[0]),lanes(data[1])
                        if any(abs(v)!=1024 for v in raw) or gamma!=[1024]*8 or st['factor']!=262144:raise ValueError('numeric oracle RMS domain exceeded')
                        put(op['dst'],pack(raw))
                    elif meta==7:
                        raw=st['raw'];stats=(sum(x*x for x in raw)<<80)|((sum(raw)&0xffffffff)<<48)|((min(raw)&0xffff)<<32)|((max(raw)&0xffff)<<16)|len(raw)
                        put(op['dst'],stats)
                elif lane=='E':
                    n=8 if task['target'].endswith('/U') else 2
                    aa,bb=lanes(data[0],n),lanes(data[1],n)
                    put(op['dst'],pack([clip(a*b if meta==3 else a+b) for a,b in zip(aa,bb)]))
                elif lane=='G':
                    if data[0]!=0:raise ValueError('numeric oracle gated-sigmoid domain exceeded')
                    put(op['dst'],pack([rne(x,1) for x in lanes(data[1],2)]))
                elif meta==0:st['R']=data[0]
                else:put(op['dst'],st['R'])
            elif op['op']=='p_load':st['a']=get(op['a']);st['b']=get(op['b'])
            elif op['op']=='p_store':
                aa,bb=lanes(st['a'],16,8),lanes(st['b'],16,8)
                if any(aa[8:]):raise ValueError('numeric oracle M fixture layout exceeded')
                put(op['dst'],pack([sum(a*b for a,b in zip(aa[:8],bb[j:j+8])) for j in (0,8)],32))
            elif op['op']=='p_gate':
                aa,bb=lanes(get(op['a']),2),lanes(get(op['b']),2)
                put(op['dst'],pack([clip(rne(silu(a)*b,10)) for a,b in zip(aa,bb)]))
            elif op['op']=='join':
                count=buffers[op['dst']]['words'];tag=task['epoch']<<24|op['tag']
                outputs[op['dst']]=[]
                for i in range(count):
                    aa,bb=lanes(get(op['left'],i)),lanes(get(op['right'],i))
                    value=pack([clip(a+b) for a,b in zip(aa,bb)]);put(op['dst'],value,i)
                    packet=value|tag<<128|i<<160|int(i==count-1)<<170
                    outputs[op['dst']].append(packet)
    checks=[]
    for name,i in sorted(changed):
        b=buffers[name]
        if b['space']=='S':checks.append(dict(op=11,target=b['block']+1,address=b['base_bytes']+16*i,value=get(name,i),mask=(1<<128)-1))
    if task['target']=='five/J':
        for name,packets in sorted(outputs.items()):
            for packet in packets:
                # Task sequence is1 on the fresh cohort; it differs from host START sequence.
                packet|=task['job']<<171|task['epoch']<<203|1<<235
                checks.append(dict(op=13,target=buffers[name]['block']+1,address=0,value=packet,mask=(1<<267)-1))
    return dict(checks=checks,write_bytes=written,commits=sum(e['words'] for e in task['transfers']),
                scope='native example numeric domain, not arbitrary tensor or full-model equivalence')
