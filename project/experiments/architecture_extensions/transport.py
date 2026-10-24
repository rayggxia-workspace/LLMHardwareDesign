"""Source-bound capacity certificates and COPY-only calendars, Issue70.

No arithmetic timing: these are data-movement lower-bound experiments.
"""
import argparse
import ast
from collections import defaultdict
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import platform
import struct
import zipfile


SIZES = {'V':16384,'R':32768,'M':32768,**{'S'+str(i):32768 for i in range(8)},'EXT':128*1024*1024}
WIRE = {'beat_bytes':16,'header_bytes':32,'max_payload':1984,'fifo_bytes':2048,
        'bank_port':'one shared read/write 128bit','bus':'one 128bit shared BUS',
        'external_port_ii':1,'qualification':'external latency/bandwidth assumption, unmeasured'}


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for x in iter(lambda:f.read(8<<20),b''):
            h.update(x)
    return h.hexdigest()


def save(path,obj):
    Path(path).write_text(json.dumps(obj,indent=2,sort_keys=True,allow_nan=False)+'\n',encoding='utf-8',newline='\n')


def canonical(obj):
    return json.dumps(obj,sort_keys=True,separators=(',',':'),allow_nan=False).encode()


def ceildiv(x,y):
    return (x+y-1)//y


def access_beats(offset,size):
    if type(offset) is not int or type(size) is not int or offset<0 or size<0:
        raise ValueError('physical access domain')
    return ceildiv(offset%16+size,16) if size else 0


def res(resource,offset,duration,amount=1):
    return {'resource':resource,'offset':offset,'duration':duration,'amount':amount}


def capacities():
    cap = {'BUS':1}
    for bank in SIZES:
        cap['PORT:'+bank] = 1
        for direction in ('TX','RX'):
            cap['EP:'+bank+':'+direction] = 1
            cap['FIFO:'+bank+':'+direction] = 2048
    return cap


def certificate(label,bank,objects):
    if bank not in SIZES or any(type(v) is not int or v<0 for v in objects.values()):
        raise ValueError('capacity domain')
    required = sum(objects.values())
    return {'label':label,'bank':bank,'objects':objects,'required_bytes':required,
            'capacity_bytes':SIZES[bank],'status':'FITS_CAPACITY_ONLY' if required<=SIZES[bank] else 'REJECT_CAPACITY',
            'excess_bytes':max(0,required-SIZES[bank]),'lifetime':'all listed objects simultaneous',
            'not_proven':'arithmetic, address generation, timing, or complete dataflow feasibility'}


def aggregate_s_certificate(label,objects):
    c=certificate(label,'S0',objects)
    c.update(bank='S_ALL',capacity_bytes=8*32768,
             status='FITS_CAPACITY_ONLY' if c['required_bytes']<=8*32768 else 'REJECT_CAPACITY',
             excess_bytes=max(0,c['required_bytes']-8*32768),
             allocation='aggregate lower bound only; no implicit multiport bank')
    return c


