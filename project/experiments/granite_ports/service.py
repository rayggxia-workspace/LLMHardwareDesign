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
RQ_DECODER_FEE_VERSION='NONNEGATIVE_MIN128_FOUR_TYPED_PLUS_FLAG_TEST76_V1'


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


def partial_write_beats(offset,n):
    if not n:return 0
    full=max(0,(offset+n)//16-(offset+15)//16)
    return beats(offset,n)-full


def packet_cost(src,dst,n):
    if min(src,dst,n)<0:raise ValueError('negative packet')
    c=Counter();done=0
    while done<n:
        amount=min(1984,n-done);wire=32+16*((amount+15)//16)
        c.update(src_beats=beats(src+done,amount),dst_beats=beats(dst+done,amount),dst_rmw_beats=partial_write_beats(dst+done,amount),wire_beats=wire//16,wire_bytes=wire,packets=1,payload_bytes=amount)
        done+=amount
    return dict(c)


class Builder:
    """Compressed affine witness, strict serial calendar, fixed finite buffers."""
    def __init__(self,tile,placement,calibration):
        if tile not in (128,256,1536) or placement not in ('M','V'):raise ValueError('frozen configuration')
        self.tile=tile;self.owner=placement;self.cal=calibration
        self.cap={'M':32*KIB,'V':16*KIB,'R':32*KIB,**{'S'+str(i):32*KIB for i in range(8)},'EXT':128*MIB,'ROM':4260100}
        self.alloc={};self.used=Counter();self.phase_base={};self.phase_cursor={};self.events=[];self.clock=0;self.counts=Counter()
        self.inventory={'capacities':self.cap,'banks':{k:{'bits':128,'kind':'1RW','partial_write':'128bit endpoint RMW, no assumed byte mask'} for k in self.cap if k!='ROM'},
            'matrix':{'resource':'M256','S8_PEs':256,'shape':[16,16],'effective_B1_PEs':16,'Ktile':512,'weight_bytes':8192,'accumulator_register_bytes':64,'A_register_bytes':16,'weight_register_bytes':16},
            'vector':{'resource':'VR8','byte_lanes':8,'policy':'scalar dependency cycles, never total carry/8','internal_staging_from_FIFO':True},
            'SFU':{'count':1,'resource':'SFU','borrows':'VR8 lane0','extra_byte_ALU':False},
            'ROM':{'capacity':4260100,'return_bits':32,'ports':1,'latency':2,'II':1,'synchronous_candidate':True},
            'packet':{'BUS_count':1,'BUS_bits':128,'beat_bytes':16,'header_bytes':32,'max_payload_bytes':1984,'FIFO_bytes':2048},
            'policy':'strict serialized B1; no free prefill/decode batching, no optimality/RTL/PPA claim'}

    def add(self,name,bank,n,role='scratch'):
        if name in self.alloc or bank not in self.cap or n<0 or bank in self.phase_base:raise ValueError('allocation/global-after-phase')
        alignment=4 if bank=='ROM' else 16
        offset=(self.used[bank]+alignment-1)//alignment*alignment
        if offset+n>self.cap[bank]:raise ValueError('capacity '+bank+' '+name)
        self.alloc[name]={'object':name,'bank':bank,'offset':offset,'bytes':int(n),'role':role,'lifetime':['task_start','task_end']}
        self.used[bank]=offset+n
        return name

    def add_phase(self,name,bank,n,phase,role='scratch'):
        if phase not in ('front','down','norm') or name in self.alloc:raise ValueError('phase allocation')
        base=self.phase_base.setdefault(bank,self.used[bank]);key=(bank,phase)
        cursor=self.phase_cursor.get(key,base);offset=(cursor+15)//16*16
        if offset+n>self.cap[bank]:raise ValueError('capacity '+bank+' '+name)
        self.alloc[name]={'object':name,'bank':bank,'offset':offset,'bytes':int(n),'role':role,
            'lifetime':{'kind':'token_phase','phases':[phase],'every_token':True,'barriers':'front -> down -> norm -> next_token'}}
        self.phase_cursor[key]=offset+n;self.used[bank]=max(self.used[bank],offset+n);return name

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
        c['bank_beats']=c.get('src_beats',0)+c.get('dst_beats',0)+c.get('dst_rmw_beats',0)
        packets=[];done=0;cursor=0;peak=0
        while done<n:
            size=min(1984,n-done);sa=s['offset']+so+done;da=d['offset']+do+done
            sb=beats(sa,size);db=beats(da,size);rmw=partial_write_beats(da,size);wire=2+(size+15)//16
            source_peak=32+16*sb;destination_peak=32+16*((size+15)//16)+16*rmw
            packet_peak=max(source_peak,destination_peak);peak=max(peak,packet_peak)
            duration=sb+wire+db+rmw
            packets.append({'index':len(packets),'src_offset':so+done,'dst_offset':do+done,'payload_bytes':size,
                'src_absolute_offset':sa,'dst_absolute_offset':da,'src_beats':sb,'dst_beats':db,'dst_rmw_beats':rmw,
                'wire_beats':wire,'start':cursor,'end':cursor+duration,'FIFO_peak_bytes':packet_peak,
                'steps':[{'resource':'bank.'+s['bank'],'start':cursor,'end':cursor+sb},
                    {'resource':'BUS','start':cursor+sb,'end':cursor+sb+wire},
                    {'resource':'bank.'+d['bank'],'start':cursor+sb+wire,'end':cursor+duration,'operation':'destination old-line RMW reads then writes'}]})
            cursor+=duration;done+=size
        if peak>2048:raise ValueError('finite packet/RMW FIFO')
        names=list(dict.fromkeys(('bank.'+s['bank'],'BUS','bank.'+d['bank'])))
        return self.leaf(body,'transfer',[(name,cursor) for name in names],simultaneous=True,
            accesses=[self.access(src,so,n,index_strides=src_index),self.access(dst,do,n,'write',index_strides=dst_index)],
            counts=c,FIFO_peak_bytes=peak,packet={'src':src,'dst':dst,'src_offset':so,'dst_offset':do,'bytes':n,'partial_write':'endpoint RMW'},
            serial_packet_retiming_certificate={'kind':'bounded_serial_packet_retiming','max_payload_bytes':1984,'header_bytes':32,
                'per_packet_order':'source reads -> BUS -> destination RMW/read/write','resident_payload_only_one_packet':True,
                'all_endpoint_state_within_FIFO':True,'duration_formula':'sum(src_beats + wire_beats + dst_beats + dst_rmw_beats)',
                'FIFO_peak_rule':'max(32+16*source_physical_beats,32+16*ceil(payload/16)+16*destination_partial_beats)',
                'packet_times_relative_to_leaf':True,'source_index_strides':list(src_index),'destination_index_strides':list(dst_index),
                'resource_reservation':'unique bank/BUS resources reserved for whole leaf; explicit packet steps fit inside, global serial policy',
                'packets':packets})

    def engine(self,body,obj,offset,n,mode='read',index=()):
        if n>512:raise ValueError('engine caller staging exceeds512; large transfer requires packet certificate')
        a=self.alloc[obj];c=packet_cost(a['offset']+offset,0,n) if mode=='read' else packet_cost(0,a['offset']+offset,n)
        bankbeats=c.get('src_beats',0) if mode=='read' else c.get('dst_beats',0)+c.get('dst_rmw_beats',0)
        rr=[('bank.'+a['bank'],bankbeats),('BUS',c.get('wire_beats',0))] if mode=='read' else [('BUS',c.get('wire_beats',0)),('bank.'+a['bank'],bankbeats)]
        peak=32+16*((min(n,1984)+15)//16)+(16*partial_write_beats(a['offset']+offset,min(n,1984)) if mode=='write' else 0)
        return self.leaf(body,'engine_access',rr,accesses=[self.access(obj,offset,n,mode,index_strides=index)],
            counts={**c,'bank_beats':bankbeats,'engine_read_bytes' if mode=='read' else 'engine_write_bytes':n},FIFO_peak_bytes=peak,engine='shared BUS-attached VR8')

    def compute(self,body,op,count=1,parameters=None):
        item=self.cal['ops'].get(op)
        if not item or item.get('proof',{}).get('kind')!='fixed_loops_exhaustive_shift_domain':raise ValueError('unknown/unqualified width fee '+op)
        c=item['costs'];count=int(count)
        if c['SIMD8_qualified'] is not False or c['frame_capacity_bytes']!=512 or c['scratch_peak_bytes']>512:
            raise ValueError('bounded scalar microprogram '+op)
        alu=int(c['scalar_ALU_dependency_cycles'])*count;dispatch=int(c['software_controller_dispatches'])*count
        if int(c['conservative_scalar_cycles_ALU_plus_dispatch'])*count!=alu+dispatch:raise ValueError('explicit controller surcharge')
        reads=(int(c['byte_store_reads'])+int(c['result_read_bytes']))*count
        writes=(int(c['byte_store_writes'])+int(c['input_load_bytes']))*count
        total=alu+dispatch+4*reads+5*writes
        uses_sfu=op in ('udiv_u128','isqrt_u128','div_rne_s128_u64_i32')
        # Each scalar instruction can be legally retimed read<=3 -> ALU -> write<=2.
        # Whole-leaf resource reservations enclose that schedule; global policy is serial.
        resources=[('VR8',total),('bank.V',total),('BUS',total)]
        if uses_sfu:resources.append(('SFU',total))
        frame=self.alloc.get('V.microframe')
        if frame is None:raise ValueError('microframe backing absent')
        return self.leaf(body,'micro',resources,simultaneous=True,op=op,count=count,parameters=parameters or {},
            counts={'op.'+op:count,'micro_alu_cycles':alu,'micro_dispatch_cycles':dispatch,
                'micro_frame_read_bytes':reads,'micro_frame_write_bytes':writes,'bank_beats':reads+2*writes,'micro_frame_write_RMW_read_beats':writes,
                'wire_bytes':48*(reads+writes),'wire_beats':3*(reads+writes),'packets':reads+writes,'payload_bytes':reads+writes},
            microprogram_sha256=self.cal['source']['micro_sha256'],proof=item['proof'],scratch_peak_bytes=int(c['scratch_peak_bytes']),
            accesses=[{'object':'V.microframe','offset':0,'bytes':1,'mode':mode,'repeat':1,'stride':0,'index_strides':[],
                'address_class':{'kind':'source_bound_microprogram_byte_frame','minimum':0,'maximum':511,'access_count':number}}
                for mode,number in (('read',reads),('write',writes))],
            FIFO_peak_bytes=1024,operand_register_bytes=5,caller_staging_budget_bytes=512,
            retiming_certificate={'kind':'fixed_source_byte_microprogram','per_scalar_instruction':'read <=3 frame bytes; 1 byte ALU; <=2 frame writes; one controller dispatch',
                'all_accesses_within_allocated_frame':True,'input_initialization_and_result_extract_included':True,
                'each_byte_access':'read:1 V128 beat+48B BUS; write:128bit endpoint RMW2 V beats+48B BUS; old16B line in already charged FIFO',
                'duration_formula':'ALU+dispatch+4*frame_reads+5*frame_writes',
                'reservation':'whole leaf blocks V/BUS/VR8(+SFU); a legal serial retiming fits inside, no overlap with other leaves',
                'controller_level':'candidate one dispatch/action, full FSM not RTL implemented'})

    def macro(self,stage,body,meta):
        ident=len(self.events);duration=body[-1]['end'] if body else 0
        event={'id':ident,'stage':stage,'start':self.clock,'end':self.clock+duration,'deps':[ident-1] if ident else [],'meta':meta,'body':body}
        self.events.append(event);self.clock+=duration;self.count_tree(body,1);return event

    def count_tree(self,nodes,mult):
        for node in nodes:
            if node['kind']=='loop':self.count_tree(node['body'],mult*node['count'])
            else:
                for k,v in node.get('counts',{}).items():self.counts[k]+=int(v)*mult



def allocate(b):
    # Persistent target objects. Scientific source archives are not deployed copies.
    for name,n in [('a',1536),('weight',8192),('acc_store',64),('acc_regs',64),('a_regs',16),('w_regs',16),
                   ('scale_q31',64),('scale_exp',32),('delta',16),('rq_product64',128),('rq_out32',64),('shift64',128)]:
        b.add('M.'+name,'M',n,'matrix/register' if name.endswith('_regs') else 'scratch')
    for name,n in [('microframe',512),('byte_regs',40),('ctrl64',64),('p64',128),('n128',128),('small32',64),('sum128',16),
                   ('var128',16),('rad128',16),('den64',16),('gamma32',64),('out32',64),('index32',64),('x32',64),('y32',64),('shift64',128)]:
        b.add('V.'+name,'V',n,'VR8_operand_registers' if name=='byte_regs' else 'scratch')
    b.add('S0.mid_a8','S0',8*512);b.add('S0.mid_delta','S0',16);b.add('S0.mid_delta64','S0',64);b.add('S0.input_delta64','S0',8)
    for name,n in [('ids',8),('gates',16),('input_delta',2),('dispatch',64)]:b.add('S0.'+name,'S0',n)
    b.add('const.gate_up_w8','EXT',40*1024*1536,'static_packed_weight')
    b.add('const.down_w8','EXT',40*1536*512,'static_packed_weight')
    for which,O in [('gate_up',1024),('down',1536)]:
        b.add('const.'+which+'_mant','EXT',40*O*4,'static_scale')
        b.add('const.'+which+'_exp','EXT',40*O*2,'static_scale')
    b.add('const.next_gamma','EXT',1536*4,'static_Q20');b.add('const.scalars','EXT',96,'static_integer')
    b.add('const.zero','EXT',16,'static_zero');b.add('const.dispatch','EXT',40*64,'static_descriptor')
    for name,n in [('norm',72*1536*4),('residual',72*1536*4),('ids',72*8),('gates',72*8*2)]:b.add('cut.'+name,'EXT',n,'external_cut_preloaded')
    for name in ('layer_output','nextnorm'):b.add('ext.'+name,'EXT',72*1536*4,'target_output')
    b.add('const.silu','ROM',16385*4,'static_LUT');b.add('const.router_exp2','ROM',2049*4,'external_cut_LUT_reserve');b.add('ROM.padding','ROM',131072-73736,'physical_ROM_unused_padding')
    # Front arrays die after all eight midA8+delta rows are durably in S0.
    for name,n in [('gateup',4096),('silu',2048),('mid',2048),('norm_a8',1536)]:b.add_phase('front.'+name,'V',n,'front')
    # Physical return/RQ scratch remains O16 even for a full-H logical merge.
    b.add_phase('down.merge64',b.owner,b.tile*8,'down')
    if b.owner=='V':
        for name,n in [('acc32',64),('mant',64),('exp',32),('shift64',128),('product64',128),('out32',64)]:b.add_phase('down.'+name,'V',n,'down')
    return {'peak_bytes':dict(b.used),'phase_peak_bytes':{bank:{phase:b.phase_cursor.get((bank,phase),b.phase_base.get(bank,b.used[bank])) for phase in ('front','down','norm')} for bank in ('M','V')},
        'full8S32_return_bytes':8*1536*4,'full_H_merge64_bytes':1536*8,'no_full_Q12_return_co_resident':True,
        'owner_physical_RQ_elements':16,'phase_aliasing':'disjoint token phases only; all tokens serial, nextnorm precedes reuse',
        'negative_full8S32_V':'REJECTED:49152 > 16384 before other live objects'}



def kernel(b,body,op,count,reads,writes,parameters=None):
    """Caller operands/results are real BUS/bank accesses; no unbounded RF."""
    staging=sum(x[2] for x in reads)+sum(x[2] for x in writes)
    if staging>512:raise ValueError('caller staging exceeds fixed FIFO slice')
    for obj,offset,n,index in reads:b.engine(body,obj,offset,n,index=index)
    b.compute(body,op,count,{**(parameters or {}),'caller_staging_bytes':staging})
    for obj,offset,n,index in writes:b.engine(body,obj,offset,n,'write',index)


def at(obj,offset,n,index=()):return (obj,offset,n,tuple(index))


def meta(token,phase,**kw):return {'token':int(token),'phase':phase,**kw}


def rne_s64_observer(value,shift):
    """Offline exact observer only; target RNE/decoder costs are separate."""
    value=int(value);shift=int(shift)
    if not -(1<<63)<=value<(1<<63) or shift<0:raise ValueError('S64/nonnegative observer domain')
    if shift==0:return value
    q,r=divmod(abs(value),1<<shift);half=1<<(shift-1)
    q+=int(r>half or (r==half and q%2))
    return -q if value<0 else q


def rq_decoder_evidence(trace,const):
    """All real metadata, plus exact proof witnesses at every changed position.

    Source exponent/delta/product/published codes remain immutable.  This is
    scientific bookkeeping, never an uncharged target decoding operation.
    """
    evidence={'schema':'granite-rq-decoder76-v1','fee_version':RQ_DECODER_FEE_VERSION,'raw_formula':'31-weight_exponent_I16-current_activation_delta_I16',
        'decoded_formula':'128-max(128-raw_shift,0), guarded raw_shift>=0',
        'proof':'For signed S64 n and s>=64, |n|/2**s<=1/2; the only equality is I64_MIN at s64, tie-to-even zero. Hence all s>128 may map to128 exactly.',
        'target_policy':'all outputs execute cmp/sub/max/sub and explicit flag consumption; no observed-position shortcut',
        'observer_cost':'hashes/histograms/equality witnesses are offline observations, not target operations',
        'operations':{}}
    ids=np.asarray(trace['router.ids'])
    if np.any(ids<0) or np.any(ids>=40):raise ValueError('actual expert ID range')
    for which,pkey,qkey in (('gate_up','gate_up_RQ_product64','gate_up_q12'),('down','down_RQ_product64','down_q12')):
        exp=np.asarray(const[which+'_exp'])
        if exp.dtype!=np.int16 or exp.ndim!=2 or exp.shape[0]!=40:raise ValueError('source exponent I16/40 experts')
        product=np.asarray(trace[pkey]);published=np.asarray(trace[qkey]);O=exp.shape[1]
        if ids.shape!=(72,8) or product.dtype!=np.int64 or product.shape!=(72,8,O) or published.shape!=product.shape:
            raise ValueError('complete actual S64 RQ products/published codes')
        raw=np.empty(product.shape,np.int64);decoded=np.empty_like(raw);changed=[]
        for token in range(72):
            for rank,expert in enumerate(ids[token]):
                delta=int(trace['expert_input_delta'][token]) if which=='gate_up' else int(trace['mid_delta'][token,rank])
                row=31-exp[int(expert)].astype(np.int64)-delta
                if np.any(row<0):raise ValueError('negative actual RQ shift needs explicit left-shift/overflow policy; no clamp')
                raw[token,rank]=row;decoded[token,rank]=128-np.maximum(128-row,0)
                for output in np.flatnonzero(row>128):
                    n=int(product[token,rank,output]);s=int(row[output]);d=int(decoded[token,rank,output])
                    before=rne_s64_observer(n,s);after=rne_s64_observer(n,d);q=int(published[token,rank,output])
                    if before!=after or before!=q or before!=0:raise ValueError('actual decoder RNE/published equivalence')
                    changed.append({'token':token,'phase':'prefill64' if token<64 else 'decode8','rank':rank,'expert':int(expert),'output':int(output),
                        'weight_exponent_I16':int(exp[int(expert),output]),'activation_delta_I16':delta,'raw_shift':s,'decoded_shift':d,
                        'RQ_product_S64':n,'original_RNE':before,'decoded_RNE':after,'published_Q12':q})
        hist=lambda a:{str(int(k)):int(v) for k,v in zip(*np.unique(a,return_counts=True))}
        evidence['operations'][which]={'shape':list(raw.shape),'actual_outputs':int(raw.size),'raw_minimum':int(raw.min()),'raw_maximum':int(raw.max()),
            'decoded_minimum':int(decoded.min()),'decoded_maximum':int(decoded.max()),'negative_count':0,'changed_count':len(changed),
            'raw_histogram':hist(raw),'decoded_histogram':hist(decoded),'raw_array_sha256':array_sha(raw),'decoded_array_sha256':array_sha(decoded),
            'raw_token_rank_sha256':[[array_sha(raw[t,r]) for r in range(8)] for t in range(72)],
            'decoded_token_rank_sha256':[[array_sha(decoded[t,r]) for r in range(8)] for t in range(72)],
            'source_product_key':pkey,'source_published_key':qkey,'source_product_array_sha256':array_sha(product),
            'source_published_array_sha256':array_sha(published),'changed_positions':changed,'unchanged_positions_identical_shift':int(raw.size)-len(changed)}
    return evidence


def dynamic(b,token,phase,which,n,source,source_offset,destination,destination_offset,delta,rank=None):
    """Full current-row absmax, causal minimal RNE shift, full encode."""
    body=[];b.transfer(body,'const.zero','V.ctrl64',16,0,0)
    scan=[]
    kernel(b,scan,'align_s32_i64',8,[at(source,source_offset,32,(32,))],[at('V.p64',0,64)],{'shift':0})
    kernel(b,scan,'abs_s64',8,[at('V.p64',0,64)],[at('V.p64',0,64)])
    element=[];kernel(b,element,'max_s64',1,[at('V.p64',0,8,(8,)),at('V.ctrl64',0,8)],[at('V.ctrl64',0,8)])
    b.loop(scan,8,element);b.loop(body,n//8,scan)
    b.macro(which+'.full_absmax_scan',body,meta(token,phase,K=n,rank=rank,source=source,complete_current_row=True))
    b.macro(which+'.scan_barrier',[],meta(token,phase,K=n,rank=rank,all_elements_before_scale=True))
    control=[]
    for probe in range(int(delta)+1):
        kernel(b,control,'rne_s64_i32',1,[at('V.ctrl64',0,8)],[at('V.small32',0,4)],{'shift':probe,'probe':probe})
        kernel(b,control,'align_s32_i64',1,[at('V.small32',0,4)],[at('V.p64',0,8)],{'shift':0})
        kernel(b,control,'cmp_s64',1,[at('V.p64',0,8),at('const.scalars',56,8)],[at('V.ctrl64',16,2)])
        if probe<int(delta):kernel(b,control,'add_s64',1,[at('V.ctrl64',8,8)],[at('V.ctrl64',8,8)],{'second_operand_immediate':1,'control':'advance exactly after failed bound'})
    delta32='S0.input_delta' if rank is None else 'S0.mid_delta'
    delta64='S0.input_delta64' if rank is None else 'S0.mid_delta64'
    off=0 if rank is None else int(rank)*2;off64=0 if rank is None else int(rank)*8
    b.transfer(control,'V.ctrl64',delta64,8,8,off64)
    # loop invariant 0<=delta<=128 makes low-I16 store exact; target scan paid.
    b.transfer(control,'V.ctrl64',delta32,2,8,off)
    b.macro(which+'.minimal_shift_publish',control,meta(token,phase,K=n,rank=rank,delta=int(delta),published_format='I16 plus explicit S64 cache',minimal_RNE_bound=127))
    encode=[]
    kernel(b,encode,'align_s32_i64',8,[at(source,source_offset,32,(32,))],[at('V.p64',0,64)],{'shift':0})
    kernel(b,encode,'rne_s64_i32',8,[at('V.p64',0,64),at(delta64,off64,8)],[at(destination,destination_offset,8,(8,))],
        {'shift':int(delta),'narrow_result':'low8 after full-row monotone RNE proof of symmetric [-127,127]; no saturation','delta_object':delta64})
    all_encode=[];b.loop(all_encode,n//8,encode)
    b.macro(which+'.A8_encode',all_encode,meta(token,phase,K=n,rank=rank,delta=int(delta),complete_current_row=True,narrow_output_bytes=1))


def matrix(b,token,phase,which,expert,rank,O,K,Ostart,Ocount,delta,merge=False):
    """O16 physical PE tile, K512 packed storage, complete-K before RQ."""
    if Ocount%16 or K%512:raise ValueError('physical matrix divisibility')
    owner=b.owner if merge else 'M'
    acc='M.acc_store' if owner=='M' else 'down.acc32'
    mant='M.scale_q31' if owner=='M' else 'down.mant';exponent='M.scale_exp' if owner=='M' else 'down.exp'
    shifts='M.shift64' if owner=='M' else 'down.shift64'
    product='M.rq_product64' if owner=='M' else 'down.product64';out='M.rq_out32' if owner=='M' else 'down.out32'
    d64='S0.mid_delta64' if merge else 'S0.input_delta64';doff=rank*8 if merge else 0
    outer=[];one=[]
    b.leaf(one,'matrix_acc_reset',[('M256',1)],counts={'matrix_resets':1},register_object='M.acc_regs',bytes=64)
    kb=[]
    b.transfer(kb,'const.'+which+'_w8','M.weight',8192,expert*O*K+(Ostart//16)*16*K,0,src_index=(16*K,8192))
    k16=[];b.memory(k16,[b.access('M.a',0,16,index_strides=(512,16))])
    k1=[];b.memory(k1,[b.access('M.weight',0,16,index_strides=(256,16))])
    b.leaf(k1,'matrix_mac16',[('M256',1)],counts={'matrix_S8_MACs':16,'matrix_issued_cycles':1},
        active_PEs=16,accumulator_register_bytes=64,A_register_bytes=16,W_register_bytes=16,operation='16 S8xS8+S32 native matrix accumulators')
    b.loop(k16,16,k1);b.loop(kb,32,k16);b.loop(one,K//512,kb)
    b.memory(one,[b.access('M.acc_store',0,64,'write')])
    if owner=='V':b.transfer(one,'M.acc_store',acc,64)
    b.transfer(one,'const.'+which+'_mant',mant,64,expert*O*4+Ostart*4,0,src_index=(64,))
    b.transfer(one,'const.'+which+'_exp',exponent,32,expert*O*2+Ostart*2,0,src_index=(32,))
    kernel(b,one,'signextend_s16_i64',16,[at(exponent,0,32)],[at(shifts,0,128)])
    kernel(b,one,'sub_s64',16,[at('const.scalars',48,8),at(shifts,0,128)],[at(shifts,0,128)],{'broadcast_a':True,'formula':'31-exponent'})
    kernel(b,one,'sub_s64',16,[at(shifts,0,128),at(d64,doff,8)],[at(shifts,0,128)],{'broadcast_b':True,'formula':'31-exponent-delta','delta':int(delta)})
    kernel(b,one,'cmp_s64',16,[at(shifts,0,128),at('const.zero',0,8)],[at('V.small32',0,32)],
        {'broadcast_b':True,'guard':'raw RQ shift must be nonnegative; reject otherwise, never clamp a negative shift'})
    b.engine(one,'V.small32',0,32)
    b.leaf(one,'rq_nonnegative_guard',[('VR8',16)],counts={'rq_shift_guard_controller_slots':16},
        count=16,source='V.small32',less_flag_stride_bytes=2,negative_action='abort before decoder/RNE',
        action='candidate controller: one less-flag test/dispatch per output; fault if less',
        controller_level='same software-controller candidate as micro dispatch, not independently implemented full FSM')
    kernel(b,one,'sub_s64',16,[at('const.scalars',64,8),at(shifts,0,128)],[at(shifts,0,128)],{'broadcast_a':True,'formula':'128-raw_shift'})
    kernel(b,one,'max_s64',16,[at(shifts,0,128),at('const.zero',0,8)],[at(shifts,0,128)],{'broadcast_b':True,'formula':'max(128-raw_shift,0)'})
    kernel(b,one,'sub_s64',16,[at('const.scalars',64,8),at(shifts,0,128)],[at(shifts,0,128)],{'broadcast_a':True,'formula':'128-max(128-raw_shift,0)'})
    kernel(b,one,'mul_s32_s32',16,[at(acc,0,64),at(mant,0,64)],[at(product,0,128)])
    kernel(b,one,'rne_s64_i32',16,[at(product,0,128),at(shifts,0,128)],[at(out,0,64)],
        {'shift_source':which+'_exp plus current delta through charged nonnegative guard/min128 decoder','shift_domain':[0,128],
            'raw_shift_formula':'31-exponent-delta','decoded_shift_formula':'128-max(128-raw_shift,0)','fraction_output':12})
    if merge:
        kernel(b,one,'mul_s32_u16',16,[at(out,0,64),at('S0.gates',rank*2,2)],[at(product,0,128)],{'broadcast_b':True,'gate_rank':rank,'gate_format':'U16Q15'})
        kernel(b,one,'add_s64',16,[at('down.merge64',0,128,(128,)),at(product,0,128)],[at('down.merge64',0,128,(128,))],
            {'rank_prefix':rank,'first_rank_adds_materialized_zero':rank==0})
    else:b.transfer(one,out,'front.gateup',64,0,Ostart*4,dst_index=(64,))
    b.loop(outer,Ocount//16,one)
    b.macro(which+'.fullK_RQ_merge' if merge else which+'.fullK_RQ',outer,
        meta(token,phase,expert=int(expert),rank=rank,O=O,K=K,Ostart=Ostart,Ocount=Ocount,physical_O=16,physical_K=512,
            delta=int(delta),RQ_owner=owner,packed_weight=True,full_K_before_RQ=True,INT32_abs_bound=K*127*127,
            logical_merge_window=b.tile if merge else None,complete_rank_prefix=rank if merge else None))


def front(b,token,trace):
    dynamic(b,token,'front','expert_input',1536,'cut.norm',token*1536*4,'front.norm_a8',0,int(trace['expert_input_delta'][token]))
    entry=[];b.transfer(entry,'cut.ids','S0.ids',8,token*8);b.transfer(entry,'cut.gates','S0.gates',16,token*16)
    b.transfer(entry,'front.norm_a8','M.a',1536)
    b.macro('front.published_router_and_A8',entry,meta(token,'front',input_cut='norm/router already published',router_execution_included=False,actual_routes=trace['router.ids'][token].tolist()))
    for rank,expert in enumerate(trace['router.ids'][token]):
        dispatch=[];b.transfer(dispatch,'const.dispatch','S0.dispatch',64,int(expert)*64)
        b.macro('front.expert_dispatch',dispatch,meta(token,'front',rank=rank,expert=int(expert),descriptor_bytes=64))
        matrix(b,token,'front','gate_up',int(expert),rank,1024,1536,0,1024,int(trace['expert_input_delta'][token]))
        # Actual frozen cases have no SiLU out-of-domain path. Both bounds still checked.
        silu=[]
        kernel(b,silu,'align_s32_i64',8,[at('front.gateup',0,32,(32,))],[at('V.p64',0,64)],{'shift':0})
        kernel(b,silu,'cmp_s64',8,[at('V.p64',0,64),at('const.scalars',80,8)],[at('V.small32',0,16)],{'bound':'negative32Q12','broadcast_b':True})
        kernel(b,silu,'cmp_s64',8,[at('V.p64',0,64),at('const.scalars',88,8)],[at('V.small32',0,16)],{'bound':'positive32Q12','broadcast_b':True})
        kernel(b,silu,'rne_s64_i32',8,[at('V.p64',0,64)],[at('V.index32',0,32)],{'shift':4,'LUT_index_step':'2^-8'})
        kernel(b,silu,'align_s32_i64',8,[at('V.index32',0,32)],[at('V.p64',0,64)],{'shift':0})
        kernel(b,silu,'add_s64',8,[at('V.p64',0,64),at('const.scalars',72,8)],[at('V.p64',0,64)],{'broadcast_b':True,'add':8192})
        kernel(b,silu,'rne_s64_i32',8,[at('V.p64',0,64)],[at('V.index32',0,32)],{'shift':0})
        lookup=[]
        b.engine(lookup,'V.index32',0,4,index=(4,))
        # Dynamic aligned32bit table word. Every index is checked/bound to original trace.
        b.leaf(lookup,'ROM_read',[('bank.ROM',2)],accesses=[{'object':'const.silu','offset':0,'bytes':4,'mode':'read','repeat':1,'stride':0,'index_strides':[],
            'address_class':{'kind':'original_runtime_LUT_index','key':'silu_lut_index','token':token,'rank':rank,'minimum':0,'maximum':65536,'alignment':4}}],
            counts={'ROM_word32_reads':1,'ROM_latency_slots':2},ROM_bits=32,latency=2,II=1)
        # Request/reply traffic: the request above was engine read32; response is another packet.
        b.leaf(lookup,'ROM_response',[('BUS',3),('bank.V',2)],accesses=[b.access('front.silu',0,4,'write',index_strides=(32,4))],
            counts={'wire_bytes':48,'wire_beats':3,'packets':1,'payload_bytes':4,'bank_beats':2,'dst_rmw_beats':1},FIFO_peak_bytes=64)
        b.loop(silu,8,lookup);all_silu=[];b.loop(all_silu,64,silu)
        b.macro('front.silu_LUT',all_silu,meta(token,'front',rank=rank,expert=int(expert),elements=512,all_in_domain=True,ROM='word32 latency2 II1',result_fraction=12))
        middle=[]
        kernel(b,middle,'mul_s32_s32',8,[at('front.silu',0,32,(32,)),at('front.gateup',2048,32,(32,))],[at('V.p64',0,64)])
        kernel(b,middle,'rne_s64_i32',8,[at('V.p64',0,64)],[at('front.mid',0,32,(32,))],{'shift':12,'product_fraction':24,'output_fraction':12})
        all_mid=[];b.loop(all_mid,64,middle)
        b.macro('front.mid_Q12',all_mid,meta(token,'front',rank=rank,expert=int(expert),elements=512,original_contract=True))
        dynamic(b,token,'front','mid',512,'front.mid',0,'S0.mid_a8',rank*512,int(trace['mid_delta'][token,rank]),rank)
    b.macro('front.all8_mid_persisted',[],meta(token,'front',rank_count=8,midA8_bytes=4096,delta_bytes=16,extra_delta64_cache_bytes=64,release_front_arrays=True))


def downstream(b,token,trace):
    for start in range(0,1536,b.tile):
        init=[];zero=[];b.transfer(zero,'const.zero','down.merge64',16,0,0,dst_index=(16,));b.loop(init,b.tile//2,zero)
        b.macro('down.merge_init',init,meta(token,'down',Ostart=start,Ocount=b.tile,merge_bytes=b.tile*8,owner=b.owner))
        for rank,expert in enumerate(trace['router.ids'][token]):
            load_mid=[];b.transfer(load_mid,'S0.mid_a8','M.a',512,rank*512)
            b.transfer(load_mid,'const.dispatch','S0.dispatch',64,int(expert)*64)
            b.macro('down.load_mid_and_dispatch',load_mid,meta(token,'down',Ostart=start,Ocount=b.tile,rank=rank,expert=int(expert),reloaded_mid_bytes=512))
            matrix(b,token,'down','down',int(expert),rank,1536,512,start,b.tile,int(trace['mid_delta'][token,rank]),True)
        emit=[];ownerout='M.rq_out32' if b.owner=='M' else 'down.out32';ownerprod='M.rq_product64' if b.owner=='M' else 'down.product64'
        kernel(b,emit,'rne_s64_i32',16,[at('down.merge64',0,128,(128,))],[at(ownerout,0,64)],{'shift':15,'complete_all8_prefix':True})
        kernel(b,emit,'mul_s32_s32',16,[at(ownerout,0,64),at('const.scalars',0,4)],[at(ownerprod,0,128)],{'broadcast_b':True,'coefficient_Q20':230687})
        kernel(b,emit,'rne_s64_i32',16,[at(ownerprod,0,128)],[at(ownerout,0,64)],{'shift':20})
        kernel(b,emit,'align_s32_i64',16,[at(ownerout,0,64)],[at(ownerprod,0,128)],{'shift':0})
        kernel(b,emit,'align_s32_i64',16,[at('cut.residual',token*6144+start*4,64,(64,))],[at('V.p64',0,128)],{'shift':0})
        kernel(b,emit,'add_s64',16,[at(ownerprod,0,128),at('V.p64',0,128)],[at(ownerprod,0,128)])
        kernel(b,emit,'rne_s64_i32',16,[at(ownerprod,0,128)],[at(ownerout,0,64)],{'shift':0,'guard':'I32 no saturation'})
        b.transfer(emit,ownerout,'ext.layer_output',64,0,token*6144+start*4,dst_index=(64,))
        output=[];b.loop(output,b.tile//16,emit)
        b.macro('down.merge8_RNE15_scale_residual_emit',output,meta(token,'down',Ostart=start,Ocount=b.tile,complete_all8=True,output_chunk=16,output_target='ext.layer_output',no_full_Q12_output_buffer=True))
    b.macro('down.full1536_layer_output_barrier',[],meta(token,'down',elements=1536,complete_layer_output_before_norm=True,release_merge=True))


def nextnorm(b,token):
    init=[];b.transfer(init,'const.zero','V.sum128',16)
    b.macro('norm.init_sum128',init,meta(token,'norm',complete_group=1536))
    chunk=[]
    kernel(b,chunk,'mul_s32_s32',8,[at('ext.layer_output',token*6144,32,(32,)),at('ext.layer_output',token*6144,32,(32,))],[at('V.p64',0,64)],{'square':True})
    element=[]
    kernel(b,element,'add_u128',1,[at('V.sum128',0,16),at('V.p64',0,8,(8,))],[at('V.sum128',0,16)],
        {'zero_extend_second_S64_nonnegative_square':True,'first_add_zero_is_explicit_padding':True})
    b.loop(chunk,8,element);reduce=[];b.loop(reduce,192,chunk)
    b.macro('norm.full1536_sumsq',reduce,meta(token,'norm',elements=1536,U128_adds=1536,one_zero_add_padding=True,whole_group=True))
    barrier=[]
    kernel(b,barrier,'udiv_u128',1,[at('V.sum128',0,16),at('const.scalars',32,16)],[at('V.var128',0,16),at('V.rad128',0,16)],{'floor_divisor':1536,'output_order':'quotient then remainder'})
    kernel(b,barrier,'add_u128',1,[at('V.var128',0,16),at('const.scalars',16,16)],[at('V.var128',0,16)],{'epsilon_Q24':17})
    kernel(b,barrier,'shl_u128',1,[at('V.var128',0,16)],[at('V.rad128',0,16)],{'shift':40})
    kernel(b,barrier,'isqrt_u128',1,[at('V.rad128',0,16)],[at('V.den64',0,8)])
    b.macro('norm.complete_reduction_barrier',barrier,meta(token,'norm',group=1536,U128_stats=True,integer_denominator_ready=True,all_previous_outputs_required=True))
    emit=[]
    kernel(b,emit,'mul_s32_s32',8,[at('ext.layer_output',token*6144,32,(32,)),at('const.next_gamma',0,32,(32,))],[at('V.p64',0,64)])
    kernel(b,emit,'shl_s64_s128',8,[at('V.p64',0,64)],[at('V.n128',0,128)],{'shift':12})
    kernel(b,emit,'div_rne_s128_u64_i32',8,[at('V.n128',0,128),at('V.den64',0,8)],[at('V.out32',0,32)],{'broadcast_denominator':True,'RNE':'symmetric nearest even','overflow':'reject'})
    b.transfer(emit,'V.out32','ext.nextnorm',32,0,token*6144,dst_index=(32,))
    all_emit=[];b.loop(all_emit,192,emit)
    b.macro('norm.full1536_emit',all_emit,meta(token,'norm',elements=1536,source='ext.layer_output',actual_next_gamma=True,no_cross_token_batch=True))
    b.macro('norm.publish_after_complete_consumer',[],meta(token,'norm',complete_nextnorm=True,next_token_may_reuse_all_scratch=True))



def descriptor(path):return {'bytes':Path(path).stat().st_size,'sha256':sha(path)}


def verify_receipt(receipt,result,compiled,layer):
    r=load(receipt)
    if (r.get('schema'),r.get('status'),r.get('layer'),r.get('router_bits'),r.get('split'),r.get('tokens'),r.get('complete_selected_paths'))!=('granite-independent-receipt74-v1','PASS',layer,16,'evaluation',72,576):
        raise ValueError('requires original full R16/evaluation math receipt')
    if r.get('integer_stages_checked')!=43 or r.get('negative_status')!='PASS_ACTUAL_SHA_REWRITE' or len(r.get('negative_tests',[]))!=3:
        raise ValueError('complete stages and actual numeric negatives required')
    if r['producer_manifest']!=descriptor(result/'manifest.json') or r['compiled_manifest']!=descriptor(compiled/'manifest.json'):
        raise ValueError('numeric receipt actual source binding')
    return r


def prepare(args):
    cm=bound(args.compiled,'granite-moe-compiled74-v1','COMPILED_NOT_EXECUTED')
    nm=bound(args.result,'granite-moe-run74-v1','EXECUTED_COMPLETE');report=load(args.result/'report.json');layer=report['layer']
    if layer not in (0,13) or (report['router_bits'],report['split'],report['tokens'])!=(16,'evaluation',72):raise ValueError('frozen two evaluation sources')
    if cm['model_revision']!=REVISION or nm['model_revision']!=REVISION or nm['compiled_manifest_sha256']!=sha(args.compiled/'manifest.json'):raise ValueError('numeric compiled/revision')
    nr=verify_receipt(args.receipt,args.result,args.compiled,layer)
    pm=bound(args.packed,'granite-packed76-v1','PACKED_NOT_EXECUTED');pr=load(args.packed_receipt)
    if pm['layer']!=layer or pm['compiled_manifest_sha256']!=sha(args.compiled/'manifest.json') or pr.get('status')!='PASS_PACK_CODES' or pr.get('schema')!='granite-packed-independent76-v1' or pr['producer_manifest']!=descriptor(args.packed/'manifest.json') or pr['compiled_manifest']!=descriptor(args.compiled/'manifest.json'):
        raise ValueError('actual independent full40 static pack qualification')
    layout=load(args.packed/'layout.json')
    if layout['total_deployed_weight_bytes']!=94371840 or layout['perlayer_scale_bytes']!=614400:raise ValueError('complete packed storage')
    with np.load(args.packed/'packed.npz',allow_pickle=False) as packed:
        for rec in layout['arrays']:
            a=packed[rec['which']+'_w8']
            if array_sha(a)!=rec['packed_array_sha256'] or list(a.shape)!=rec['packed_shape']:raise ValueError('packed code/layout SHA')
    mm=bound(args.calibration,'micro-calibration-run76-v1','PASS_BYTE_CORE_AND_WIDE_MICROPROGRAM');cal=load(args.calibration/'cost_table.json');mr=load(args.calibration_receipt)
    if cal['schema']!='micro-cost-table76-v1' or cal['source']!=mm['source'] or mr.get('status')!='PASS_MICRO_CAUSAL_BYTE_AND_ROM' or mr.get('service_all_keys_qualified') is not True or mr.get('typed_keys')!=18 or mr['producer_manifest']!=descriptor(args.calibration/'manifest.json') or mr['cost_table']!=descriptor(args.calibration/'cost_table.json'):
        raise ValueError('requires independent qualified18 byte/micro/ROM receipt')
    inv=cal['inventory']
    if inv['VR8_lanes']!=8 or inv['SFU_count']!=1 or inv['SFU_uses_VR8_lane0'] is not True or inv['scalar_frame_bytes']!=512 or inv['operand_register_bytes_per_active_lane']!=5 or inv['VR8_operand_register_total_bytes']!=40:
        raise ValueError('same shared VR8/SFU finite storage')
    if inv['ROM']!={'II_cycles':1,'capacity_bytes':131072,'depth_words':32768,'latency_cycles':2,'ports':1,'word_bits':32}:
        raise ValueError('actual qualified ROM32 latency2 II1 geometry')
    with np.load(args.result/'runtime.npz',allow_pickle=False) as source:trace={k:source[k] for k in source.files}
    if any(a.dtype.kind not in 'iu' for a in trace.values()) or trace['norm_q12'].shape!=(72,1536) or trace['expert_mid_q12'].shape!=(72,8,512) or trace['down_q12'].shape!=(72,8,1536):raise ValueError('complete original integer arrays')
    if report['nonlinear_counts'].get('silu_negative_asymptote',0) or report['nonlinear_counts'].get('silu_positive_identity',0) or np.any(np.abs(trace['expert_gate_q12'].astype(np.int64))>(32<<12)):
        raise ValueError('current frozen two cases require all SiLU within qualified table domain; no hidden branch')
    for key in ('expert_input_delta','mid_delta'):
        if np.any(trace[key]<0) or np.any(trace[key]>128):raise ValueError('qualified scalar shift domain')
    const={}
    with np.load(args.compiled/'constants.npz',allow_pickle=False) as source:
        for key in ('gate_up_mant_q31','gate_up_exp','down_mant_q31','down_exp','next_gamma_q20'):
            const[key]=source['L%d.%s'%(layer,key)]
        const['multiplier']=source['residual_multiplier_q20'];const['silu']=source['silu_lut_q12'];const['exp2']=source['route_exp2_q24']
    if int(const['multiplier'])!=230687 or const['silu'].nbytes!=65540 or const['exp2'].nbytes!=8196:raise ValueError('frozen scalar/LUT formats')
    if np.any(trace['router.ids']>=40):raise ValueError('actual expert ID range')
    decoder=rq_decoder_evidence(trace,const)
    decoder['source']={'layer':layer,'numeric_manifest_sha256':sha(args.result/'manifest.json'),
        'compiled_manifest_sha256':sha(args.compiled/'manifest.json'),'numeric_receipt_sha256':sha(args.receipt)}
    rows={'schema':'granite-service-rowhashes76-v1','layer':layer,'source_manifest_sha256':sha(args.result/'manifest.json'),'stages':{}}
    for key,a in sorted(trace.items()):
        axis=0 if a.ndim and a.shape[0]==72 else 1 if a.ndim>1 and a.shape[1]==72 else None
        rows['stages'][key]={'dtype':str(a.dtype),'shape':list(a.shape),'array_sha256':array_sha(a),'token_axis':axis,
            'token_rows_sha256':[array_sha(np.take(a,t,axis=axis)) for t in range(72)] if axis is not None else []}
    trajectory=hashlib.sha256(json.dumps(rows,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    task={'layer':layer,'router_bits':16,'split':'evaluation','tokens':72,'complete_paths':576,'model_revision':REVISION,
        'numeric_manifest_sha256':sha(args.result/'manifest.json'),'compiled_manifest_sha256':sha(args.compiled/'manifest.json'),
        'numeric_receipt_sha256':sha(args.receipt),'packed_manifest_sha256':sha(args.packed/'manifest.json'),'packed_receipt_sha256':sha(args.packed_receipt),
        'calibration_manifest_sha256':sha(args.calibration/'manifest.json'),'calibration_cost_table_sha256':sha(args.calibration/'cost_table.json'),'calibration_receipt_sha256':sha(args.calibration_receipt),
        'numeric_trajectory_sha256':trajectory,'source_bound_numeric_status':'PASS','source_bound_micro_status':'PASS','rq_decoder_fee_version':RQ_DECODER_FEE_VERSION,
        'numeric_source':nm['source'],'packed_source':pm['source'],'calibration_source':mm['source'],
        'actual_expert_ids':trace['router.ids'].tolist(),'expert_input_delta':trace['expert_input_delta'].tolist(),'mid_delta':trace['mid_delta'].tolist(),
        'external_cut':'current norm/router already published; postnorm/router computation excluded, all consumed cut IO included',
        'reference_errors_preserved':report['reference_errors'],'original_issue70_status':'FAIL'}
    return task,trace,const,cal,rows,decoder


def deployment_bytes(b,const):
    scalars=bytearray(96)
    for off,value,width,signed in ((0,230687,4,True),(16,17,16,False),(32,1536,16,False),(48,31,8,True),(56,127,8,True),(64,128,8,True),(72,8192,8,True),(80,-131072,8,True),(88,131072,8,True)):
        scalars[off:off+width]=int(value).to_bytes(width,'little',signed=signed)
    desc=bytearray(40*64)
    for expert in range(40):
        pointers=[b.alloc['const.gate_up_w8']['offset']+expert*1024*1536,b.alloc['const.down_w8']['offset']+expert*1536*512,
            b.alloc['const.gate_up_mant']['offset']+expert*1024*4,b.alloc['const.gate_up_exp']['offset']+expert*1024*2,
            b.alloc['const.down_mant']['offset']+expert*1536*4,b.alloc['const.down_exp']['offset']+expert*1536*2,1024,1536]
        desc[expert*64:(expert+1)*64]=b''.join(v.to_bytes(8,'little') for v in pointers)
    return bytes(scalars),bytes(desc)


def run_service(args):
    out=Path(args.out)
    if out.exists():raise ValueError('refuse overwrite')
    binding=bind(args.binding);out.mkdir(parents=True);started=time.monotonic()
    manifest={'schema':'granite-service-run76-v1','status':'ERROR','source':binding,'producer_sha256':sha(__file__),'artifacts':[]}
    try:
        task,trace,const,cal,rows,decoder=prepare(args);owner='M' if args.placement=='near_m' else 'V'
        b=Builder(args.tile,owner,cal);capacity=allocate(b)
        b.inventory['calibrated_byte_core']=cal['inventory'];b.inventory['VR8_operand_register_total_bytes']=40
        b.inventory['ROM'].update(active_payload_bytes=73736,physical_reserved_bytes=131072,global_pool_bytes=4260100)
        b.inventory['micro_controller_level']=cal['level'];b.inventory['micro_source']=cal['source']
        b.inventory['controller_dispatch']='one candidate software dispatch slot per byte action; complete wide/address FSM not RTL implemented'
        b.inventory['RQ_shift_decoder']={'raw':'31-exponent_I16-current_delta_I16','guard':'cmp_s64 then explicit flags IO and one candidate controller test slot per output',
            'decoded':'128-max(128-raw,0)','typed_ops_per_output':['cmp_s64','sub_s64','max_s64','sub_s64'],'constant128':'const.scalars+64 S64 inside existing96B',
            'negative_shift':'fault, requires a separate explicit left-shift/overflow profile','equivalence':'signed S64 RNE(s>=64)=0 including I64_MIN/s64 tie-to-even'}
        for t in range(72):front(b,t,trace);downstream(b,t,trace);nextnorm(b,t)
        put(out/'row_hashes.json',rows);task['row_hashes_sha256']=sha(out/'row_hashes.json')
        put(out/'rq_decoder.json',decoder);task['rq_decoder_sha256']=sha(out/'rq_decoder.json')
        scalars,dispatch=deployment_bytes(b,const);(out/'deployed_scalars.bin').write_bytes(scalars);(out/'expert_dispatch.bin').write_bytes(dispatch);(out/'zero16.bin').write_bytes(bytes(16))
        static={'schema':'granite-service-deployment76-v1','packed_codes_deployment_bytes':94371840,'static_scale_bytes':614400,
            'scale_arrays':{k:{'dtype':str(a.dtype),'shape':list(a.shape),'bytes':a.nbytes,'array_sha256':array_sha(a)} for k,a in const.items() if k not in ('silu','exp2')},
            'ROM':{'active_bytes':73736,'physical_reserved_bytes':131072,'unused_padding_bytes':57336,'capacity_pool_bytes':4260100,
                'SiLU_array_sha256':array_sha(const['silu']),'exp2_array_sha256':array_sha(const['exp2'])},
            'static_zero16':descriptor(out/'zero16.bin'),'deployed_scalars':descriptor(out/'deployed_scalars.bin'),'expert_dispatch':descriptor(out/'expert_dispatch.bin'),
            'original_raw_weights':'scientific provenance only; not deployed simultaneously with packed codes',
            'compiler_constants_and_external_cut':'already present at allocated EXT/ROM addresses at task entry; one-time load not charged as repeated per-token inference',
            'offline_pack':'original pack phase elapsed/source/artifacts independently bound, not free online transpose'}
        put(out/'deployment.json',static)
        with (out/'witness.jsonl.gz').open('xb') as raw:
            with gzip.GzipFile(fileobj=raw,mode='wb',mtime=0,compresslevel=3) as stream:
                for event in b.events:stream.write((json.dumps(event,sort_keys=True,separators=(',',':'))+'\n').encode())
        summary={'schema':'granite-service76-v1','task':task,'config':{'tile':args.tile,'placement':args.placement,'label':args.label,
                'policy':'packed-weight serialized B1/scalar-byte microprogram service, no prefill batching'},
            'inventory':b.inventory,'allocations':list(b.alloc.values()),'used_bytes':dict(b.used),'phase_peak_bytes':capacity['phase_peak_bytes'],
            'counts':dict(b.counts),'end_slot':b.clock,'events':len(b.events),'capacity':capacity,'unknown_fees':[],
            'qualification':'CONDITIONAL_MICROPROGRAM_SERVICE_NOT_FULL_RTL_OR_PPA','math_trajectory_unchanged':True,
            'limits':['Full cut from published currentnorm/router to complete nextnorm, not whole model E2E/cached-decode timing or application quality',
                'All wide primitive byte ALU operations independently RTL-replayed, address/controller and scalar frame are software not complete wide FSM/STA/PPA',
                'Scalar microprogram uses dependency+candidate dispatch+finite byte-frame bank/BUS IO, no unconditional division by8',
                'M B1 uses16 effective PEs; static exact pack permits one16B weight beat perK, all pertoken transfers included',
                'M/V change is residency on same BUS-attached VR8, not extra near-M ALU or physical wire-locality proof',
                'Logical tile1536 has full S64 accumulator but O16 physical RQ returns; never materializes all8 S32 returns in V',
                'All policies conservative serial; target service slots are conditional, no optimality or real clock/PPA claim'],
            'environment':{'python':platform.python_version(),'numpy':np.__version__}}
        put(out/'summary.json',summary);manifest['status']='EXECUTED_CONDITIONAL_SERVICE'
    except Exception as exc:
        manifest['error']={'type':type(exc).__name__,'message':str(exc),'traceback':traceback.format_exc()};raise
    finally:manifest['elapsed_seconds']=time.monotonic()-started;seal(out,manifest)


def main():
    p=argparse.ArgumentParser(__doc__);sub=p.add_subparsers(dest='command',required=True)
    q=sub.add_parser('pack');q.add_argument('--compiled',type=Path,required=True);q.add_argument('--layer',type=int,choices=(0,13),required=True)
    q.add_argument('--binding',type=Path,required=True);q.add_argument('--out',type=Path,required=True)
    r=sub.add_parser('run')
    for key in ('compiled','result','receipt','packed','packed-receipt','calibration','calibration-receipt','binding','out'):r.add_argument('--'+key,type=Path,required=True)
    r.add_argument('--tile',type=int,choices=(128,256,1536),required=True)
    r.add_argument('--placement',choices=('near_m','shared_v'),required=True);r.add_argument('--label',choices=('split','shared'),required=True)
    args=p.parse_args();run_pack(args) if args.command=='pack' else run_service(args)


if __name__=='__main__':main()
