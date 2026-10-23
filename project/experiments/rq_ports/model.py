"""Finite-credit store-and-forward service DAG; not calibrated hardware cycles."""
from collections import Counter,defaultdict
import heapq

def beats(n,offset=0,word=16):
    if n<0 or offset<0:raise ValueError("negative span")
    return 0 if n==0 else (offset%word+n+word-1)//word

def chunks(n):
    for start in range(0,n,1984):yield start,min(1984,n-start)

class Graph:
    def __init__(self):
        self.nodes=[];self.last_tx={};self.last_rx={};self.packets=[];self.leases=[]
        self.bytes=Counter();self.sizes={**{f'S{i}':32768 for i in range(8)},
            'MA0':4096,'MA1':4096,'MW0':8192,'MW1':8192,'MC':8192,'VC':16384}

    def add(self,label,duration,resources=(),deps=(),**extra):
        deps=tuple(sorted(set(x for x in deps if x is not None)))
        assert duration>=0 and (duration or not resources) and len(set(resources))==len(resources)
        i=len(self.nodes);assert all(0<=d<i for d in deps)
        self.nodes.append(dict(id=i,label=label,duration=int(duration),resources=list(resources),deps=list(deps),**extra))
        return i

    def memory(self,port,n,offset,deps,write=False,label='memory'):
        if n<=0 or offset+n>self.sizes[port]:raise ValueError('capacity/span '+port)
        physical=beats(n,offset)*16
        self.bytes['memory_logical']+=n;self.bytes['memory_physical']+=physical
        return self.add(label,physical//16,(port,),deps,port=port,write=write,bytes=n,offset=offset)

    def transfer(self,src,dst,n,source_port,destination_port,deps,source_offset=0,destination_offset=0,kind='data'):
        ends=[]
        for off,size in chunks(n):
            read=self.memory(source_port,size,source_offset+off,
                (*deps,self.last_tx.get(src)),label='packet-read '+kind)
            wire_bytes=64+beats(size,word=64)*64
            wire=self.add('wire '+kind,wire_bytes//16,('bus',src+'TX',dst+'RX'),
                (read,self.last_rx.get(dst)),kind=kind,payload=size,wire_bytes=wire_bytes)
            # Destination packet occupies its 2KiB RX until the whole write completes.
            write=self.memory(destination_port,size,destination_offset+off,(wire,),True,'packet-write '+kind)
            self.last_tx[src]=wire;self.last_rx[dst]=write;ends.append(write)
            self.packets.append(dict(kind=kind,src=src,dst=dst,payload=size,wire_bytes=wire_bytes,
                read=read,wire=wire,write=write))
            self.bytes['wire']+=wire_bytes;self.bytes['wire_payload']+=size
            self.bytes['wire_'+kind]+=wire_bytes
        return ends

    def schedule(self,policy):
        if policy not in ('fifo','critical'):raise ValueError('scheduler policy')
        children=[[] for _ in self.nodes];pending=[]
        for n in self.nodes:
            pending.append(len(n['deps']))
            for d in n['deps']:children[d].append(n['id'])
        height=[0]*len(self.nodes)
        for n in reversed(self.nodes):height[n['id']]=n['duration']+max((height[c] for c in children[n['id']]),default=0)
        key=lambda i:(i if policy=='fifo' else -height[i],i)
        ready=[key(i) for i,v in enumerate(pending) if not v];heapq.heapify(ready)
        active=[];occupied=set();now=0;finished=0;trace={};busy=Counter()
        while finished<len(self.nodes):
            deferred=[]
            while ready:
                item=heapq.heappop(ready);i=item[1];n=self.nodes[i]
                if occupied.intersection(n['resources']):deferred.append(item);continue
                occupied.update(n['resources']);trace[i]=[now,now+n['duration']]
                for r in n['resources']:busy[r]+=n['duration']
                heapq.heappush(active,(now+n['duration'],i))
            for item in deferred:heapq.heappush(ready,item)
            if not active:raise RuntimeError('dependency/resource deadlock')
            now=active[0][0]
            while active and active[0][0]==now:
                _,i=heapq.heappop(active);occupied.difference_update(self.nodes[i]['resources']);finished+=1
                for c in children[i]:
                    pending[c]-=1
                    if pending[c]==0:heapq.heappush(ready,key(c))
        return dict(cycles=now,busy=dict(busy),trace=trace)


def build(rows,k,scale_mode,placement,lanes,window,consumer_cost,jobs=4):
    if rows not in (1,16) or k not in (1024,3072) or lanes not in (1,8) or window not in (1,2):raise ValueError('unsupported fixture')
    if placement not in ('near','shared') or scale_mode not in ('static','dynamic_row'):raise ValueError('profile')
    g=Graph();elements=rows*16;params=80 if scale_mode=='static' else 5*elements
    last_m=[None]*2;last_v=[None]*2;last_a=[None]*2;last_w=[None]*2;last_rq=None
    last_prefetch=[None]*2;group_index=0;weights={};resident=(16*k<=16384)
    if resident:
        for kb in range(k//128):
            off=kb*2048
            weights[kb]=g.transfer('S0','M0',2048,'S0',f'MW{kb%2}',(),
                source_offset=off,destination_offset=(kb//2)*2048,kind='W8')
    static_meta=None
    if scale_mode=='static':
        dest='MC' if placement=='near' else 'VC';ep='M1' if placement=='near' else 'V1'
        static_meta=g.transfer('S4',ep,80,'S4',dest,(),destination_offset=2048,kind='META')
    for job in range(jobs):
        slot=job%window
        reserve_m=g.add('reserve M slot',1,('control',),(last_m[slot],))
        reserve_v=None
        if placement=='shared':reserve_v=g.add('reserve V slot',1,('control',),(last_v[slot],reserve_m))
        if scale_mode=='dynamic_row':
            dest='MC' if placement=='near' else 'VC';ep='M1' if placement=='near' else 'V1'
            dependency=reserve_m if placement=='near' else reserve_v
            meta=g.transfer('S4',ep,params,'S4',dest,(dependency,),job*params,2048+slot*1280,'META')
        else:meta=static_meta
        previous=reserve_m
        for kb in range(k//128):
            buffer=(job*(k//128)+kb)%2
            ao=kb*rows*128;so=2+ao//32768
            a=g.transfer(f'S{so}','M0',rows*128,f'S{so}',f'MA{buffer}',
                (reserve_m,last_a[buffer]),source_offset=ao%32768,kind='A8')
            if resident:w=weights[kb];wb=kb%2
            else:
                wo=kb*2048;sw=wo//32768;wb=buffer
                w=g.transfer(f'S{sw}','M0',2048,f'S{sw}',f'MW{wb}',
                    (reserve_m,last_w[wb]),source_offset=wo%32768,kind='W8')
            compute=g.add('matrix K128',128+rows+16-2,('matrix',f'MA{buffer}',f'MW{wb}'),
                          (previous,*a,*w),job=job,k_begin=kb*128,k_count=128)
            previous=compute;last_a[buffer]=compute
            if not resident:last_w[wb]=compute
        acc=g.memory('MC',elements*4,slot*1024,(previous,),True,'complete-K INT32')
        if placement=='shared':
            arrived=g.transfer('M0','V0',elements*4,'MC','VC',(acc,reserve_v),slot*1024,slot*1024,'ACC32')
            last_m[slot]=arrived[-1];local='VC'
        else:arrived=[acc];local='MC'
        output=[]
        for begin in range(0,elements,lanes):
            count=min(lanes,elements-begin);pslot=group_index%2
            read=g.memory(local,4*count,slot*1024+4*begin,(*arrived,last_prefetch[pslot]),label='RQ acc read')
            po=2048+(slot*1280 if scale_mode=='dynamic_row' else 0)+5*(begin if scale_mode=='dynamic_row' else begin%16)
            parameter=g.memory(local,5*count,po,(read,*meta),label='RQ M/r read')
            execute=g.add('RQ32 batch',26,('rq',),(parameter,last_rq),job=job,begin=begin,count=count)
            cooldown=g.add('RQ interface gap',2,('rq',),(execute,))
            store=g.memory(local,count,4608+slot*256+begin,(execute,),True,'RQ8 write')
            last_prefetch[pslot]=execute;group_index+=1
            last_rq=g.add('RQ next-start barrier',0,(),(cooldown,store))
            output.append(store)
        if placement=='near':
            reserve_v=g.add('reserve V slot',1,('control',),(last_v[slot],*output))
            output=g.transfer('M0','V0',elements,'MC','VC',(*output,reserve_v),4608+slot*256,4608+slot*256,'ACT8')
            last_m[slot]=output[-1]
        read=g.memory('VC',elements,4608+slot*256,(*output,),label='consumer read')
        consume=g.add('integer row-sum consumer',rows*(2*consumer_cost+1),('vector',),(read,),job=job)
        stored=g.memory('VC',rows*4,5120+slot*64,(consume,),True,'consumer result')
        exported=g.transfer('V0','S6',rows*4,'VC','S6',(stored,),5120+slot*64,job*rows*4,'SUM32')
        last_v[slot]=exported[-1]
        g.leases.extend([dict(kind='M',slot=slot,start=reserve_m,end=last_m[slot]),
                         dict(kind='V',slot=slot,start=reserve_v,end=last_v[slot])])
    return g


def audit_schedule(graph,scheduled):
    """Independent interval/dependency/capacity checks, not a second scheduler."""
    intervals=defaultdict(list)
    for n in graph.nodes:
        begin,end=scheduled['trace'][n['id']]
        assert end-begin==n['duration'] and begin>=0
        assert all(begin>=scheduled['trace'][d][1] for d in n['deps'])
        for r in n['resources']:intervals[r].append((begin,end,n['id']))
        if 'port' in n:assert n['offset']+n['bytes']<=graph.sizes[n['port']]
    for r,events in intervals.items():
        events.sort()
        assert all(a[1]<=b[0] for a,b in zip(events,events[1:])),r
        assert sum(e-b for b,e,_ in events)==scheduled['busy'][r]
    for packet in graph.packets:
        assert packet['wire_bytes']<=2048 and packet['wire_bytes']%64==0
        assert packet['wire_bytes']==64+beats(packet['payload'],word=64)*64
    for kind in ('M','V'):
        for slot in (0,1):
            leases=[(scheduled['trace'][x['start']][0],scheduled['trace'][x['end']][1])
                    for x in graph.leases if x['kind']==kind and x['slot']==slot]
            assert all(a[1]<=b[0] for a,b in zip(leases,leases[1:])),(kind,slot)
    for direction,phase in (('src',('read','wire')),('dst',('wire','write'))):
        queues=defaultdict(list)
        for p in graph.packets:
            queues[p[direction]].append((scheduled['trace'][p[phase[0]]][0],scheduled['trace'][p[phase[1]]][1]))
        for endpoint,events in queues.items():
            events.sort();assert all(a[1]<=b[0] for a,b in zip(events,events[1:])),endpoint
    assert scheduled['cycles']==max(e for _,e in scheduled['trace'].values())
    return {'nodes':len(graph.nodes),'packets':len(graph.packets),'leases':len(graph.leases),'resources':len(intervals)}