class CopyGraph:
    def __init__(self):
        self.nodes=[]; self.seq=defaultdict(list); self.logical=defaultdict(int)

    def io(self,bank,read,write,deps,label,accesses=None):
        """Required bank read/write service only; no math or free register accumulator."""
        if read<0 or write<0 or not read+write:
            raise ValueError('local IO amount')
        # Independent addresses cannot silently share a physical word transaction.
        # A 3-byte descriptor at byte15 crosses two 128bit words.
        duration=(sum(access_beats(a['offset'],a['bytes']) for a in accesses)
                  if accesses else ceildiv(read,16)+ceildiv(write,16))
        n={'id':len(self.nodes),'kind':'local_io','deps':list(dict.fromkeys(deps)),
           'duration':duration,'reservations':[res('PORT:'+bank,0,duration)],
           'meta':{'bank':bank,'read_bytes':read,'write_bytes':write,'label':label,'accesses':accesses or [],
                   'compute_cycles':'NOT_MODELED; port-only lower bound'}}
        self.nodes.append(n)
        return [n['id']]

    def copy(self,src,dst,size,deps,label,src_base=0,dst_base=0):
        if src==dst or type(size) is not int or size<=0:
            raise ValueError('copy domain')
        if min(src_base,dst_base)<0 or size+src_base>SIZES[src] or size+dst_base>SIZES[dst]:
            raise ValueError('copy object exceeds finite endpoint bank; explicit tiling required')
        previous=list(deps); result=[]
        for offset in range(0,size,1984):
            payload=min(1984,size-offset)
            rd=access_beats(src_base+offset,payload)
            wire=ceildiv(payload+32,16)
            wr=access_beats(dst_base+offset,payload)
            duration=rd+wire+wr
            rr=[res('PORT:'+src,0,rd),res('BUS',rd,wire),res('PORT:'+dst,rd+wire,wr)]
            for bank,direction in ((src,'TX'),(dst,'RX')):
                rr.extend([res('EP:'+bank+':'+direction,0,duration),
                           res('FIFO:'+bank+':'+direction,0,duration,payload)])
            n={'id':len(self.nodes),'kind':'packet','deps':list(dict.fromkeys(previous)),
               'duration':duration,'reservations':rr,'meta':{'src':src,'dst':dst,
                 'payload_bytes':payload,'wire_bytes':wire*16,'object_bytes':size,
                 'object_offset':offset,'src_address':src_base+offset,'dst_address':dst_base+offset,'label':label}}
            self.nodes.append(n);result.append(n['id']);previous=[n['id']]
            self.logical[src+'->'+dst]+=payload
        return result[-1:]


def schedule(graph,strategy):
    if strategy not in ('fifo','critical'):
        raise ValueError('strategy')
    nodes=json.loads(json.dumps(graph.nodes)); children=defaultdict(list)
    for n in nodes:
        for d in n['deps']:
            children[d].append(n['id'])
    critical={}
    for n in reversed(nodes):
        critical[n['id']]=n['duration']+max((critical[c] for c in children[n['id']]),default=0)
    pending={n['id'] for n in nodes}; readytime={}; free=defaultdict(int)
    while pending:
        ready=[i for i in pending if all(d in readytime for d in nodes[i]['deps'])]
        if not ready:
            raise ValueError('cycle')
        key=min(ready,key=lambda i:(i,) if strategy=='fifo' else (-critical[i],i))
        n=nodes[key]
        start=max([0]+[readytime[d] for d in n['deps']]+[
            free[r['resource']]-r['offset'] for r in n['reservations']])
        n['start']=start; n['end']=start+n['duration']
        for r in n['reservations']:
            free[r['resource']]=start+r['offset']+r['duration']
        readytime[key]=n['end'];pending.remove(key)
    return nodes


