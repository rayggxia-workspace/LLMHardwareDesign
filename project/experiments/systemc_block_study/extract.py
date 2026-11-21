"""Extract the frozen integer DAG without importing or editing its compiler."""
import argparse, collections, hashlib, json, math
from pathlib import Path

SOURCE=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search/algorithm-fix-277-phased-tile-full/generated/ir.json')

def write_trace(path,formats,nodes,scope,tokens):
    # Tensor IDs are dense. Runtime views are explicitly materialized.
    ids={name:i for i,name in enumerate(formats)}
    for node in nodes:ids[node['id']]=len(ids)
    bits={name:m['bits'] for name,m in formats.items()}
    shapes={name:m['shape'] for name,m in formats.items()}
    for node in nodes:bits[node['id']]=node['bits'];shapes[node['id']]=node['shape']
    lines=[f'{len(ids)} {len(nodes)} {tokens}']
    for name,i in ids.items():
        s=shapes[name];b=bits[name]
        lines.append(f'{i} {math.prod(s)} {b} {int(name in formats)}')
    for node in nodes:
        op=node['op'];s=node['shape'];a=node['attributes'];ins=[ids[x] for x in node['inputs']]
        k=a.get('length',1);n=s[-1] if s else 1;r=s[-2] if len(s)>1 else 1;batch=math.prod(s[:-2]) if len(s)>2 else 1
        # Immutable checkpoint B can be tiled offline. Dynamic QK/PV uses
        # explicit strided DMA and local gather; no host activation packing.
        layout=0 if len(ins)>1 and node['inputs'][1] in formats and 'cache' not in node['inputs'][1] else (2 if 'MatMul_1' in node['kernel'] else 1)
        if 'gqa_rows' in a:r=a['gqa_rows'];batch=a['gqa_batches']
        lines.append(' '.join(map(str,[ids[node['id']],op,math.prod(s),r,n,k,batch,a.get('shift',0),layout,len(ins),*ins])))
    Path(path).write_bytes(('\n'.join(lines)+'\n').encode())
    return {'scope':scope,'tokens':tokens,'tensors':len(ids),'nodes':len(nodes),'ops':dict(collections.Counter(n['op'] for n in nodes)),
            'trace_sha256':hashlib.sha256(Path(path).read_bytes()).hexdigest()}

def decode_graph(context):
    """Configuration-derived KV decode timing graph, not pretrained numeric qualification."""
    h,f,heads,kv,d,layers,vocab=2048,11008,16,2,128,36,151936
    fmt={};nodes=[]
    def tensor(name,shape,bits=32):fmt[name]={'shape':shape,'bits':bits};return name
    def op(kind,inputs,shape,**attrs):
        name='d'+str(len(nodes));nodes.append(dict(id=name,kernel=attrs.pop('kernel',kind),op=kind,inputs=inputs,shape=shape,bits=attrs.pop('bits',32),attributes=attrs));return name
    def weight(name,n,k):return tensor(name,[k,n],16)
    def norm(x,name):
        narrow=op('Convert',[x],[1,1,h],shift=0,bits=16)
        factor=op('NFactor',[narrow],[1,1,1],length=h)
        z=op('Product',[x,factor],[1,1,h],shift=12)
        return op('Product',[z,tensor(name,[h],16)],[1,1,h],shift=12)
    def dot(x,name,n,k):return op('Dot',[x,weight(name,n,k)],[1,1,n],length=k,shift=16)
    x=op('Gather',[tensor('embedding',[vocab,h],16),tensor('token',[],32)],[1,1,h])
    # Canonical operations below have explicit conservative local micro-op
    # costs in model.cpp. This graph is a workload projection, not a numeric
    # implementation or an export of a qualified KV decode program.
    rope=tensor('rope-tables',[context,d],32)
    coefficients=tensor('silu-coefficients',[21],32)
    for layer in range(layers):
        saved=x;z=norm(x,f'norm-attn{layer}')
        q=dot(z,f'q{layer}',h,h);k=dot(z,f'k{layer}',kv*d,h);v=dot(z,f'v{layer}',kv*d,h)
        q=op('RoPE',[q,rope],[1,1,h]);k=op('RoPE',[k,rope],[1,1,kv*d])
        kc=tensor(f'kcache{layer}',[1,kv,d,context],32)
        vc=tensor(f'vcache{layer}',[1,kv,context,d],32)
        # Keep K/V as [KVhead,context,head_dim] in DRAM. QK gathers K
        # by dimension rather than assuming the new token is pre-transposed.
        op('KVWrite',[k,v,kc,vc],[1,1,2*kv*d],length=context)
        score=op('Dot',[q,kc],[1,heads,1,context],length=d,shift=24,kernel='self_attn/MatMul',gqa_rows=8,gqa_batches=2)
        # Cache tensors are runtime state, never offline-tilable weights.
        mx=op('Max',[score],[1,heads,1,1],length=context)
        score=op('Sub',[score,mx],[1,heads,1,context])
        ex=op('NExp',[score],[1,heads,1,context])
        total=op('Sum',[ex],[1,heads,1,1],length=context)
        inverse=op('Reciprocal',[total],[1,heads,1,1])
        prob=op('Product',[ex,inverse],[1,heads,1,context],shift=16)
        y=op('Dot',[prob,vc],[1,heads,1,d],length=context,shift=24,kernel='self_attn/MatMul_1',gqa_rows=8,gqa_batches=2)
        y=dot(y,f'o{layer}',h,h);x=op('Add',[saved,y],[1,1,h]);saved=x;z=norm(x,f'norm-ffn{layer}')
        gate=dot(z,f'gate{layer}',f,h);up=dot(z,f'up{layer}',f,h)
        # Account for a degree-20 Horner service: 20 multiplies, 20 adds,
        # and final gate multiply per four-lane packet, plus scratch traffic.
        # Coefficients/numerical approximation remain unqualified.
        a=op('SiLU',[gate,coefficients],[1,1,f])
        mid=op('Product',[a,up],[1,1,f],shift=16)
        y=dot(mid,f'down{layer}',h,f);x=op('Add',[saved,y],[1,1,h])
    x=norm(x,'final-norm');dot(x,'lm-head',vocab,h)
    # An initial runtime KV object is resident in DRAM, not a static weight.
    return fmt,nodes

