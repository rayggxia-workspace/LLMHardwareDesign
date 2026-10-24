"""Issue74 same-function grouped out projection M/V residency service.
Opaque inherited complete R chain plus explicitly replaced output kernel.
Conditional finite resource calendar, no RTL/PPA or model-speed claim.
"""
import argparse, copy, gzip, hashlib, importlib.util, json, platform, sys, time
from collections import Counter
from pathlib import Path
import numpy as np

HELPER=Path(__file__).resolve().parents[1]/'closure'/'service.py'
_spec=importlib.util.spec_from_file_location('issue74_closure_service',HELPER)
base=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(base)

# Byte-ALU schedule assumptions, explicitly separated from inherited primitives.
WIDE_COST={'digit_byte_op':1,'wide_s8_product':1,'constant_shift64':14,'constant_shift128':22,
           'wide_add64':10,'wide_add128':18,'rq_rne64_complete':106,'rq_rne128_complete':182,
           'signextend_i32_i64':11,'alignment_shift64':18}
RQ_RECIPES={
 '64':{'operand_digits':[5,5],'digit_extraction_byte_ops':18,'products':25,'constant_shift_byte_ops':14,'wide_adds':24,'wide_add_byte_ops':10,'RNE_byte_ops':106,
       'RNE_breakdown':{'abs':10,'byte_shift':24,'sticky':16,'half_tie':4,'increment':10,'sign_restore':10,'i32_guard':20,'control':12}},
 '128':{'operand_digits':[9,5],'digit_extraction_byte_ops':26,'products':45,'constant_shift_byte_ops':22,'wide_adds':44,'wide_add_byte_ops':18,'RNE_byte_ops':182,
        'RNE_breakdown':{'abs':18,'byte_shift':48,'sticky':32,'half_tie':4,'increment':18,'sign_restore':18,'i32_guard':32,'control':12}}}
REMOVED={'out.A8_absmax','out.A8_minimal_shift','out.A8_encode','out.matrix_fullK_RQ'}

def sha(path):return base.sha(path)
def put(path,value):return base.put(path,value)
def load(path):return base.load(path)
def arr_sha(a):
    a=np.ascontiguousarray(a);h=hashlib.sha256();h.update(str(a.dtype).encode());h.update(json.dumps(list(a.shape),separators=(',',':')).encode());h.update(a.tobytes());return h.hexdigest()
def artifacts(m):return {a['path']:{'bytes':a['bytes'],'sha256':a['sha256']} for a in m['artifacts']}
def canonical(ev):return {'stage':ev['stage'],'token':ev['token'],'phase':ev['phase'],'meta':ev['meta'],'body':ev['body'],'duration':ev['end']-ev['start']}
def canonical_sha(ev):return hashlib.sha256(json.dumps(canonical(ev),sort_keys=True,separators=(',',':')).encode()).hexdigest()

def signed_digits(n,bits):
    n=int(n)
    if not -(1<<(bits-1))<=n<(1<<(bits-1)):raise ValueError('signed operand domain')
    count=1 if bits<=8 else 1+(bits-8+6)//7;result=[]
    for _ in range(count-1):result.append(n&127);n>>=7
    if not -128<=n<=127:raise AssertionError('signed-high digit')
    return result+[n]

def rq_product_micro(a,b,bits):
    ad=signed_digits(a,bits);bd=signed_digits(b,32);total=0
    for i,x in enumerate(ad):
        for j,y in enumerate(bd):
            total+=(x*y)<<(7*(i+j))
            if not -(1<<127)<=total<(1<<127):raise OverflowError('I128 prefix')
    return total

