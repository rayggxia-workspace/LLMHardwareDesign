"""Issue76 finite Granite expert/merge service; actual inputs server-only.

One immutable packed weight deployment, B1/16 effective matrix PEs, shared
VR8 and lane0-borrowing SFU. No numerical producer imports or runtime math.
"""
import argparse
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import platform
import time
import traceback
import numpy as np

KIB=1024
MIB=1024*KIB
REVISION='a02780686e08a03fe0d2679a293b5c74a90efa89'
PHYSICAL_K=512


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(8<<20),b''):h.update(block)
    return h.hexdigest()


def array_sha(a):
    a=np.ascontiguousarray(a)
    h=hashlib.sha256();h.update(str(a.dtype).encode());h.update(json.dumps(list(a.shape),separators=(',',':')).encode());h.update(a.tobytes())
    return h.hexdigest()


def load(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def put(path,value):
    Path(path).write_text(json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+'\n',encoding='utf-8',newline='\n')


def bound(directory,schema,status):
    directory=Path(directory);m=load(directory/'manifest.json')
    if m.get('schema')!=schema or m.get('status')!=status:raise ValueError('typed source '+str(directory))
    for entry in m['artifacts']:
        p=Path(entry['path'])
        if p.is_absolute() or '..' in p.parts:raise ValueError('artifact path')
        p=directory/p
        if p.stat().st_size!=entry['bytes'] or sha(p)!=entry['sha256']:raise ValueError('artifact SHA/size '+str(p))
    return m


def bind(path):
    value=load(path)
    if not value.get('commit') or value.get('service_sha256')!=sha(__file__):raise ValueError('source binding')
    return value


def seal(out,manifest):
    manifest['artifacts']=[{'path':p.name,'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(out.iterdir()) if p.is_file() and p.name!='manifest.json']
    put(out/'manifest.json',manifest)


def pack_weight(w):
    """Only reorders exact S8 codes; output axes E,Oblock,Kblock,k16,o16."""
    w=np.asarray(w)
    if w.dtype!=np.int8 or w.ndim!=3 or w.shape[1]%16 or w.shape[2]%16:
        raise ValueError('packed S8 shape E/O16/K16')
    E,O,K=w.shape
    return np.ascontiguousarray(w.reshape(E,O//16,16,K//16,16).transpose(0,1,3,4,2))


def unpack_weight(w):
    w=np.asarray(w)
    if w.dtype!=np.int8 or w.ndim!=5 or w.shape[-2:]!=(16,16):raise ValueError('packed tensor shape')
    E,Ob,Kb,_,_=w.shape
    return np.ascontiguousarray(w.transpose(0,1,4,2,3).reshape(E,Ob*16,Kb*16))


def run_pack(args):
    out=Path(args.out)
    if out.exists():raise ValueError('refuse overwrite')
    binding=bind(args.binding);cm=bound(args.compiled,'granite-moe-compiled74-v1','COMPILED_NOT_EXECUTED')
    if cm.get('model_revision')!=REVISION:raise ValueError('pinned revision')
    out.mkdir(parents=True);started=time.monotonic()
    manifest={'schema':'granite-packed76-v1','status':'ERROR','source':binding,'producer_sha256':sha(__file__),
        'compiled_manifest_sha256':sha(args.compiled/'manifest.json'),'model_revision':REVISION,'layer':args.layer,'artifacts':[]}
    try:
        arrays={};metadata=[]
        with np.load(args.compiled/'constants.npz',allow_pickle=False) as source:
            for which,shape in (('gate_up',(40,1024,1536)),('down',(40,1536,512))):
                key='L%d.%s_w8'%(args.layer,which);original=source[key]
                if original.shape!=shape:raise ValueError('complete current-layer40 experts')
                packed=pack_weight(original)
                if not np.array_equal(unpack_weight(packed),original):raise ValueError('exact pack inverse')
                arrays[which+'_w8']=packed
                metadata.append({'which':which,'source_key':key,'original_shape':list(original.shape),'packed_shape':list(packed.shape),
                    'dtype':'int8','bytes':packed.nbytes,'original_array_sha256':array_sha(original),'packed_array_sha256':array_sha(packed)})
        np.savez_compressed(out/'packed.npz',**arrays)
        put(out/'layout.json',{'schema':'granite-packed-layout76-v1','layer':args.layer,'arrays':metadata,
            'mapping':'packed[e,ob,kb,k,o]=original[e,16*ob+o,16*kb+k]',
            'linear_address':'e*O*K + ob*16*K + kstart*16 + k*16 + o',
            'matrix_physical_tile':{'O':16,'K':512,'bytes':8192},'M_effective_B1_PEs':16,
            'hardware_EXT_deployment':'packed codes only; original scientific NPZ is not a second deployed copy',
            'offline_preprocessing':'real integer reorder/inverse checked; outside per-token inference slots; source storage and elapsed time recorded separately',
            'total_deployed_weight_bytes':sum(a.nbytes for a in arrays.values()),'perlayer_scale_bytes':40*(1024+1536)*6})
        manifest['status']='PACKED_NOT_EXECUTED'
    except Exception as exc:
        manifest['error']={'type':type(exc).__name__,'message':str(exc),'traceback':traceback.format_exc()};raise
    finally:manifest['elapsed_seconds']=time.monotonic()-started;seal(out,manifest)


def beats(offset,n):
    if offset<0 or n<0:raise ValueError('negative access')
    return (offset%16+n+15)//16 if n else 0


def packet_cost(src,dst,n):
    if min(src,dst,n)<0:raise ValueError('negative packet')
    c=Counter();done=0
    while done<n:
        amount=min(1984,n-done);wire=32+16*((amount+15)//16)
        c.update(src_beats=beats(src+done,amount),dst_beats=beats(dst+done,amount),wire_beats=wire//16,wire_bytes=wire,packets=1,payload_bytes=amount)
        done+=amount
    return dict(c)


class Builder:
    """Compressed affine witness, strict serial calendar, fixed finite buffers."""
    def __init__(self,tile,placement,calibration):
        if tile not in (128,256) or placement not in ('M','V'):raise ValueError('frozen configuration')
        self.tile=tile;self.owner=placement;self.cal=calibration
        self.cap={'M':32*KIB,'V':16*KIB,'R':32*KIB,**{'S'+str(i):32*KIB for i in range(8)},'EXT':128*MIB,'ROM':4260100}
        self.alloc={};self.used=Counter();self.events=[];self.clock=0;self.counts=Counter()
        self.inventory={'capacities':self.cap,'banks':{k:{'bits':128,'kind':'1RW'} for k in self.cap if k!='ROM'},
            'matrix':{'resource':'M256','S8_PEs':256,'shape':[16,16],'effective_B1_PEs':16,'Ktile':512,'weight_bytes':8192,'accumulator_register_bytes':64,'A_register_bytes':16,'weight_register_bytes':16},
            'vector':{'resource':'VR8','byte_lanes':8,'policy':'scalar dependency cycles, never total carry/8','internal_staging_from_FIFO':True},
            'SFU':{'count':1,'resource':'SFU','borrows':'VR8 lane0','extra_byte_ALU':False},
            'ROM':{'capacity':4260100,'return_bits':32,'ports':1,'latency':2,'II':1,'synchronous_candidate':True},
            'packet':{'BUS_count':1,'BUS_bits':128,'beat_bytes':16,'header_bytes':32,'max_payload_bytes':1984,'FIFO_bytes':2048},
            'policy':'strict serialized B1; no free prefill/decode batching, no optimality/RTL/PPA claim'}

    def add(self,name,bank,n,role='scratch'):
        if name in self.alloc or bank not in self.cap or n<0:raise ValueError('allocation')
        alignment=4 if bank=='ROM' else 16
        offset=(self.used[bank]+alignment-1)//alignment*alignment
        if offset+n>self.cap[bank]:raise ValueError('capacity '+bank+' '+name)
        self.alloc[name]={'object':name,'bank':bank,'offset':offset,'bytes':int(n),'role':role,'lifetime':['task_start','task_end']}
        self.used[bank]=offset+n
        return name

    def access(self,obj,offset,n,mode='read',repeat=1,stride=0,index_strides=()):
        a=self.alloc[obj]
        if min(offset,n,repeat,stride)<0 or offset+n+(repeat-1)*stride>a['bytes']:raise ValueError('object range '+obj)
        return {'object':obj,'offset':int(offset),'bytes':int(n),'mode':mode,'repeat':int(repeat),'stride':int(stride),'index_strides':list(map(int,index_strides))}

    def leaf(self,body,kind,resources,simultaneous=False,**meta):
        start=body[-1]['end'] if body else 0;rr=[];end=start
        for name,duration in resources:
            duration=int(duration)
            if duration:
                begin=start if simultaneous else end;rr.append({'name':name,'start':begin,'end':begin+duration});end=max(end,begin+duration)
        event={'kind':kind,'start':start,'end':end,'resources':rr,**meta};body.append(event);return event

    def loop(self,body,count,inner):
        if count<0:raise ValueError('loop count')
        start=body[-1]['end'] if body else 0;period=inner[-1]['end'] if inner else 0
        node={'kind':'loop','start':start,'end':start+int(count)*period,'count':int(count),'period':period,'body':inner};body.append(node);return node

    def memory(self,body,accesses):
        resources=[];count=0
        for a in accesses:
            obj=self.alloc[a['object']];n=sum(beats(obj['offset']+a['offset']+j*a['stride'],a['bytes']) for j in range(a['repeat']))
            resources.append(('bank.'+obj['bank'],n));count+=n
        return self.leaf(body,'access',resources,accesses=accesses,counts={'bank_beats':count})

    def transfer(self,body,src,dst,n,so=0,do=0,src_index=(),dst_index=()):
        s=self.alloc[src];d=self.alloc[dst];c=packet_cost(s['offset']+so,d['offset']+do,n)
        return self.leaf(body,'transfer',[('bank.'+s['bank'],c.get('src_beats',0)),('BUS',c.get('wire_beats',0)),('bank.'+d['bank'],c.get('dst_beats',0))],
            accesses=[self.access(src,so,n,index_strides=src_index),self.access(dst,do,n,'write',index_strides=dst_index)],
            counts=c,FIFO_peak_bytes=32+16*((min(n,1984)+15)//16),packet={'src':src,'dst':dst,'src_offset':so,'dst_offset':do,'bytes':n})

    def engine(self,body,obj,offset,n,mode='read',index=()):
        a=self.alloc[obj];c=packet_cost(a['offset']+offset,0,n);bankbeats=c.get('src_beats',0)
        rr=[('bank.'+a['bank'],bankbeats),('BUS',c.get('wire_beats',0))] if mode=='read' else [('BUS',c.get('wire_beats',0)),('bank.'+a['bank'],bankbeats)]
        return self.leaf(body,'engine_access',rr,accesses=[self.access(obj,offset,n,mode,index_strides=index)],
            counts={**c,'engine_read_bytes' if mode=='read' else 'engine_write_bytes':n},FIFO_peak_bytes=32+16*((min(n,1984)+15)//16),engine='shared BUS-attached VR8')

    def compute(self,body,op,count=1,parameters=None):
        item=self.cal['ops'].get(op)
        if not item or item.get('status')!='PASS':raise ValueError('unknown/unqualified width fee '+op)
        cycles=int(item['scalar_dependency_cycles'])*int(count)
        scratch=int(item['scratch_peak_bytes'])
        if not cycles or scratch>1024:raise ValueError('bounded microprogram cost/scratch '+op)
        resources=[('VR8',cycles)]
        if item.get('uses_SFU'):resources.append(('SFU',cycles))
        return self.leaf(body,'compute',resources,simultaneous=True,op=op,count=int(count),parameters=parameters or {},
            counts={'op.'+op:int(count),'micro_dependency_cycles':cycles},calibration_sha256=item['microprogram_sha256'],
            scratch_peak_bytes=scratch,operand_register_budget_bytes=1024,FIFO_peak_bytes=1024)

    def macro(self,stage,body,meta):
        ident=len(self.events);duration=body[-1]['end'] if body else 0
        event={'id':ident,'stage':stage,'start':self.clock,'end':self.clock+duration,'deps':[ident-1] if ident else [],'meta':meta,'body':body}
        self.events.append(event);self.clock+=duration;self.count_tree(body,1);return event

    def count_tree(self,nodes,mult):
        for node in nodes:
            if node['kind']=='loop':self.count_tree(node['body'],mult*node['count'])
            else:
                for k,v in node.get('counts',{}).items():self.counts[k]+=int(v)*mult


def main():
    p=argparse.ArgumentParser(__doc__);sub=p.add_subparsers(dest='command',required=True)
    q=sub.add_parser('pack');q.add_argument('--compiled',type=Path,required=True);q.add_argument('--layer',type=int,choices=(0,13),required=True)
    q.add_argument('--binding',type=Path,required=True);q.add_argument('--out',type=Path,required=True)
    a=p.parse_args();run_pack(a)


if __name__=='__main__':main()
