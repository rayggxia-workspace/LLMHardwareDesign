"""Issue72 finite-resource complete Falcon R-chain service calendar.

Serialized single-token policy, conditional slots only: not RTL or model speed.
No numerical producer is imported. Requires an independent PASS receipt.
"""
import argparse
from collections import Counter
import gzip
import hashlib
import io
import json
from pathlib import Path
import platform
import sys
import time
import traceback
import numpy as np

KIB=1024
MIB=1024*1024
VARIANTS={'r32_d8':('R',8,False),'v16_d2':('V',2,False),'r32_d16_spill':('R',16,True)}
# Explicit bytewise candidate costs; no native wide ALU is gifted.
BYTE_COST={'mul32':25+24*10,'add64':10,'rne64':10,'abs64':10,'compare64':10,
    'reduce_flag':1,'normadd128':18,'copy_byte':1,'scalar_control':10,'cast_i32_guard':20}


def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(8<<20),b''):h.update(b)
    return h.hexdigest()


def put(p,o):
    Path(p).write_text(json.dumps(o,sort_keys=True,indent=2,allow_nan=False,default=str)+'\n',encoding='utf-8',newline='\n')


def load(p):return json.loads(Path(p).read_text())


def bound(directory):
    directory=Path(directory);m=load(directory/'manifest.json')
    for a in m['artifacts']:
        p=directory/a['path']
        if p.stat().st_size!=a['bytes'] or sha(p)!=a['sha256']:raise ValueError('artifact SHA/size '+str(p))
    return m