def main():
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,default=SOURCE);args=p.parse_args()
    out=Path('generated');out.mkdir(exist_ok=True)
    raw=args.source.read_bytes();ir=json.loads(raw);g=ir['primitive_program']
    allowed={'Gather','Convert','NFactor','Product','Constant','Add','Dot','View','SquareSum','Compare','Select','Maximum','Minimum','MaskZero','MaskFloor','NExp','Sum','Max','Mask','Concat'}
    if set(n['op'] for n in g['instructions'])-allowed:raise ValueError('unhandled integer primitive')
    formats={k:{x:v[x] for x in ('bits','shape','exponent') if x in v} for k,v in g['initial_formats'].items()}
    # View shape/axis constants are compile-time control operands. Concrete
    # output shapes are already in the frozen graph; retain only data edges.
    nodes=[dict(n,inputs=n['inputs'][:1] if n['op']=='View' else list(n['inputs'])) for n in g['instructions']]
    for name,meta in g.get('predicates',{}).items():formats[name]={'bits':32,'shape':meta['shape']}
    for n in nodes:
        predicate=n['attributes'].get('predicate_source')
        if predicate and predicate not in n['inputs']:n['inputs'].append(predicate)
    # Token IDs are host/control arguments, not quantized arithmetic tensors.
    known=set(formats)|{n['id'] for n in nodes}
    missing={x for n in nodes for x in n['inputs'] if x not in known}
    if missing-{'input_ids'}:raise ValueError('unbound graph inputs: '+str(missing))
    if 'input_ids' in missing:formats['input_ids']={'bits':64,'shape':[1,2]}
    report={'source':str(args.source),'source_sha256':hashlib.sha256(raw).hexdigest(),'hardware':{k:ir['hardware'][k] for k in ('leaf_inventory','virtual_memory')},'traces':{}}
    report['traces']['prefill2']=write_trace(out/'prefill2.trace',formats,nodes,'actual frozen S32/S16 integer DAG; shape controls specialized, runtime views explicitly materialized; B1/S2 no KV',2)
    for context in (128,512,2048):
        fmt,nodes=decode_graph(context)
        # Override the static flag for runtime KV and forbid offline layout.
        name=f'decode{context}';report['traces'][name]=write_trace(out/(name+'.trace'),fmt,nodes,'configuration-derived decode work/traffic projection; NOT numeric-qualified KV graph',1)
    profile=ir['hardware']['native_leaf_profiles']['measurements']
    report['native_N_profile']={k:v for k,v in profile.items() if k.startswith('N:')}
    (out/'input.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'source_sha256':report['source_sha256'],'traces':report['traces']}))

if __name__=='__main__':main()