def independent_checker(path):
    spec=importlib.util.spec_from_file_location('issue68_independent_copy_intervals',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module.verify_intervals


def check_packet_formula(nodes):
    """Public receipt consistency; independent interval sweep is separate code."""
    for n in nodes:
        if n['kind']=='packet':
            m=n['meta'];p=m['payload_bytes']
            if not 0<p<=1984 or m['wire_bytes']!=ceildiv(p+32,16)*16:
                raise ValueError('wire amount')
            if m['object_offset']<0 or m['object_offset']+p>m['object_bytes']:
                raise ValueError('packet object bound')
            if any(m[k+'_address']<0 or m[k+'_address']+p>SIZES[m[k]] for k in ('src','dst')):
                raise ValueError('packet physical bank address')
        elif n['kind']=='local_io':
            m=n['meta']; bank=m['bank']
            for a in m['accesses']:
                if a['direction'] not in ('read','write') or a['offset']<0 or a['offset']+a['bytes']>SIZES[bank]:
                    raise ValueError('local IO address')
            if m['accesses']:
                for direction in ('read','write'):
                    if sum(a['bytes'] for a in m['accesses'] if a['direction']==direction)!=m[direction+'_bytes']:
                        raise ValueError('local IO amount/address inconsistency')


def bank_for(index,layout):
    if layout not in ('roundrobin','all_one'):
        raise ValueError('layout')
    return 'S'+str(index%8 if layout=='roundrobin' else 0)


def granite_graph(h,tile,layout):
    g=CopyGraph(); last=[]
    # Actual scales/IDs are not granted free residency. One token's descriptor/scales loaded.
    last=g.copy('EXT','V',8+16+8+8*8+2,last,'token route IDs/Q15/input/down scales/common unit',
                src_base=8*h*(4+6),dst_base=tile*18)
    for offset in range(0,h,tile):
        width=min(tile,h-offset)
        last=g.io('V',0,width*8,last,'initialize finite S64 accumulator',
                  [{'direction':'write','offset':tile*10,'bytes':width*8}])
        # One expert at a time. Scale/RQ parameters occupy V slots and traverse the BUS.
        for expert in range(8):
            bank=bank_for(expert,layout)
            a=g.copy('EXT',bank,width*4,last,'expert S32 return backing->staging',src_base=(expert*h+offset)*4)
            b=g.copy('EXT','M',width*6,last,'actual Q31 multiplier/int16 shift backing->M',src_base=8*h*4+(expert*h+offset)*6)
            b=g.copy('M','V',width*6,b,'RQ parameters M->V',dst_base=tile*4)
            a=g.copy(bank,'V',width*4,a+b,'expert S32 return staging->V')
            last=g.io('V',width*(4+6+8)+3,width*8,a,'RQ and wide merge minimum IO; arithmetic omitted',
                [{'direction':'read','offset':0,'bytes':width*4},
                 {'direction':'read','offset':tile*4,'bytes':width*6},
                 {'direction':'read','offset':tile*10,'bytes':width*8},
                 {'direction':'read','offset':tile*18+expert*3,'bytes':3},
                 {'direction':'write','offset':tile*10,'bytes':width*8}])
        last=g.io('V',width*8,width*4,last,'S64->S32 minimum IO; RNE/sat compute omitted',
            [{'direction':'read','offset':tile*10,'bytes':width*8},{'direction':'write','offset':0,'bytes':width*4}])
        last=g.copy('V','EXT',width*4,last,'merged S32 tile store',dst_base=8*h*10+98+offset*4)
    return g


def state_graph(n,d,bits,tile_d,layout,heads=32):
    g=CopyGraph();stage_last={}; proposal=[]
    descriptor=24+(2 if bits==16 else 0)
    last_r=g.copy('EXT','R',descriptor,[],'read declared owner/epoch/version/position and optional unit',
                  src_base=2*heads*n*d*(bits//8),dst_base=16384)
    last_r=g.io('R',descriptor,0,last_r,'descriptor validation minimum IO; guard compute omitted',
                [{'direction':'read','offset':16384,'bytes':descriptor}])
    # One complete captured head; all N cells of each selected D tile, no truncated reduction.
    for i,offset in enumerate(range(0,d,tile_d)):
        width=min(tile_d,d-offset); amount=n*width*(bits//8);bank=bank_for(i,layout)
        deps=stage_last.get(bank,[])+last_r
        a=g.copy('EXT',bank,amount,deps,'committed head state tile backing->S',src_base=offset*n*(bits//8))
        a=g.copy(bank,'R',amount,a,'committed complete-N tile S->R')
        a=g.io('R',amount,amount,a,'state update minimum IO; recurrence arithmetic omitted',
            [{'direction':'read','offset':0,'bytes':amount},{'direction':'write','offset':8192,'bytes':amount}])
        a=g.copy('R',bank,amount,a,'proposal complete-N tile R->S',src_base=8192)
        a=g.copy(bank,'EXT',amount,a,'proposal state backing write',dst_base=heads*n*d*(bits//8)+offset*n*(bits//8))
        stage_last[bank]=a;proposal.extend(a);last_r=a
    # Guard/atomic commit cost unknown. A full publication barrier is retained, no free claim.
    final=[]
    for i,offset in enumerate(range(0,d,tile_d)):
        width=min(tile_d,d-offset);amount=n*width*(bits//8);bank=bank_for(i,layout)
        a=g.copy('EXT',bank,amount,proposal+last_r,'published state output readback backing->S',
                 src_base=heads*n*d*(bits//8)+offset*n*(bits//8))
        a=g.copy(bank,'R',amount,a,'published complete-N state S->R')
        a=g.io('R',amount,0,a,'complete-N state output contraction minimum IO; compute omitted',
            [{'direction':'read','offset':0,'bytes':amount}])
        final.extend(a);last_r=a
    final=g.io('R',0,descriptor,final,'write updated owner/epoch/version/position and optional unit',
                [{'direction':'write','offset':16384,'bytes':descriptor}])
    g.copy('R','EXT',descriptor,final,'store declared commit descriptor; atomic publication timing omitted',
           src_base=16384,dst_base=2*heads*n*d*(bits//8))
    return g


def norm_join_graph(norm_h,hidden,tile,layout,norm_before_gate=False):
    g=CopyGraph();scan=[]
    last=g.io('V',0,8,[],'initialize full-row reduction accumulator',
              [{'direction':'write','offset':tile*16,'bytes':8}])
    for i,offset in enumerate(range(0,norm_h,tile)):
        amount=min(tile,norm_h-offset)*4;bank=bank_for(i,layout)
        a=g.copy('EXT',bank,amount,last,'gatednorm full-row reduction scan',src_base=offset*4)
        a=g.copy(bank,'V',amount,a,'gatednorm scan staging->V')
        if not norm_before_gate:
            # Native norm-before-gate=false reduces (raw * SiLU(gate))**2.
            # Without a separately paid pre-gated materialization, gate is read here too.
            a=g.copy('EXT',bank,amount,a,'gatednorm first-scan gate backing->S',src_base=norm_h*4+offset*4)
            a=g.copy(bank,'V',amount,a,'gatednorm first-scan gate staging->V',dst_base=tile*4)
        first_reads=[{'direction':'read','offset':0,'bytes':amount}]
        if not norm_before_gate:
            first_reads.append({'direction':'read','offset':tile*4,'bytes':amount})
        last=g.io('V',amount*(1 if norm_before_gate else 2)+8,8,a,'global reduction minimum IO; gate/square/sum omitted',
                  first_reads+[
                   {'direction':'read','offset':tile*16,'bytes':8},
                   {'direction':'write','offset':tile*16,'bytes':8}])
        scan.extend(last)
    for i,offset in enumerate(range(0,norm_h,tile)):
        amount=min(tile,norm_h-offset)*4;bank=bank_for(i,layout)
        deps=scan+last
        for plane,label in enumerate(('gatednorm x second read','gatednorm gate','gatednorm gamma')):
            a=g.copy('EXT',bank,amount,deps,label+' backing->S',src_base=plane*norm_h*4+offset*4)
            a=g.copy(bank,'V',amount,a,label+' staging->V',dst_base=plane*tile*4)
            deps=a
        last=g.io('V',amount*3+8,amount,deps,'gatednorm complete-row dependency minimum IO; math omitted',
            [{'direction':'read','offset':p*tile*4,'bytes':amount} for p in range(3)]+
            [{'direction':'read','offset':tile*16,'bytes':8}]+
            [{'direction':'write','offset':tile*12,'bytes':amount}])
        last=g.copy('V','EXT',amount,last,'gatednorm FP32 output',src_base=tile*12,dst_base=norm_h*12+offset*4)
    last=g.copy('EXT','V',64,last,'A/R sequence token valid-length precision epoch descriptors',
                src_base=norm_h*16+hidden*16,dst_base=tile*16)
    last=g.io('V',64,0,last,'A/R descriptor matching minimum IO; comparison compute omitted',
              [{'direction':'read','offset':tile*16,'bytes':64}])
    branch=[]
    for i,offset in enumerate(range(0,hidden,tile)):
        amount=min(tile,hidden-offset)*4;bank=bank_for(i,layout)
        a=g.copy('EXT',bank,amount,last,'A branch output',src_base=norm_h*16+offset*4)
        a=g.copy(bank,'V',amount,a,'A branch staging->join')
        b=g.copy('EXT','R',amount,last,'R branch output',src_base=norm_h*16+hidden*4+offset*4)
        b=g.copy('R','V',amount,b,'R branch->join',dst_base=tile*4)
        c=g.copy('EXT',bank,amount,a+b,'residual hidden input',src_base=norm_h*16+hidden*8+offset*4)
        c=g.copy(bank,'V',amount,c,'residual staging->join',dst_base=tile*8)
        last=g.io('V',amount*3,amount,c,'residual+A/R join minimum IO; multipliers/add omitted',
            [{'direction':'read','offset':p*tile*4,'bytes':amount} for p in range(3)]+
            [{'direction':'write','offset':tile*12,'bytes':amount}])
        last=g.copy('V','EXT',amount,last,'residual+A/R FP32 joined output',src_base=tile*12,dst_base=norm_h*16+hidden*12+offset*4);branch.extend(last)
    return g


def load_source(directory,kind,diagnostic_failed_chunk=False):
    manifest=json.loads((directory/'manifest.json').read_text())
    if manifest.get('kind')!=kind and not(kind=='falcon_capture' and manifest.get('schema')=='falcon-h1-bounded-v1'):
        raise ValueError('source kind expected '+kind)
    if manifest.get('status')=='PARTIAL_DIAGNOSTIC':
        qualification=manifest.get('reference_qualification',{})
        if (not diagnostic_failed_chunk or kind!='granite_numeric'
                or qualification.get('capture_status')!='FAIL'
                or qualification.get('chunk_reference_accepted') is not False
                or qualification.get('quality_accepted') is not False
                or [v.get('check') for v in qualification.get('failed_checks',[])]!=['evaluation.chunk16']):
            raise ValueError('partial failed-chunk source needs explicit restricted diagnostic scope')
    elif manifest.get('status') not in ('PASS','EXECUTED'):
        raise ValueError('source not successfully executed')
    verified=[]
    for a in manifest['artifacts']:
        p=directory/a['path']
        # Actual selected artifacts must match before any shape/metric is consumed.
        if sha(p)!=a['sha256']:
            raise ValueError('source artifact SHA '+str(p))
        verified.append({'path':a['path'],'sha256':a['sha256'],'bytes':p.stat().st_size})
    return manifest,{'path':str(directory),'manifest_sha256':sha(directory/'manifest.json'),
                     'status':manifest['status'],'reference_qualification':manifest.get('reference_qualification'),
                     'verified_artifacts':verified}


def npz_header(path,key):
    """Read actual NumPy member header only; no loading multi-GB arrays or pickle."""
    with zipfile.ZipFile(path) as z, z.open(key+'.npy') as f:
        if f.read(6)!=b'\x93NUMPY':
            raise ValueError('NPY magic')
        version=f.read(2)
        if version not in (b'\x01\x00',b'\x02\x00',b'\x03\x00'):
            raise ValueError('NPY version')
        size=struct.unpack('<H' if version==b'\x01\x00' else '<I',f.read(2 if version==b'\x01\x00' else 4))[0]
        if size>4096:
            raise ValueError('bounded NPY header')
        header=ast.literal_eval(f.read(size).decode('utf-8'))
        if 'O' in str(header['descr']) or not all(type(x) is int and x>=0 for x in header['shape']):
            raise ValueError('NPY dtype/shape')
        return {'shape':list(header['shape']),'dtype':header['descr'],'fortran_order':header['fortran_order']}


def run(args):
    if args.out.exists():
        raise ValueError('refuse overwrite')
    binding=json.loads(args.binding.read_text())
    checker=Path(__file__).parents[1]/'range_service'/'receive_service.py'
    if not binding.get('commit') or binding.get('transport_sha256')!=sha(__file__):
        raise ValueError('source binding')
    if binding.get('interval_checker_sha256')!=sha(checker):
        raise ValueError('independent interval checker binding')
    verify=independent_checker(checker)
    sources={};certs=[];specs=[];ledgers={}
    if args.granite:
        gm,sources['granite']=load_source(args.granite,'granite_numeric',getattr(args,'diagnostic_failed_chunk',False))
        metrics=json.loads((args.granite/'metrics.json').read_text())
        actual=[c for c in metrics['cases'] if c['activation']=='dynamic_row' and c['route']=='route_recomputed']
        if not actual or actual[0]['logical_payload_per_token']['expert_return_S32']!=8*1536*4:
            raise ValueError('Granite actual full8/H1536 contract')
        h=1536
        certs.extend([certificate('full8 expert S32 return','V',{'returns':8*h*4}),
                      certificate('full S64 accumulator plus one expert return','V',{'accumulator':h*8,'return':h*4}),
                      certificate('one full expert W8 in M','M',{'gate_up_down_weights':h*512*3})])
        ledgers['granite']={'actual_case_metrics':actual,'scope':'one token complete top8/H1536 return and RQ/merge data only',
            'weight_compute_excluded':'full expert matrix compute, W8 and weight-scale streaming NOT scheduled; no free residency assumed',
            'payload_equivalence':'same S32 returns, Q31 coefficients, Q15 gates, S64 accumulator; no precision-changing early INT8 return'}
        for tile in (256,512):
            certs.append(certificate('Granite tile'+str(tile),'V',{'S64_accumulator':tile*8,
                'one_S32_return':tile*4,'Q31mult_shift':tile*6,'route_and_scale_descriptor':98}))
            for layout in ('roundrobin','all_one'):
                specs.append(('granite',tile,layout,granite_graph(h,tile,layout),{'state_precision':'not applicable','return':'S32','accumulator':'S64'}))
    if args.falcon:
        fm,sources['falcon']=load_source(args.falcon,'falcon_capture')
        cfg=json.loads((args.falcon/'config.json').read_text())
        report=json.loads((args.falcon/'report.json').read_text())
        n=int(cfg['mamba_d_state']);d=int(cfg['mamba_d_head']);heads=int(cfg['mamba_n_heads'])
        norm_h=int(cfg['mamba_d_ssm'] or cfg['mamba_expand']*cfg['hidden_size']);hidden=int(cfg['hidden_size'])
        if (n,d,heads,norm_h)!=(256,128,32,4096):
            raise ValueError('unreviewed Falcon complete state/norm configuration')
        headers={key:npz_header(args.falcon/'capture.npz',key) for key in
                 ('full.final.ssm','full.final.conv','full.final.kv_key','full.final.kv_value',
                  'evaluation.input','evaluation.attention','evaluation.mamba','evaluation.projected',
                  'evaluation.raw_scan','weight.gated_norm_gamma')}
        if headers['full.final.ssm']['shape']!=[1,heads,d,n] or headers['full.final.ssm']['dtype']!='<f4':
            raise ValueError('actual captured complete FP32 state shape')
        if headers['weight.gated_norm_gamma']['shape']!=[norm_h] or report['gated_norm']['elements']!=norm_h:
            raise ValueError('actual complete gatednorm shape')
        if any(headers[k]['shape'][-1]!=hidden for k in ('evaluation.input','evaluation.attention','evaluation.mamba')):
            raise ValueError('actual complete branch width')
        if headers['evaluation.raw_scan']['shape'][-1]!=norm_h or headers['evaluation.projected']['shape'][-1]<norm_h:
            raise ValueError('actual complete gatednorm raw/gate source width')
        for bits,tile_d in ((32,8),(16,16)):
            b=bits//8;head=n*d*b;full=head*heads
            state_format='FP32' if bits==32 else 'S16-candidate'
            certs.append(certificate('Falcon complete head '+state_format,'R',{'state':head}))
            certs.append(aggregate_s_certificate('Falcon full32head two generations '+state_format,{'old_and_new':full*2}))
            certs.append(certificate('Falcon tiled old/new '+state_format,'R',{'old':n*tile_d*b,'new':n*tile_d*b,'aux':8192}))
            for layout in ('roundrobin','all_one'):
                specs.append(('falcon-state-'+state_format,tile_d,layout,state_graph(n,d,bits,tile_d,layout),
                    {'state_precision':'captured FP32' if bits==32 else 'S16 STORAGE CANDIDATE ONLY; numeric quality not proven',
                     'trace_scope':'one COMPLETE captured head; full32head capacity/byte ledger separate, no cycle extrapolation'}))
        certs.append(certificate('Falcon gatednorm all planes','V',{'x':norm_h*4,'gate':norm_h*4,'gamma':norm_h*4,'output':norm_h*4,'reduction':8}))
        certs.append(certificate('Falcon residual+A/R full join','V',{'residual':hidden*4,'A':hidden*4,'R':hidden*4,'joined':hidden*4,'descriptors':64}))
        ledgers['falcon']={'state_shape':[1,heads,d,n],'full32head_state_bytes':{'FP32':heads*d*n*4,'S16_candidate':heads*d*n*2},
            'actual_capture_headers':headers,'native_report_inventory':report['inventory'],
            'full_model_single_generation_state_FP32':int(cfg['num_hidden_layers'])*heads*d*n*4,
            'norm_width':norm_h,'norm_before_gate':bool(cfg['mamba_norm_before_gate']),
            'norm_minimum_logical_FP32_source_and_output_bytes':norm_h*4*(5 if cfg['mamba_norm_before_gate'] else 6),
            'norm_global_dependency':'full first-row scan including gate when norm_before_gate=false; then second raw/gate/gamma read/output; no tilewise independent norm',
            'join_width':hidden,'join_input_planes':['residual','attention','mamba'],'join_output_planes':1,
            'join_logical_FP32_input_and_output_bytes':hidden*4*4,'join_descriptors_bytes':64,
            'KV':'actual full model cache storage must remain separately charged; not a state=KV alias',
            'excluded':'compute, nonlinear arithmetic, cache/weight loads, KV update, atomic guard latency; no full-model service claim'}
        for bits in (32,16):
            # State candidate changes state storage only; keep conv/KV FP32 and charge their real shapes.
            def elems(key):
                value=1
                for v in headers[key]['shape']:
                    value*=v
                return value
            layers=int(cfg['num_hidden_layers'])
            state_format='FP32' if bits==32 else 'S16-candidate'
            certs.append(certificate('Falcon all-layer persistent backing '+state_format+' plus actual FP32 KV/conv','EXT',
                {'state':layers*heads*d*n*(bits//8),'conv':layers*elems('full.final.conv')*4,
                 'KV':layers*(elems('full.final.kv_key')+elems('full.final.kv_value'))*4,
                 'owner_version_position':layers*24,'units':layers*heads*2 if bits==16 else 0}))
        for tile in (256,512):
            certs.append(certificate('Falcon norm tile'+str(tile),'V',{'x':tile*4,'gate':tile*4,'gamma':tile*4,'output':tile*4,'reduction':8}))
            certs.append(certificate('Falcon residual+A/R join tile'+str(tile),'V',{'residual':tile*4,
                'A':tile*4,'R':tile*4,'joined':tile*4,'descriptors':64}))
            for layout in ('roundrobin','all_one'):
                specs.append(('falcon-norm-join',tile,layout,norm_join_graph(norm_h,hidden,tile,layout,
                    norm_before_gate=bool(cfg['mamba_norm_before_gate'])),{'data':'captured FP32'}))
    if not specs:
        raise ValueError('at least one actual source required')
    args.out.mkdir(parents=True)
    rows=[];artifacts=[]
    for suite,tile,layout,g,precision in specs:
        for strategy in ('fifo','critical'):
            nodes=schedule(g,strategy);check_packet_formula(nodes)
            audit=verify(nodes,capacities())
            tag=suite+'-t'+str(tile)+'-'+layout+'-'+strategy
            witness={'schema_version':1,'tag':tag,'scope':'COPY/PORT-IO ONLY; arithmetic cycles omitted lower bound',
                'precision':precision,'inventory_bytes':SIZES,'wire_contract':WIRE,'capacities':capacities(),'nodes':nodes}
            blob=gzip.compress(canonical(witness),mtime=0)
            (args.out/(tag+'.json.gz')).write_bytes(blob)
            artifacts.append({'path':tag+'.json.gz','bytes':len(blob),'sha256':sha(args.out/(tag+'.json.gz')),'kind':'complete_copy_calendar'})
            payload=sum(n['meta']['payload_bytes'] for n in nodes if n['kind']=='packet')
            wire=sum(n['meta']['wire_bytes'] for n in nodes if n['kind']=='packet')
            rows.append({'tag':tag,'suite':suite,'tile':tile,'layout':layout,'strategy':strategy,
                'logical_transmitted_bytes':payload,'wire_bytes':wire,'header_and_padding_bytes':wire-payload,
                'packets':sum(n['kind']=='packet' for n in nodes),'route_payload_bytes':dict(g.logical),
                'independent_interval_audit':audit,'scope':witness['scope'],'precision':precision})
    metrics={'schema_version':1,'capacity_certificates':certs,'ledgers':ledgers,'copy_calendars':rows,
        'reference_qualifications':{k:v['reference_qualification'] for k,v in sources.items() if v.get('reference_qualification')},
        'qualification':'fixed finite banks/BUS/FIFOs; source data format held constant within each comparison; no compute scheduling or physical timing',
        'not_ranked':'capacity rejected materialized candidates have no fabricated cycles; FP32 and S16 are separate, not performance peers'}
    save(args.out/'metrics.json',metrics)
    artifacts.append({'path':'metrics.json','bytes':(args.out/'metrics.json').stat().st_size,'sha256':sha(args.out/'metrics.json'),'kind':'capacity_and_copy_metrics'})
    partial=any(v['status']=='PARTIAL_DIAGNOSTIC' for v in sources.values())
    save(args.out/'manifest.json',{'schema_version':1,'kind':'architecture_transport','status':'PARTIAL_DIAGNOSTIC' if partial else 'EXECUTED',
        'reference_qualifications':metrics['reference_qualifications'],
        'diagnostic_failed_chunk_explicit':bool(getattr(args,'diagnostic_failed_chunk',False)),
        'source':{'commit':binding['commit'],'transport_sha256':sha(__file__),'interval_checker_sha256':sha(checker),
                  'binding_sha256':sha(args.binding)},'sources':sources,'host':platform.node(),
        'artifacts':artifacts,'acceptance':'copy interval witness checked, arithmetic/end-to-end/hardware not validated'})


def main():
    p=argparse.ArgumentParser(__doc__)
    p.add_argument('--granite',type=Path);p.add_argument('--falcon',type=Path)
    p.add_argument('--binding',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--diagnostic-failed-chunk',action='store_true')
    run(p.parse_args())


if __name__=='__main__':
    main()
