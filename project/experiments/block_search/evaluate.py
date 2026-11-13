"""Slurm evaluation driver; explicit analytical hardware scenarios."""
import argparse
from collections import Counter
import copy
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import traceback

from search import compile_graph, import_onnx, Unsupported


def hardware(capacity, ops):
    # This is a research scenario, NOT a reconstructed pin-qualified base.
    # Services are deliberately marked unqualified. No implicit CPU fallback.
    groups = [('P0','M'),('P1','M'),('P2','M'),('U0','N'),('U1','N'),
              ('C0','R'),('F0','G'),('J0','E'),('J1','E')]
    supported = {'M': ['MatMul','Gemm'], 'N': ['ReduceMean','ReduceSum','Softmax','Sqrt','Pow'],
                 'R': ['CumSum'], 'G': ['Sigmoid','Tanh','Erf','Exp'],
                 'E': ['Add','Sub','Mul','Div','Neg','Reciprocal','Where','Max','Min']}
    # Layout/index/coefficient operations lack a qualified fixed-macro recipe.
    # For exploratory scheduling only, place them on U as a declared extension.
    known = {v for values in supported.values() for v in values}
    supported['N'] += sorted(set(ops)-known)
    instances = {name:{'capacity_bytes':capacity,'kind':kind} for name,kind in groups}
    services = [{'id':name+'.'+kind, 'instance':name, 'ops':supported[kind],
                 'dtypes':['FLOAT','FLOAT16','BFLOAT16','INT64','INT32','BOOL'],
                 'resources':[name+'.compute',name+'.lc',name+'.s'],
                 'work_per_cycle':4096 if kind=='M' else 16,
                 'setup_cycles':8, 'workspace_bytes':128,'weight_window_bytes':1024,
                 'evidence':'hypothetical FP32 cost/recipe; not qualified macro ISA'}
                for name,kind in groups]
    links=[]
    for i,(src,dst) in enumerate((a,b) for a in ['MEM']+list(instances)
                                for b in instances if a!=b):
        links.append({'id':src+'->'+dst,'src':src,'dst':dst,
                      'resources':[src+'.tx',dst+'.rx',dst+'.s']+
                                  ([src+'.s'] if src!='MEM' else ['MEM.bandwidth']),
                      'bytes_per_cycle':16,'latency_cycles':4,
                      'static_cost':128+3+abs(i%9-i//9)*4,
                      'fixed':src=='MEM','enabled':True})
    return {'instances':instances,'services':services,'links':links,
            'external_memory':'MEM','qualified_numeric':False,
            'route_candidates':1,'route_combinations':1,
            'evidence':'Analytical nine-control-group scenario. Native endpoint reachability, FP32 recipes, cost/ISA and physical electrical closure unqualified.',
            'extension_ops':sorted(set(ops)-known)}


def dump(path,obj):
    path.write_text(json.dumps(obj,ensure_ascii=False,indent=2))


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('root',type=Path)
    parser.add_argument('output',type=Path)
    parser.add_argument('--full',type=Path)
    a=parser.parse_args()
    a.output.mkdir(parents=True,exist_ok=False)
    paths=sorted(a.root.glob('results/native*/**/simplified.onnx'))
    # Latest successful native export per layer kind.
    latest={p.parent.name:p for p in paths}
    if a.full and a.full.exists():
        latest['full-qwen3']=a.full/'full.onnx'
    results=[]
    for name,path in latest.items():
        try:
            receipt=path.parent/'receipt.json'
            weights=json.loads(receipt.read_text()).get('parameters',{}) if name.startswith('full-') else ()
            graph=import_onnx(path,weights)
            dump(a.output/(name+'.graph.json'),graph)
            ops=Counter(t['op'] for t in graph['tasks'])
            for capacity in [16384,4*1024*1024]:
                arch=hardware(capacity,ops)
                dump(a.output/(name+f'.hardware-{capacity}.json'),arch)
                for width in ([1,4] if name.startswith('full-') else [1,4,16]):
                    label=f'{name}-s{capacity}-b{width}'
                    try:
                        plan=compile_graph(graph,arch,width,1.,allow_estimates=True)
                    except Unsupported as error:
                        plan={'status':'unsupported','reason':str(error)}
                    dump(a.output/(label+'.plan.json'),plan)
                    results.append({'case':label,'model':name,'capacity_bytes':capacity,'width':width,
                                    'tasks':len(graph['tasks']),'ops':dict(ops),
                                    'status':plan['status'],
                                    **{k:plan[k] for k in ['latency_cycles','static_cost','seconds','statistics','at','reason'] if k in plan},
                                    'extension_ops':arch['extension_ops']})
                    dump(a.output/'summary.json',results)
                    print(json.dumps(results[-1]),flush=True)
        except Exception as error:
            results.append({'model':name,'status':'frontend_failed','reason':str(error),'traceback':traceback.format_exc()})
            dump(a.output/'summary.json',results)
            print(json.dumps(results[-1]),flush=True)
    dump(a.output/'run.json',{'python':platform.python_version(),
                            'hostname':platform.node(),
                            'scope':'analytical mapping/scheduling only; complete graph where named full-qwen3; remaining inputs are decoder layers',
                            'source_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest()
                                             for p in Path(__file__).parent.glob('*.py')}})


if __name__=='__main__':
    main()
