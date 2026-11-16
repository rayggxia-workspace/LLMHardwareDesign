"""Diagnose repeated identical native expressions, without changing a plan.

Signatures preserve operation order, integer widths/shifts, saturation and
every M term/coefficient. Only IDs/provenance and already-proven input aliases
are normalized. Native command reuse still needs a separately qualified
allocator, all required external output commits and independent source audit.
"""
from collections import Counter
from copy import deepcopy
import argparse
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path('project/experiments/block_synthesis').resolve()))
from native_pointwise import execute,counts
from resident_survey import reference


def diagnose(graph):
    aliases={};seen={};kept=[];duplicates=Counter()
    for n in graph['operations']:
        signature={k:v for k,v in n.items() if k not in ('id','output','primitive')}
        signature['inputs']=[aliases.get(x,x) for x in n['inputs']]
        if n['kind']=='M':
            signature['terms']=[{**t,'a':aliases.get(t['a'],t['a']),'b':aliases.get(t['b'],t['b'])} for t in n['terms']]
        key=json.dumps(signature,sort_keys=True,separators=(',',':'))
        if key in seen:
            aliases[n['output']]=seen[key];duplicates[n['kind']]+=1
        else:
            aliases[n['output']]=n['output'];seen[key]=n['output']
            kept.append({**n,**signature})
    reduced={**graph,'operations':kept,
             'live_out':{n:aliases.get(x,x) for n,x in graph['live_out'].items()},
             'primitive_outputs':{n:aliases.get(x,x) for n,x in graph['primitive_outputs'].items()}}
    return reduced,aliases,dict(duplicates)


def main():
    p=argparse.ArgumentParser();p.add_argument('ir',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
    a.output.mkdir(exist_ok=False);ir=json.loads(a.ir.read_text());groups={}
    for r in ir['resident_recipes'].values():groups.setdefault(tuple(r['primitives']),r)
    rows=[]
    for ri,r in enumerate(sorted(groups.values(),key=lambda r:len(r['graph']['operations']),reverse=True)[:2]):
        graph=r['graph'];reduced,aliases,duplicates=diagnose(graph);cases=0
        for value in (0,1,-1,32767,-32768,2147483647,-2147483648):
            inputs={}
            for o in graph['objects'].values():
                if o['kind']=='external' and 'literal' not in o:
                    inputs[o['tensor'],o['index']]=max(-(1<<(o['bits']-1)),min((1<<(o['bits']-1))-1,value))
            original=execute(graph,inputs);actual=execute(reduced,inputs)
            source=reference(ir['primitive_program'],graph,inputs)
            for n in graph['operations']:
                if original[n['output']]!=actual[aliases[n['output']]]:raise ValueError('diagnostic expression reuse changed a native result')
            for name,record in graph['primitive_outputs'].items():
                raw=original[record]&0xffffffff;signed=raw-(1<<32) if raw&(1<<31) else raw
                if signed!=source[name]:raise ValueError('diagnostic native/source result differs')
            cases+=1
        row={'region':ri,'primitives':r['primitives'],'original_operations':len(graph['operations']),
             'unique_expressions':len(reduced['operations']),'duplicates_by_kind':duplicates,
             'original_native_counts':counts(graph),'reduced_expression_counts':counts(reduced),'numeric_cases':cases}
        rows.append(row)
        (a.output/f'region-{ri}.json').write_text(json.dumps({'original':graph,'expression_graph':reduced,'aliases':aliases},separators=(',',':'))+'\n')
    result={'passed':True,'rows':rows,'input_sha256':hashlib.sha256(a.ir.read_bytes()).hexdigest(),
            'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'scope':'structural duplicate expression counts and synthetic integer equivalence only; no allocated/selected program, external alias materialization, performance, actual weights, RTL or system qualification'}
    (a.output/'summary.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))


if __name__=='__main__':main()