class Builder(base.Builder):
    def __init__(self,summary,placement):
        if placement not in ('near_m','shared_v'):raise ValueError('placement')
        self.placement=placement;self.owner='M' if placement=='near_m' else 'V';self.wide_factor=1
        self.cap=copy.deepcopy(summary['inventory']['capacities']);self.alloc={a['object']:copy.deepcopy(a) for a in summary['allocations']};self.used=Counter(summary['used_bytes']);self.events=[];self.clock=0;self.totals=Counter()
        self.inventory=copy.deepcopy(summary['inventory']);self.inventory['grouped_kernel']={'Otile':16,'physical_Ktile':256,'VR8_count':8,'new_private_M_ALU':False,'VR8_interface':'same shared bank-select BUS master; every new operand and write packet consumes bank1RW and single BUS; no physical wire locality claim','VR8_operand_staging':'at most1024B from existing2048B endpoint FIFO, not extra SRAM','byte_cost':WIDE_COST,'rq_recipes':RQ_RECIPES,'wide_recipe':'signed-high radix128 digits, explicit S8 products and materialized constant-shift/wide-add; no free I128 ALU'}
        # Same bank capacities; scratch objects have real full-task lifetimes.
        self.add('gs.Vmeta','V',64)
        for bank in ('M','V'):
            for short,n in (('partial',64),('sum',128),('product',256),('shifted',256),('product16',32),('digits',224),('meta',256),('out',64),('control',64)):
                self.add('gs.'+bank+'.'+short,bank,n)
    def obj(self,short):return 'gs.'+self.owner+'.'+short
    def compute(self,body,counts,matrix_active=16):
        if not any(k in WIDE_COST for k in counts):return super().compute(body,counts,matrix_active)
        costs={**base.BYTE_COST,**WIDE_COST};c={k:int(v) for k,v in counts.items() if int(v)}
        if set(c)-set(costs):raise ValueError('unknown grouped primitive')
        slots=(sum(costs[k]*v for k,v in c.items())+7)//8
        return self.leaf(body,'compute',[('VR8',slots)],counts=c,matrix_active_PEs=matrix_active)
    def engine(self,body,obj,offset,n,mode='read',index=()):
        a=self.alloc[obj];x=self.access(obj,offset,n,mode,index_strides=index);cost=base.packet_cost(a['offset']+offset,0,n)
        bankbeats=cost['src_beats'];rr=[('bank.'+a['bank'],bankbeats),('BUS',cost['wire_beats'])] if mode=='read' else [('BUS',cost['wire_beats']),('bank.'+a['bank'],bankbeats)]
        counts={'engine_operand_read_bytes' if mode=='read' else 'engine_operand_write_bytes':n,'engine_local_beats':bankbeats,'engine_wire_bytes':cost['wire_bytes'],'engine_wire_beats':cost['wire_beats'],'engine_packets':cost['packets'],'wire_bytes':cost['wire_bytes'],'wire_beats':cost['wire_beats'],'packets':cost['packets'],'payload_bytes':n,'src_beats':bankbeats if mode=='read' else 0,'dst_beats':bankbeats if mode=='write' else 0}
        return self.leaf(body,'engine_access',rr,accesses=[x],counts=counts,FIFO_peak_bytes=32+16*((min(n,1984)+15)//16),engine='VR8',semantics='same bus-attached eight lane engine; no direct uncharged M ALU')
    def inherit(self,event):
        e=copy.deepcopy(event);duration=e['end']-e['start'];oldid=e['id'];digest=canonical_sha(e)
        e.update(id=len(self.events),start=self.clock,end=self.clock+duration,deps=[len(self.events)-1] if self.events else [],inherited_event_id=oldid,inherited_canonical_sha256=digest)
        self.events.append(e);self.clock+=duration;self.count_tree(e['body'],1)
    def encode(self,t,delta,common,gk):
        g=len(delta);body=[]
        self.memory(body,[self.access('gs.Vmeta',0,64,'write')]);self.compute(body,{'copy_byte':64})
        for gi,d in enumerate(delta):
            self.memory(body,[self.access('gs.V.control',0,4,'write')]);self.compute(body,{'scalar_control':1})
            for start in range(0,gk,512):
                n=min(512,gk-start);self.transfer(body,'ext.gated_norm','local.Vaux',n*4,(gi*gk+start)*4,0)
                self.memory(body,[self.access('local.Vaux',0,n*4),self.access('gs.V.control',0,4)])
                self.compute(body,{'abs64':n,'compare64':n});self.memory(body,[self.access('gs.V.control',0,4,'write')])
            self.memory(body,[self.access('gs.V.control',0,4)]);self.compute(body,{'rne64':int(d)+1,'scalar_control':int(d)+1})
            self.memory(body,[self.access('gs.Vmeta',gi*2,2,'write')])
            for start in range(0,gk,512):
                n=min(512,gk-start);self.transfer(body,'ext.gated_norm','local.Vaux',n*4,(gi*gk+start)*4,0)
                self.memory(body,[self.access('local.Vaux',0,n*4)]);self.compute(body,{'rne64':n,'cast_i32_guard':n})
                self.memory(body,[self.access('local.Vaux',4096,n,'write')]);self.transfer(body,'local.Vaux','ext.out_a8',n,4096,gi*gk+start)
        self.memory(body,[self.access('gs.Vmeta',0,2*g)]);self.compute(body,{'compare64':g-1,'scalar_control':1});self.memory(body,[self.access('gs.Vmeta',32,2,'write')])
        if self.owner=='M':self.transfer(body,'gs.Vmeta','gs.M.control',34)
        else:
            self.memory(body,[self.access('gs.Vmeta',0,34)]);self.compute(body,{'copy_byte':34});self.memory(body,[self.access('gs.V.control',0,34,'write')])
        self.macro('grouped.out.dynamic_A8',body,{'group_K':gk,'groups':g,'delta':list(map(int,delta)),'common_delta':int(common),'owner_bank':self.owner,'integer_current_input_only':True},t)
    def matrix_group(self,body,gi,gk):
        self.memory(body,[self.access('local.m_acc',0,64,'write')]);self.compute(body,{'copy_byte':64})
        inner=[];self.transfer(inner,'const.out_weight_w8','local.m_wrow',256,so=gi*gk,segments=16,ss=4096,ds=256,src_index=(16*4096,256),dst_index=(0,0))
        transpose=[];self.memory(transpose,[self.access('local.m_wrow',0,16,repeat=16,stride=256,index_strides=(16,)),self.access('local.m_regs',0,256,'write')]);self.memory(transpose,[self.access('local.m_regs',0,256)]);self.compute(transpose,{'copy_byte':256});self.memory(transpose,[self.access('local.m_wcol',0,256,'write',index_strides=(256,))]);self.loop(inner,16,transpose)
        self.memory(inner,[self.access('local.m_acc',0,64)])
        k16=[];self.memory(k16,[self.access('local.m_a',gi*gk,16,index_strides=(0,256,16))]);k1=[];self.memory(k1,[self.access('local.m_wcol',0,16,index_strides=(256,16))]);self.compute(k1,{'matrix_mac':16},16);self.loop(k16,16,k1);self.loop(inner,16,k16);self.memory(inner,[self.access('local.m_acc',0,64,'write')]);self.loop(body,gk//256,inner)
    def align(self,body,gi,groups,delta,common):
        if self.owner=='V':self.transfer(body,'local.m_acc',self.obj('partial'),64)
        partial='local.m_acc' if self.owner=='M' else self.obj('partial')
        if groups==1:return partial
        self.engine(body,partial,0,64);self.engine(body,self.obj('control'),gi*2,2);self.engine(body,self.obj('control'),32,2)
        if gi:self.engine(body,self.obj('sum'),0,128)
        counts={'signextend_i32_i64':16}
        if int(delta[gi])!=int(common):counts['alignment_shift64']=16
        if gi:counts['add64']=16
        self.compute(body,counts);self.engine(body,self.obj('sum'),0,128,'write')
        return self.obj('sum')
    def rq(self,body,source,groups):
        bits=64 if groups>1 else 32;pbits=128 if groups>1 else 64;pbytes=pbits//8;recipe=RQ_RECIPES[str(pbits)];ad,bd=recipe['operand_digits']
        self.transfer(body,'const.out_scale_q31',self.obj('meta'),64,do=0,src_index=(64,));self.transfer(body,'const.out_scale_exp',self.obj('meta'),32,do=64,src_index=(32,));self.transfer(body,'const.out_bias_q12',self.obj('meta'),64,do=128,src_index=(64,))
        self.engine(body,source,0,16*(bits//8));self.engine(body,self.obj('meta'),0,64)
        self.compute(body,{'digit_byte_op':16*recipe['digit_extraction_byte_ops']});self.engine(body,self.obj('digits'),0,16*(ad+bd),'write')
        for i in range(ad):
            for j in range(bd):
                self.engine(body,self.obj('digits'),i*16,16);self.engine(body,self.obj('digits'),(ad+j)*16,16)
                self.compute(body,{'wide_s8_product':16});self.engine(body,self.obj('product16'),0,32,'write');self.engine(body,self.obj('product16'),0,32)
                self.compute(body,{'constant_shift'+str(pbits):16})
                first=i==0 and j==0;target=self.obj('product') if first else self.obj('shifted');self.engine(body,target,0,16*pbytes,'write')
                if not first:
                    self.engine(body,self.obj('product'),0,16*pbytes);self.engine(body,self.obj('shifted'),0,16*pbytes);self.compute(body,{'wide_add'+str(pbits):16});self.engine(body,self.obj('product'),0,16*pbytes,'write')
        self.engine(body,self.obj('product'),0,16*pbytes);self.engine(body,self.obj('meta'),64,32);self.engine(body,self.obj('control'),32,2)
        self.compute(body,{'rq_rne'+str(pbits)+'_complete':16});self.engine(body,self.obj('out'),0,64,'write')
        self.engine(body,self.obj('out'),0,64);self.engine(body,self.obj('meta'),128,64);self.compute(body,{'add64':16,'cast_i32_guard':16});self.engine(body,self.obj('out'),0,64,'write');self.transfer(body,self.obj('out'),'ext.out',64,dst_index=(64,))
    def output(self,t,z):
        delta=z['a8_delta'][t];common=int(z['common_delta'][t]);groups=len(delta);gk=4096//groups
        self.encode(t,delta,common,gk);outer=[];self.transfer(outer,'ext.out_a8','local.m_a',4096);tile=[]
        source=None
        for gi in range(groups):self.matrix_group(tile,gi,gk);source=self.align(tile,gi,groups,delta,common)
        self.rq(tile,source,groups);self.loop(outer,160,tile)
        hashes={k:arr_sha(z[k][t]) for k in ('a8','a8_delta','common_delta','partial_acc32','aligned_sum_i64','rq_product_hi_i64','rq_product_lo_u64','out_linear_q12','join_q12','next_norm_q12')}
        self.macro('grouped.out.fullK_ALIGN_final_RQ',outer,{'token':t,'O':2560,'K':4096,'Otile':16,'physical_Ktile':256,'group_K':gk,'groups':groups,'owner_bank':self.owner,'effective_matrix_PEs':16,'complete_group_INT32_then_complete_K_alignment':True,'one_final_RQ_only':True,'product_bits':128 if groups>1 else 64,'VR8_operand_bundle_peak_bytes':576 if groups>1 else 320,'numeric_row_hashes':hashes},t)

def prepare(args):
    sm=base.bound(args.base_service);gs=base.bound(args.grouped);bm=base.bound(args.baseline);cm=base.bound(args.compiled)
    summary=load(Path(args.base_service)/'summary.json');receipt=load(args.base_receipt);nr=load(args.grouped_receipt);report=load(Path(args.grouped)/'report.json')
    if receipt['status']!='PASS' or receipt['artifacts']!=artifacts(sm):raise ValueError('independent base service receipt')
    if summary['config']['state_bits']!=32 or summary['config']['placement']!='r32_d8' or summary['config']['wide_factor']!=1:raise ValueError('fixed common whole-chain base')
    if summary['task']['numeric_manifest_sha256']!=sha(Path(args.baseline)/'manifest.json') or summary['task']['compiled_manifest_sha256']!=sha(Path(args.compiled)/'manifest.json'):raise ValueError('base numerical/compiler binding')
    if nr['status']!='PASS' or nr['artifacts']!=artifacts(gs) or nr['group_k']!=report['group_k']:raise ValueError('independent grouped math receipt')
    if report['baseline_manifest_sha256']!=sha(Path(args.baseline)/'manifest.json') or report['compiled_manifest_sha256']!=sha(Path(args.compiled)/'manifest.json'):raise ValueError('grouped baseline/compiler binding')
    if report['group_k'] not in (0,512,256):raise ValueError('predeclared granularity')
    z=np.load(Path(args.grouped)/'outproj.npz',allow_pickle=False)
    if z['a8'].shape!=(72,4096) or z['partial_acc32'].shape!=(72,report['groups'],2560):raise ValueError('complete actual group shape')
    task={'group_k':report['group_k'],'groups':report['groups'],'grouped_manifest_sha256':sha(Path(args.grouped)/'manifest.json'),'grouped_receipt_sha256':sha(args.grouped_receipt),'base_service_manifest_sha256':sha(Path(args.base_service)/'manifest.json'),'base_service_receipt_sha256':sha(args.base_receipt),'baseline_manifest_sha256':sha(Path(args.baseline)/'manifest.json'),'compiled_manifest_sha256':sha(Path(args.compiled)/'manifest.json'),'frozen_input_array_sha256':report['frozen_input_array_sha256'],'frozen_weight_array_sha256':report['frozen_weight_array_sha256'],'fixed_w_scale_array_sha256':report['fixed_w_scale_array_sha256'],'fixed_w_exp_array_sha256':report['fixed_w_exp_array_sha256'],'reference_errors':report['reference_errors'],'numeric_function':'each group fullINT32 dot, completeK same-exponent I64 align, one final Q31 RNE (g0 I64,g>1 I128), same complete consumers','state_bits':32,'tokens':72,'cuts':'external residual/A remain original encoded cuts; no attention/MLP closure'}
    return summary,z,task

def run(args):
    out=Path(args.out);out.mkdir(parents=True,exist_ok=False);bd=load(args.binding)
    if not bd.get('commit') or bd.get('grouped_service_sha256')!=sha(__file__) or bd.get('closure_service_sha256')!=sha(HELPER):raise ValueError('source/dependency binding')
    started=time.time();summary,z,task=prepare(args);b=Builder(summary,args.placement);inherited=[];removed=[];inserted=[]
    with gzip.open(Path(args.base_service)/'witness.jsonl.gz','rt',encoding='utf-8') as f:
        for line in f:
            event=json.loads(line)
            if event['stage'] in REMOVED:
                removed.append({'event_id':event['id'],'stage':event['stage'],'token':event['token'],'canonical_sha256':canonical_sha(event)})
                if event['stage']=='out.matrix_fullK_RQ':b.output(event['token'],z);inserted.append(event['token'])
            else:
                inherited.append({'event_id':event['id'],'canonical_sha256':canonical_sha(event)});b.inherit(event)
    if inserted!=list(range(72)) or len(removed)!=72*4:raise ValueError('unique exact service cut')
    with (out/'witness.jsonl.gz').open('xb') as raw:
        with gzip.GzipFile(fileobj=raw,mode='wb',mtime=0,compresslevel=3) as stream:
            for event in b.events:stream.write((json.dumps(event,sort_keys=True,separators=(',',':'))+'\n').encode())
    put(out/'splice.json',{'inherited':inherited,'removed':removed,'inserted_tokens':inserted,'common_R_trajectory_and_epochs_unchanged':True,'suffix_new_codes':'pergroup numeric row hashes bound at replacement; inherited suffix costs/shapes preserve full MuP/join/nextnorm, not original whole-row numerical outputs','base_summary_sha256':sha(Path(args.base_service)/'summary.json'),'base_witness_sha256':sha(Path(args.base_service)/'witness.jsonl.gz')})
    put(out/'summary.json',{'schema':'grouped-service-v1','task':task,'config':{'placement':args.placement,'label':args.label,'Otile':16,'physical_Ktile':256,'policy':'conservative serialized single row/no prefill batch; same arithmetic microprogram in pair'},'inventory':b.inventory,'allocations':list(b.alloc.values()),'used_bytes':dict(b.used),'counts':dict(b.totals),'end_slot':b.clock,'events':len(b.events),'limits':['Same numerical function within each group/placement pair; different groups have different quantized functions, no crossgroup placement causal claim.','Fixed bus-attached VR8 service supports M or V bank endpoints; this tests residency/transfer policy, not physical wire locality or new private M ALU.','Every wide operand/temporary packet and bank1RW/BUS is charged; explicit conservative bytewise recipes are not RTL calibration.','Inherited complete input/R/gatednorm and complete consumers remain in calendar; no model quality/actual INT8 speed/PPA acceptance.'],'environment':{'python':platform.python_version(),'numpy':np.__version__},'elapsed_seconds':time.time()-started})
    put(out/'manifest.json',{'schema':'grouped-service-run-v1','status':'EXECUTED_CONDITIONAL_SERVICE','source':bd,'producer_sha256':sha(__file__),'dependency_sha256':sha(HELPER),'artifacts':[{'path':p.name,'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(out.iterdir()) if p.is_file()]})
    print(json.dumps({'out':str(out),'end_slot':b.clock,'group_k':task['group_k'],'placement':args.placement,'manifest_sha256':sha(out/'manifest.json')}))

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('base-service','base-receipt','grouped','grouped-receipt','baseline','compiled','binding','out'):p.add_argument('--'+name,required=True)
    p.add_argument('--placement',choices=('near_m','shared_v'),required=True);p.add_argument('--label',choices=('split','shared'),required=True);run(p.parse_args())
if __name__=='__main__':main()