def beats(offset,length):
    if offset<0 or length<0:raise ValueError('negative access')
    return ((offset%16+length+15)//16) if length else 0


def packet_cost(src,dst,length,maxpayload=1984):
    """Every packet is a distinct physical access, including leading offsets."""
    total={'src_beats':0,'dst_beats':0,'wire_beats':0,'packets':0,'wire_bytes':0,'payload_bytes':length}
    done=0
    while done<length:
        n=min(maxpayload,length-done)
        total['src_beats']+=beats(src+done,n);total['dst_beats']+=beats(dst+done,n)
        wire=32+((n+15)//16)*16
        total['wire_bytes']+=wire;total['wire_beats']+=wire//16;total['packets']+=1;done+=n
    return total


class Builder:
    def __init__(self,placement,wide_factor=1):
        self.bank,self.dpage,self.spill=VARIANTS[placement]
        self.placement=placement;self.wide_factor=wide_factor
        self.cap={'V':16*KIB,'R':32*KIB,'M':32*KIB,**{'S'+str(i):32*KIB for i in range(8)},'EXT':128*MIB,'ROM':4260100}
        self.used=Counter();self.alloc={};self.events=[];self.clock=0;self.totals=Counter()
        self.inventory={'capacities':self.cap,'ports':{k:{'kind':'1RW','bits':128} for k in self.cap},
            'matrix':{'resource':'M256','S8_PEs':256,'shape':[16,16],'effective_PEs_single_row':16},
            'lanes':{'resource':'VR8','S8_lanes':8},'alu_slots64':10,'alu_slots128':18,
            'SFUiterations':{'division128':128,'isqrt128':64},'LUTport':{'resource':'bank.ROM','bits':128,'one_access_per_lookup':True},
            'packet':{'header_bytes':32,'beat_bytes':16,'max_payload':1984,'FIFO_bytes':2048,'BUS_count':1,'BUS_bits':128},
            'byte_cost':BYTE_COST,'wide_factor':wide_factor,
            'policy':'strict serialized single token; prefill64 and decode8 never batched; no optimality or RTL claim'}
        self.add('local.Vaux','V',8192)
        if self.bank=='R':self.add('local.Raux','R',8192)
        self.aux='local.'+self.bank+'aux'
        self.add('local.old',self.bank,self.dpage*256*4) # reserve S32 even for S16, no extra precision-dependent resource
        if self.spill:self.add('local.wide','S0',self.dpage*256*8)
        else:self.add('local.wide',self.bank,self.dpage*256*8)
        self.add('local.m_a','M',4096);self.add('local.m_wrow','M',8192);self.add('local.m_wcol','M',8192)
        self.add('local.m_regs','M',512);self.add('local.m_acc','M',64);self.add('local.m_meta','M',256);self.add('local.m_out','M',64)

    def add(self,name,bank,n):
        if name in self.alloc:raise ValueError('duplicate object '+name)
        alignment=4 if bank=='ROM' else 16
        offset=((self.used[bank]+alignment-1)//alignment)*alignment
        if offset+n>self.cap[bank]:raise ValueError('capacity '+bank+' '+name)
        self.alloc[name]={'object':name,'bank':bank,'offset':offset,'bytes':int(n),'lifetime':['task_start','task_end']}
        self.used[bank]=offset+n
        return name

    def access(self,obj,offset,n,mode='read',repeat=1,stride=0,index_strides=()):
        a=self.alloc[obj]
        if min(offset,n,repeat,stride)<0 or offset+n+(repeat-1)*stride>a['bytes']:raise ValueError('access outside '+obj)
        return {'object':obj,'offset':int(offset),'bytes':int(n),'mode':mode,'repeat':int(repeat),'stride':int(stride),
            'index_strides':list(map(int,index_strides))}

    def leaf(self,body,kind,resources,**kw):
        start=body[-1]['end'] if body else 0
        rr=[];cursor=start
        for name,duration in resources:
            duration=int(duration)
            if duration:
                rr.append({'name':name,'start':cursor,'end':cursor+duration});cursor+=duration
        event={'kind':kind,'start':start,'end':cursor,'resources':rr,**kw};body.append(event)
        return event

    def memory(self,body,accesses):
        rr=[];total=0
        for x in accesses:
            a=self.alloc[x['object']]
            n=sum(beats(a['offset']+x['offset']+i*x['stride'],x['bytes']) for i in range(x['repeat']))
            rr.append(('bank.'+a['bank'],n));total+=n
        return self.leaf(body,'access',rr,accesses=accesses,counts={'local_beats':total})

    def transfer(self,body,src,dst,n,so=0,do=0,segments=1,ss=0,ds=0,src_index=(),dst_index=()):
        sa,da=self.alloc[src],self.alloc[dst]
        accesses=[self.access(src,so,n,'read',segments,ss,src_index),self.access(dst,do,n,'write',segments,ds,dst_index)]
        count=Counter()
        for i in range(segments):count.update(packet_cost(sa['offset']+so+i*ss,da['offset']+do+i*ds,n))
        return self.leaf(body,'transfer',[('bank.'+sa['bank'],count['src_beats']),('BUS',count['wire_beats']),('bank.'+da['bank'],count['dst_beats'])],
            accesses=accesses,counts=dict(count),FIFO_peak_bytes=32+16*((min(1984,n)+15)//16),
            packet={'src':src,'dst':dst,'src_offset':so,'dst_offset':do,'bytes':n,'segments':segments,'src_stride':ss,'dst_stride':ds})

    def compute(self,body,counts,matrix_active=16):
        count={k:int(v) for k,v in counts.items() if int(v)}
        if set(count)-set(BYTE_COST)-{'matrix_mac','division_iterations','isqrt_iterations'}:raise ValueError('unknown primitive '+str(count))
        normal=sum(v*BYTE_COST[k] for k,v in count.items() if k in BYTE_COST)
        normal*=self.wide_factor
        rr=[]
        if count.get('matrix_mac'):rr.append(('M256',(count['matrix_mac']+matrix_active-1)//matrix_active))
        if normal:rr.append(('VR8',(normal+7)//8))
        if count.get('division_iterations'):rr.append(('SFU',count['division_iterations']))
        if count.get('isqrt_iterations'):rr.append(('SFU',count['isqrt_iterations']))
        return self.leaf(body,'compute',rr,counts=count,matrix_active_PEs=matrix_active)

    def lookup(self,body,lut,n,bank='V',source_offset=0,out_offset=4096):
        """One request/reply per lookup, serialized FIFO<=48B.

        Actual index is an integer-runtime operand. Any aligned4B LUT element
        consumes exactly one 128bit ROM access; address-invariant cost certificate.
        """
        inner=[]
        aa='local.'+bank+'aux'
        self.leaf(inner,'lookup',[('bank.'+bank,1),('BUS',3),('bank.ROM',1),('SFU',1),('BUS',3),('bank.'+bank,1)],
            accesses=[self.access(aa,source_offset,4,'read',index_strides=(4,)),
                {'object':lut,'offset':0,'bytes':4,'mode':'read','repeat':1,'stride':0,'index_strides':[0],
                    'address_class':{'kind':'integer_runtime_index','alignment':4,'minimum':0,'maximum':self.alloc[lut]['bytes']-4,'beat_invariant':1}},
                self.access(aa,out_offset,4,'write',index_strides=(4,))],
            counts={'lut_reads':1,'payload_bytes':8,'wire_bytes':96,'wire_beats':6,'packets':2,'src_beats':1,'dst_beats':1},FIFO_peak_bytes=48)
        self.loop(body,n,inner)

    def loop(self,body,count,inner):
        start=body[-1]['end'] if body else 0;period=inner[-1]['end'] if inner else 0
        node={'kind':'loop','start':start,'end':start+int(count)*period,'count':int(count),'period':period,'body':inner}
        body.append(node);return node

    def macro(self,stage,body,meta=None,token=None):
        n=len(self.events);duration=body[-1]['end'] if body else 0
        event={'id':n,'stage':stage,'start':self.clock,'end':self.clock+duration,'deps':[n-1] if n else [],
            'token':token,'phase':'prefill' if token is not None and token<64 else 'decode' if token is not None else 'setup',
            'meta':meta or {},'body':body}
        self.events.append(event);self.clock+=duration
        self.count_tree(body,1)
        return n

    def count_tree(self,nodes,mult):
        for n in nodes:
            if n['kind']=='loop':self.count_tree(n['body'],mult*n['count'])
            else:
                for k,v in n.get('counts',{}).items():self.totals[k]+=v*mult

    def stream(self,stage,n,reads,writes,counts,token,bank='V',lut=None):
        """512-value I32 chunks; aux input/gamma/output slots at0/2048/4096."""
        main=[]
        def make(size,base_index):
            body=[];aux='local.'+bank+'aux'
            for idx,(obj,off) in enumerate(reads):
                self.transfer(body,obj,aux,size*4,off,idx*2048,src_index=base_index)
            c={k:v(size) if callable(v) else v for k,v in counts.items()}
            self.memory(body,[self.access(aux,idx*2048,size*4) for idx in range(len(reads))])
            if 'division_iterations' in c:self.memory(body,[self.access(aux,6384,16)])
            if lut:
                c['rne64']=c.get('rne64',0)+size
                c['compare64']=c.get('compare64',0)+2*size
            self.compute(body,c)
            if lut:self.lookup(body,lut,size,bank)
            else:self.memory(body,[self.access(aux,4096,size*4,'write')])
            for idx,(obj,off) in enumerate(writes):
                self.transfer(body,aux,obj,size*4,4096,off,dst_index=base_index)
            return body
        full,tail=divmod(n,512)
        if full:self.loop(main,full,make(512,(2048,)))
        if tail:
            body=make(tail,())
            for leaf in body:
                if leaf['kind']=='transfer':
                    for a in leaf['accesses']:
                        if a['object'].startswith('ext.') or a['object'].startswith('const.'):
                            a['offset']+=full*2048
                    # Packet address shift is a 16B multiple: all physical beats remain invariant.
                    p=leaf['packet']
                    if p['src'].startswith(('ext.','const.')):p['src_offset']+=full*2048
                    if p['dst'].startswith(('ext.','const.')):p['dst_offset']+=full*2048
            # Stitch relative offsets into the surrounding body.
            shift=main[-1]['end'] if main else 0
            self.shift_nodes(body,shift);main.extend(body)
        self.macro(stage,main,{'elements':n,'chunk':512,'bank':bank},token)

    @staticmethod
    def shift_nodes(nodes,amount):
        for n in nodes:
            n['start']+=amount;n['end']+=amount
            for r in n.get('resources',[]):r['start']+=amount;r['end']+=amount

    def norm(self,stage,n,source,gamma,dest,token):
        # Full-group U128 partials and denominator have explicit memory locations.
        reduce=[];tiles=(n+511)//512
        for start in range(0,n,512):
            size=min(512,n-start)
            self.transfer(reduce,source,'local.Vaux',size*4,start*4,0)
            self.memory(reduce,[self.access('local.Vaux',0,size*4)])
            self.compute(reduce,{'mul32':size,'normadd128':size-1})
            self.memory(reduce,[self.access('local.Vaux',6144,16,'write')])
            self.transfer(reduce,'local.Vaux','ext.norm_partials',16,6144,(start//512)*16)
        self.macro(stage+'.reduce',reduce,{'elements':n,'chunk':512,'U128_partials':tiles},token)
        barrier=[]
        self.transfer(barrier,'ext.norm_partials','local.Vaux',tiles*16,0,6144)
        self.memory(barrier,[self.access('local.Vaux',6144,tiles*16)])
        self.compute(barrier,{'normadd128':tiles-1+1,'scalar_control':2,'division_iterations':128,'isqrt_iterations':64})
        self.memory(barrier,[self.access('local.Vaux',6384,16,'write')])
        self.macro(stage+'.full_group_barrier',barrier,{'group':n,'complete_reduction':True,'epsilon_add128':1,'radicand_shift':40,'denominator_aux_offset':6384},token)
        self.stream(stage+'.emit',n,[(source,0),(gamma,0)],[(dest,0)],
            {'mul32':lambda s:s,'division_iterations':lambda s:s*128,'cast_i32_guard':lambda s:s},token)

    def dynamic(self,which,n,source,dest,delta,token):
        self.stream(which+'.A8_absmax',n,[(source,0)],[],{'abs64':lambda s:s,'compare64':lambda s:s},token)
        body=[];self.compute(body,{'rne64':int(delta)+1,'scalar_control':int(delta)+1})
        self.macro(which+'.A8_minimal_shift',body,{'K':n,'delta':int(delta),'lowering':'RNE is monotone in abs(input); max once then scalar RNE shift search'},token)
        main=[]
        # I32 source -> A8 destination, use exact byte quantities; no float scale.
        for start in range(0,n,512):
            size=min(512,n-start);self.transfer(main,source,'local.Vaux',size*4,start*4,0)
            self.memory(main,[self.access('local.Vaux',0,size*4)])
            self.compute(main,{'rne64':size,'cast_i32_guard':size})
            self.memory(main,[self.access('local.Vaux',4096,size,'write')])
            self.transfer(main,'local.Vaux',dest,size,4096,start)
        self.macro(which+'.A8_encode',main,{'K':n,'delta':int(delta),'integer_only':True},token)

    def matrix(self,which,O,K,weight,scale,bias,input_a,output,token):
        if O%16 or K%512:raise ValueError('frozen matrix tiling requires O16/K512 divisibility')
        outer=[]
        self.transfer(outer,input_a,'local.m_a',K)
        tiles=[];inner=[]
        # Packed row-major tile then explicit transpose into K-major 16-column stream.
        self.transfer(inner,weight,'local.m_wrow',512,segments=16,ss=K,ds=512,src_index=(16*K,512),dst_index=(0,0))
        transpose=[]
        self.memory(transpose,[self.access('local.m_wrow',0,16,repeat=16,stride=512,index_strides=(16,)),
            self.access('local.m_regs',0,256,'write')])
        self.memory(transpose,[self.access('local.m_regs',0,256)])
        self.compute(transpose,{'copy_byte':256})
        self.memory(transpose,[self.access('local.m_wcol',0,256,'write',index_strides=(256,))])
        self.loop(inner,32,transpose)
        self.memory(inner,[self.access('local.m_acc',0,64)])
        k16=[]
        self.memory(k16,[self.access('local.m_a',0,16,index_strides=(0,512,16))])
        k1=[]
        self.memory(k1,[self.access('local.m_wcol',0,16,index_strides=(256,16))])
        self.compute(k1,{'matrix_mac':16},16)
        self.loop(k16,16,k1);self.loop(inner,32,k16)
        self.memory(inner,[self.access('local.m_acc',0,64,'write')])
        self.memory(tiles,[self.access('local.m_acc',0,64,'write')])
        self.loop(tiles,K//512,inner)
        # Source stride axes here: Otiles is outermost, Ktiles innermost.
        self.transfer(tiles,scale[0],'local.m_meta',16*4,0,0,src_index=(16*4,))
        self.transfer(tiles,scale[1],'local.m_meta',16*2,0,64,src_index=(16*2,))
        self.transfer(tiles,bias,'local.m_meta',16*4,0,128,src_index=(16*4,))
        self.memory(tiles,[self.access('local.m_acc',0,64),self.access('local.m_meta',0,96),self.access('local.m_meta',128,64)])
        self.compute(tiles,{'mul32':16,'rne64':16,'add64':16,'cast_i32_guard':16})
        self.memory(tiles,[self.access('local.m_out',0,64,'write')])
        self.transfer(tiles,'local.m_out',output,64,dst_index=(64,))
        self.loop(outer,O//16,tiles)
        self.macro(which+'.matrix_fullK_RQ',outer,{'which':which,'O':O,'K':K,'Otile':16,'Ktile':512,'Trow':1,
            'real_Otilelast':16,'effective_matrix_PEs':16,'complete_K_before_RQ':True,'transpose_byte_copy_charged':True},token)


    def eltwise(self,stage,n,source,dest,token,mul=False,constant=None,other=None,add=False,lut=None):
        if constant:
            b=[];self.transfer(b,constant,'local.Vaux',4,0,6144);self.memory(b,[self.access('local.Vaux',6144,4)])
            self.macro(stage+'.constant',b,{'constant':constant,'format':'I32Q20'},token)
        reads=[(source,0)]+([(other,0)] if other else [])
        c={}
        if mul:c.update(mul32=lambda s:s,rne64=lambda s:s)
        if add:c['add64']=lambda s:s
        c['cast_i32_guard']=lambda s:s
        self.stream(stage,n,reads,[(dest,0)],c,token,lut=lut)

    def conv(self,token):
        main=[];body=[];aux=self.aux;bank=self.bank
        # 128 channels per tile, 4 history samples, retained across tokens in EXT.
        for obj,off,n,slot,stride in [(self.hist_trial,0,2048,0,2048),('const.conv_weight_q20',0,2048,2048,2048),
            ('ext.projected',4096*4,512,4096,512),('const.conv_bias_q12',0,512,6144,512)]:
            self.transfer(body,obj,aux,n,off,slot,src_index=(stride,))
        self.memory(body,[self.access(aux,0,2048),self.access(aux,4096,512)])
        self.compute(body,{'copy_byte':1536})
        self.memory(body,[self.access(aux,0,2048,'write')])
        self.memory(body,[self.access(aux,0,2048),self.access(aux,2048,2048),self.access(aux,6144,512)])
        self.compute(body,{'mul32':128*4,'add64':128*4,'rne64':256,'compare64':256,'cast_i32_guard':128})
        self.transfer(body,aux,self.hist_trial,2048,0,0,dst_index=(2048,))
        self.memory(body,[self.access(aux,5120,512,'write')])
        self.lookup(body,'const.silu_lut_q12',128,bank,5120,4096)
        self.transfer(body,aux,'ext.conv',512,4096,0,dst_index=(512,))
        self.loop(main,36,body)
        self.macro('conv4_continuous_silu',main,{'channels':4608,'taps':4,'channel_tile':128,'bank':bank,'history_persists':True},token)
        body=[]
        self.transfer(body,'ext.projected',aux,128,(8192+512)*4,0)
        self.transfer(body,'const.dt_bias_q12',aux,128,0,2048)
        self.compute(body,{'add64':32,'rne64':32,'compare64':64,'cast_i32_guard':32})
        self.lookup(body,'const.dt_lut_q20',32,bank,0,4096)
        self.transfer(body,aux,'ext.dt',128,4096,0)
        self.lookup(body,'const.alpha_lut_q31',32,bank,0,4096)
        self.transfer(body,aux,'ext.alpha',128,4096,0)
        self.macro('dt_alpha',body,{'heads':32,'B_C_group_count':1},token)

    def terms(self,token,attempt,head,unit,epoch,bits,source_hash):
        D=self.dpage;N=256;b=bits//8;aux=self.aux;outer=[]
        self.transfer(outer,self.units_trial,aux,2,head*2,7936)
        self.transfer(outer,self.desc_trial,aux,16,0,7952)
        self.memory(outer,[self.access(aux,7936,2),self.access(aux,7952,16)])
        self.transfer(outer,'ext.dt',aux,4,head*4,0)
        self.transfer(outer,'ext.conv',aux,1024,4096*4,1024)
        # dtB20 is head-specific, recomputed once per attempt/head, fullN.
        term=[]
        self.memory(term,[self.access(aux,0,4),self.access(aux,1024,32,index_strides=(32,))])
        self.compute(term,{'mul32':8,'rne64':8,'cast_i32_guard':8})
        self.memory(term,[self.access(aux,2048,32,'write',index_strides=(32,))])
        self.loop(outer,32,term)
        page=[]
        self.transfer(page,'ext.trial','local.old',D*N*b,head*128*N*b,0,src_index=(D*N*b,))
        self.transfer(page,'ext.alpha',aux,4,head*4,0)
        self.transfer(page,'ext.conv',aux,D*4,head*128*4,4096,src_index=(D*4,))
        row=[];cell=[]
        self.memory(cell,[self.access('local.old',0,8*b,index_strides=(N*b,8*b)),self.access(aux,0,4),
            self.access(aux,2048,32,index_strides=(32,)),self.access(aux,4096,4,index_strides=(4,0))])
        self.compute(cell,{'mul32':16,'rne64':16})
        # 8 elements per lane step: <=64B outputs, never whole-page registers.
        self.memory(cell,[self.access(aux,6144,64,'write')])
        self.transfer(cell,aux,'ext.decay',64,6144,head*128*N*8,dst_index=(D*N*8,N*8,64))
        self.memory(cell,[self.access(aux,6144,64,'write')])
        self.transfer(cell,aux,'ext.injection',64,6144,head*128*N*8,dst_index=(D*N*8,N*8,64))
        self.loop(row,32,cell);self.loop(page,D,row);self.loop(outer,128//D,page)
        self.macro('state.terms',outer,{'head':head,'attempt':attempt,'unit':unit,'epoch':epoch,'Dpage':D,'N':N,'D':128,'bits':bits,
            'source_stage_hashes':source_hash,'integer_elements_per_register_step':8},token)

    def global_wide_guard(self,token,attempt):
        body=[];inner=[]
        self.transfer(inner,'ext.decay',self.aux,64,src_index=(64,))
        self.transfer(inner,'ext.injection',self.aux,64,0,256,src_index=(64,))
        self.memory(inner,[self.access(self.aux,0,64),self.access(self.aux,256,64),self.access(self.aux,7168,16)])
        self.compute(inner,{'abs64':16,'compare64':16})
        self.memory(inner,[self.access(self.aux,7168,16,'write')])
        self.memory(body,[self.access(self.aux,7168,16,'write')])
        self.loop(body,(32*128*256)//8,inner)
        self.compute(body,{'add64':1,'compare64':1})
        self.macro('state.full_I64_add_guard',body,{'attempt':attempt,'all_heads':32,'elements':32*128*256,'maxabs_decay_plus_maxabs_injection':True},token)

    def proposal(self,token,attempt,head,unit,epoch,bits,source_hash):
        D=self.dpage;N=256;aux=self.aux;body=[];page=[];cell=[]
        base=head*128*N*8
        self.transfer(cell,'ext.decay',aux,64,base,0,src_index=(D*N*8,64))
        self.transfer(cell,'ext.injection',aux,64,base,256,src_index=(D*N*8,64))
        self.memory(cell,[self.access(aux,0,64),self.access(aux,256,64)])
        self.compute(cell,{'add64':8})
        self.memory(cell,[self.access(aux,6144,64,'write')])
        self.transfer(cell,aux,'local.wide',64,6144,0,dst_index=(0,64))
        self.loop(page,D*N//8,cell)
        scan=[]
        self.transfer(scan,'local.wide',aux,64,0,0,src_index=(64,))
        self.memory(scan,[self.access(aux,0,64),self.access(aux,7200,4)])
        self.compute(scan,{'compare64':16,'reduce_flag':8})
        self.memory(scan,[self.access(aux,7200,4,'write')])
        self.loop(page,D*N//8,scan)
        self.transfer(page,'local.wide','ext.proposal',D*N*8,0,base,dst_index=(D*N*8,))
        self.memory(body,[self.access(aux,7200,4,'write')])
        self.loop(body,128//D,page)
        self.transfer(body,aux,'ext.guard_flags',4,7200,head*4)
        self.macro('state.proposal_guard_head',body,{'head':head,'attempt':attempt,'unit':unit,'epoch':epoch,'Dpage':D,'N':N,'D':128,
            'bits':bits,'I64_proposal':True,'spill_S0':self.spill,'source_stage_hashes':source_hash},token)

    def pre_readout(self,token,head,unit,epoch,bits):
        D=self.dpage;N=256;b=bits//8;aux=self.aux;body=[]
        self.transfer(body,'ext.conv',aux,N*4,(4096+256)*4,1024)
        page=[]
        self.transfer(page,'ext.proposal','local.wide',D*N*8,head*128*N*8,0,src_index=(D*N*8,))
        row=[];cell=[]
        self.transfer(cell,'local.wide',aux,64,0,0,src_index=(N*8,64))
        self.memory(cell,[self.access(aux,0,64),self.access(aux,1024,32,index_strides=(32,)),self.access(aux,7168,8)])
        self.compute(cell,{'cast_i32_guard':8,'mul32':8,'abs64':8,'compare64':8})
        self.memory(cell,[self.access(aux,6144,64,'write'),self.access(aux,7168,8,'write')])
        self.transfer(cell,aux,'ext.readout_product',64,6144,head*128*N*8,dst_index=(D*N*8,N*8,64))
        self.memory(cell,[self.access(aux,6400,8*b,'write')])
        self.transfer(cell,aux,self.state_next,8*b,6400,head*128*N*b,dst_index=(D*N*b,N*b,8*b))
        self.loop(row,32,cell);self.loop(page,D,row)
        self.memory(body,[self.access(aux,7168,8,'write')])
        self.loop(body,128//D,page)
        self.transfer(body,aux,'ext.readout_guardmax',8,7168,head*8)
        self.macro('state.readout_products_guard',body,{'head':head,'unit':unit,'epoch':epoch,'Dpage':D,'N':N,'bits':bits,
            'generic_unchecked_sum_requires_signed_bits':71,'actual_I64_maxproduct_guard':True},token)

    def readout(self,token,head,unit,epoch,bits):
        N=256;aux=self.aux;body=[];row=[];cell=[]
        self.memory(row,[self.access(aux,7168,8,'write')])
        self.transfer(cell,'ext.readout_product',aux,64,head*128*N*8,0,src_index=(N*8,64))
        self.memory(cell,[self.access(aux,0,64),self.access(aux,7168,8)])
        self.compute(cell,{'add64':8})
        self.memory(cell,[self.access(aux,7168,8,'write')])
        self.loop(row,32,cell)
        self.transfer(row,'ext.conv',aux,4,head*128*4,4096,src_index=(4,))
        self.transfer(row,'const.skip_q20',aux,4,head*4,5120)
        self.memory(row,[self.access(aux,4096,4),self.access(aux,5120,4),self.access(aux,7168,8)])
        self.compute(row,{'rne64':2,'mul32':1,'add64':1,'cast_i32_guard':1})
        self.memory(row,[self.access(aux,6144,4,'write')])
        self.transfer(row,aux,'ext.scan',4,6144,head*128*4,dst_index=(4,))
        self.loop(body,128,row)
        self.macro('state.readout_complete_N',body,{'head':head,'unit':unit,'epoch':epoch,'N':256,'D':128,'bits':bits,
            'complete_N_before_RNE':True,'allhead_product_guard_precedes':True},token)


def make_task(args):
    numeric=Path(args.numeric);compiled=Path(args.compiled)
    nm=bound(numeric);cm=bound(compiled);report=load(numeric/'report.json');tx=load(numeric/'transactions.json')
    receipt=load(args.receipt)
    if receipt.get('status')!='PASS' or receipt.get('mode')!='full' or receipt.get('policy')!='guard_rescale':raise ValueError('independent full guard PASS required')
    if report['mode']!='full' or report['policy']!='guard_rescale' or report['committed_tokens']!=report['input_tokens'] or report['published_state_saturations']!=0:raise ValueError('requires complete unsaturated full task')
    if receipt.get('producer_manifest',{}).get('sha256')!=sha(numeric/'manifest.json'):raise ValueError('receiver not bound to numeric manifest')
    if report['compiled_manifest_sha256']!=sha(compiled/'manifest.json'):raise ValueError('compiled source mismatch')
    runtime=np.load(numeric/'runtime.npz',allow_pickle=False)
    const=np.load(compiled/'constants.npz',allow_pickle=False)
    if report['input_tokens']!=72:raise ValueError('frozen B1 pre64/decode8 task')
    return nm,cm,report,tx,receipt,runtime,const


def build(args):
    nm,cm,r,tx,receipt,runtime,const=make_task(args)
    B=Builder(args.placement,args.wide_factor);T=72;H=2560;I=4096;E=32*128*256;b=r['state_bits']//8
    for name in sorted(const.files):
        a=const[name]
        B.add('const.'+name,'ROM' if 'lut' in name else 'EXT',a.nbytes)
    for name,n in {'cut_input':T*H*4,'cut_attention':T*H*4,'input':H*4,'attention':H*4,'norm':H*4,'mamba_input':H*4,
        'in_a8':H,'projected':8736*4,'conv':4608*4,'history':4608*4*4,'dt':128,'alpha':128,'state':E*b,'old':E*b,'trial':E*b,
        'proposal':E*8,'decay':E*8,'injection':E*8,'readout_product':E*8,'readout_guardmax':256,'guard_flags':128,'new':E*b,'scan':I*4,'gated':I*4,'gated_norm':I*4,'out_a8':I,'out':H*4,'mamba':H*4,
        'attention_scaled':H*4,'join1':H*4,'join':H*4,'nextnorm':H*4,'descriptor':16,'desc0':96,'desc1':96,'units0':64,'units1':64,'history_trial':4608*4*4,'norm_partials':128}.items():B.add('ext.'+name,'EXT',n)
    task={'numeric_manifest_sha256':sha(Path(args.numeric)/'manifest.json'),'compiled_manifest_sha256':sha(Path(args.compiled)/'manifest.json'),
        'receipt_sha256':sha(args.receipt),'runtime_sha256':sha(Path(args.numeric)/'runtime.npz'),
        'trajectory_sha256':sha(Path(args.numeric)/'transactions.json'),'mode':'full','bits':r['state_bits'],'policy':r['policy'],
        'precision':'complete captured integer task; external I32Q12 residual/A cuts','tokens':T,'calibration_tokens':16,
        'source':nm['source'],'compiled_source':cm['source'],'reference_errors':r['reference_errors']}
    setup=[]
    B.memory(setup,[B.access('ext.state',0,E*b,'write'),B.access('ext.history',0,4608*4*4,'write'),B.access('ext.descriptor',0,16,'write'),B.access('ext.desc0',0,96,'write')])
    B.compute(setup,{'copy_byte':E*b+4608*4*4+16+96})
    B.transfer(setup,'const.state_s%d_exponents'%r['state_bits'],'ext.units0',64)
    B.macro('setup_zero_state_history_units',setup,{'initial_state_zero':True,'history_zero':True,'constants_and_external_cuts_preloaded':True})
    for t,txn in enumerate(tx['tokens']):
        if not txn['committed']:raise ValueError('unexpected rejected token')
        B.state_pub='ext.state' if t%2==0 else 'ext.new'
        B.state_next='ext.new' if t%2==0 else 'ext.state'
        B.hist_pub='ext.history' if t%2==0 else 'ext.history_trial'
        B.hist_trial='ext.history_trial' if t%2==0 else 'ext.history'
        B.units_pub='ext.units0' if t%2==0 else 'ext.units1'
        B.units_trial='ext.units1' if t%2==0 else 'ext.units0'
        B.desc_pub='ext.desc0' if t%2==0 else 'ext.desc1'
        B.desc_trial='ext.desc1' if t%2==0 else 'ext.desc0'
        body=[];B.transfer(body,B.desc_pub,B.desc_trial,96)
        B.transfer(body,B.hist_pub,B.hist_trial,4608*4*4)
        B.transfer(body,B.units_pub,B.units_trial,64)
        B.macro('private_history_units_clone',body,{'published_history_preserved_until_consumer':True},t)
        body=[];B.transfer(body,'ext.cut_input','ext.input',H*4,t*H*4,0);B.transfer(body,'ext.cut_attention','ext.attention',H*4,t*H*4,0)
        B.macro('external_integer_cuts',body,{'external_attention_not_integer_closed':True},t)
        B.norm('input_norm',H,'ext.input','const.input_gamma_q20','ext.norm',t)
        B.eltwise('input_mup',H,'ext.norm','ext.mamba_input',t,mul=True,constant='const.ssm_in_multiplier_q20')
        B.dynamic('in',H,'ext.mamba_input','ext.in_a8',runtime['in_a8_delta'][t],t)
        B.matrix('in',8736,H,'const.in_weight_w8',('const.in_scale_q31','const.in_scale_exp'),'const.in_bias_q12','ext.in_a8','ext.projected',t)
        B.stream('projected_mup',8736,[('ext.projected',0),('const.mup_q20',0)],[('ext.projected',0)],
            {'mul32':lambda n:n,'rne64':lambda n:n,'cast_i32_guard':lambda n:n},t)
        B.conv(t)
        body=[];B.transfer(body,B.state_pub,'ext.old',E*b);B.transfer(body,'ext.old','ext.trial',E*b)
        B.macro('state.old_trial_clones',body,{'target_clone_generations':2,'observer_SHA_scans_charged':False},t)
        for attempt in txn['attempts']:
            for h in range(32):B.terms(t,attempt['attempt'],h,attempt['trial_units'][h],attempt['trial_epoch'],r['state_bits'],attempt.get('stage_hashes',{}))
            B.global_wide_guard(t,attempt['attempt'])
            for h in range(32):B.proposal(t,attempt['attempt'],h,attempt['trial_units'][h],attempt['trial_epoch'],r['state_bits'],attempt.get('stage_hashes',{}))
            body=[];B.transfer(body,'ext.guard_flags',B.aux,128,0,0);B.memory(body,[B.access(B.aux,0,128)])
            B.compute(body,{'reduce_flag':31,'scalar_control':32})
            B.macro('state.complete_group_guard_barrier',body,{'attempt':attempt['attempt'],'epoch':attempt['trial_epoch'],
                'result':attempt['result'],'published':False,'range_violations':attempt['range_violations'],'all_heads':32},t)
            if attempt['result']=='COMMIT':
                for h in range(32):B.pre_readout(t,h,attempt['trial_units'][h],attempt['trial_epoch'],r['state_bits'])
                guard=[];B.transfer(guard,'ext.readout_guardmax',B.aux,256,0,0);B.compute(guard,{'compare64':32,'scalar_control':2})
                B.macro('state.allhead_readout_I64_guard_barrier',guard,{'actual_guard':'maxabs_product * 256 <= I64MAX','all_heads':32},t)
                for h in range(32):B.readout(t,h,attempt['trial_units'][h],attempt['trial_epoch'],r['state_bits'])
            else:
                heads=[h for h,c in enumerate(attempt['range_violations']) if c>0]
                body=[]
                for h in heads:
                    sub=[];D=B.dpage
                    B.transfer(sub,'ext.trial','local.old',D*256*b,h*128*256*b,0,src_index=(D*256*b,))
                    B.memory(sub,[B.access('local.old',0,D*256*b)])
                    B.compute(sub,{'rne64':D*256,'cast_i32_guard':D*256})
                    B.memory(sub,[B.access('local.old',0,D*256*b,'write')])
                    B.transfer(sub,'local.old','ext.trial',D*256*b,0,h*128*256*b,dst_index=(D*256*b,))
                    B.loop(body,128//D,sub)
                    B.transfer(body,B.units_trial,B.aux,2,h*2,0);B.compute(body,{'scalar_control':1});B.memory(body,[B.access(B.aux,0,2,'write')]);B.transfer(body,B.aux,B.units_trial,2,0,h*2)
                B.transfer(body,B.desc_trial,B.aux,4,8,0);B.compute(body,{'scalar_control':1});B.memory(body,[B.access(B.aux,0,4,'write')]);B.transfer(body,B.aux,B.desc_trial,4,0,8)
                B.macro('state.causal_trial_recode',body,{'attempt':attempt['attempt'],'affected_heads':heads,'next_epoch':attempt['trial_epoch']+1,'published':False},t)
        B.eltwise('gate_silu',I,'ext.projected','ext.gated',t,lut='const.silu_lut_q12')
        B.eltwise('gate_multiply',I,'ext.scan','ext.gated',t,mul=True,other='ext.gated')
        B.norm('gated_norm',I,'ext.gated','const.gated_gamma_q20','ext.gated_norm',t)
        B.dynamic('out',I,'ext.gated_norm','ext.out_a8',runtime['out_a8_delta'][t],t)
        B.matrix('out',H,I,'const.out_weight_w8',('const.out_scale_q31','const.out_scale_exp'),'const.out_bias_q12','ext.out_a8','ext.out',t)
        B.eltwise('output_mup',H,'ext.out','ext.mamba',t,mul=True,constant='const.ssm_out_multiplier_q20')
        B.eltwise('attention_mup',H,'ext.attention','ext.attention_scaled',t,mul=True,constant='const.attention_out_multiplier_q20')
        B.eltwise('join_residual_R',H,'ext.input','ext.join1',t,add=True,other='ext.mamba')
        B.eltwise('join_A',H,'ext.join1','ext.join',t,add=True,other='ext.attention_scaled')
        B.norm('next_norm',H,'ext.join','const.next_gamma_q20','ext.nextnorm',t)
        body=[]
        B.compute(body,{'scalar_control':32+6})
        private_desc='ext.desc1' if t%2==0 else 'ext.desc0'
        B.memory(body,[B.access(B.aux,0,96,'write')])
        B.transfer(body,B.aux,private_desc,96)
        B.transfer(body,B.aux,'ext.descriptor',16) # single 128bit descriptor publication after all private data/consumer completion
        B.macro('atomic_publish_after_complete_consumer',body,{'epoch':txn['after']['epoch'],'position':txn['after']['position'],
            'version':txn['after']['version'],'units':txn['after']['units'],'nextnorm_precedes_publish':True,
            'published_state_sha256':txn['after']['state_sha256'],'state_object':B.state_next,'history_object':B.hist_trial,'units_object':B.units_trial,'atomic_descriptor_bytes':16},t)
        if (t+1)%8==0:
            body=[];B.transfer(body,B.state_next,'ext.old',E*b);B.transfer(body,'ext.old',B.state_next,E*b)
            B.macro('chunk_checkpoint_state_reload',body,{'position':t+1,'observer_checksums_excluded':True,'state_and_descriptor_persist':True},t)
    return B,task


def run(args):
    out=Path(args.out)
    if out.exists():raise ValueError('refuse overwrite')
    bd=load(args.binding)
    if not bd.get('commit') or bd.get('service_sha256')!=sha(__file__):raise ValueError('service source binding')
    out.mkdir(parents=True);started=time.monotonic()
    manifest={'schema':'closure-service-run-v1','status':'ERROR','source':bd,'producer_sha256':sha(__file__),'artifacts':[]}
    try:
        B,task=build(args)
        with (out/'witness.jsonl.gz').open('xb') as raw:
            with gzip.GzipFile(fileobj=raw,mode='wb',mtime=0,compresslevel=3) as f:
                for ev in B.events:f.write((json.dumps(ev,sort_keys=True,separators=(',',':'))+'\n').encode())
        summary={'schema':'closure-service-v1','task':task,'config':{'placement':args.placement,'label':args.label,'state_bits':task['bits'],
                'Dpage':B.dpage,'wide_factor':args.wide_factor,'policy':'serialized single-token complete branch, no batch packing'},
            'inventory':B.inventory,'allocations':list(B.alloc.values()),'used_bytes':dict(B.used),'counts':dict(B.totals),
            'events':len(B.events),'end_slot':B.clock,'trajectory_unchanged':True,
            'qualification':'conditional complete integer service policy; independent mathematical PASS is not model quality or RTL/PPA',
            'limits':['All input/output cuts, full K, wide products/reassembly/RNE, SFU, finite1RW/packets/FIFO and target state guards/clones/retries counted',
                'No physical layout/timing calibration; baseline bytewise costs and wide-factor sensitivity are explicit assumptions',
                'All single-token matrix operations use16 effective PEs from M256; prefill64 also deliberately not batched',
                'The same math task/source/units/epochs/backing is used in each placement; pure split/shared label has identical calendar',
                'Readout actual I64 guards accepted; generic S32xC32xN256 may require71bits and is not promised without guards'],
            'environment':{'python':platform.python_version(),'numpy':np.__version__}}
        put(out/'summary.json',summary)
        manifest['status']='EXECUTED_CONDITIONAL_SERVICE'
        manifest['artifacts']=[{'path':p.name,'bytes':p.stat().st_size,'sha256':sha(p)} for p in (out/'summary.json',out/'witness.jsonl.gz')]
    except Exception as e:
        manifest['error']={'type':type(e).__name__,'message':str(e),'traceback':traceback.format_exc()};raise
    finally:
        manifest['elapsed_seconds']=time.monotonic()-started;put(out/'manifest.json',manifest)


def main():
    p=argparse.ArgumentParser(__doc__)
    for name in ('numeric','compiled','receipt','binding','out'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--placement',choices=tuple(VARIANTS),required=True)
    p.add_argument('--label',choices=('shared','split'),required=True)
    p.add_argument('--wide-factor',type=int,choices=(1,2,4),default=1)
    run(p.parse_args())

if __name__=='__main__':main()
