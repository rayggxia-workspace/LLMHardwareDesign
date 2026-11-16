"""Conditional-reuse programs on frozen real P/M/feeder/E/16KiB-S RTL.

REUSE/DISCARD are compiler metadata, not arithmetic or data delivery. Extra
reads only observe retained words. All output commits use real SRAM reads.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import shutil

from native_pointwise import execute,lower
from native_reuse import rewrite,verify
from resident_probe import analyse,fixture_program
from resident_records import plan
from resident_replay import replay
from resident_survey import reference
from resident_timing import audit
from row_tile_probe import sha


def prepare(origin,boundary,irfile,regionsfile,out):
    analyse(origin,origin/'simulate-0-run1.log',write_summary=False)
    old=json.loads((origin/'manifest.json').read_text());out.mkdir(parents=True,exist_ok=False)
    for f in old['sha256']:
        target=out/f;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(origin/f,target)
    timing=old['origin_timing'];programs=json.loads((boundary/'programs.json').read_text())
    ir=json.loads(irfile.read_text());graphs=[g for r in json.loads(regionsfile.read_text()) for g in r['graphs']]
    fixtures=json.loads((irfile.parents[2]/'resident-boundary-program-terminal-r16/generated/actual-boundary-fixtures.json').read_text())
    reusable=[i for i,g in enumerate(graphs) if any(n.get('reuse_of') for n in rewrite(g)['operations'])]
    selected={max(reusable,key=lambda i:len(graphs[i]['operations'])),min(reusable,key=lambda i:len(graphs[i]['operations']))}
    cases=[]
    for f in fixtures:
        if f['region_index'] not in selected:continue
        gi=f['region_index'];cases.append((graphs[gi],{(n,i):v for n,i,v in f['inputs']},
            programs[str(gi)]['plans'],{'kind':'actual-weight-boundary','sample':f['sample'],'region':gi}))
    p=fixture_program();g=lower(p,[n['id'] for n in p['instructions']])
    for i,o in enumerate(g['objects'].values()):o['external_address']=50_000_000+i
    r=rewrite(g);actors={'P':{'kind':'M','words':32,'stride':8,'load_ticks':20,'store_ticks':22},
                        'U':{'kind':'E','words':3,'stride':1,'load_ticks':20,'store_ticks':22}}
    diagnostics={name:plan(r if shared else g,actors,0,width=w,rank_policy=rank,service_timing=timing)
        for name,w,rank,shared in (('original_future_greedy',1,'future_copies',False),
            ('reuse_future_greedy',1,'future_copies',True),('reuse_dp',8,'copy_cost',True))}
    for v in (0,1,-1,32767,-32768,-2147483648,2147483647,65535):
        values={(o['tensor'],o['index']):max(-(1<<(o['bits']-1)),min((1<<(o['bits']-1))-1,v))
                for o in g['objects'].values() if o['kind']=='external' and 'literal' not in o}
        cases.append((g,values,diagnostics,{'kind':'s32-edge','value':v}))
    alias_program={'instructions':[{'id':name,'op':'Convert','inputs':['x'],'shape':[],
        'bits':32,'exponent':0,'attributes':{'shift':0}} for name in ('first','second')],
        'outputs':{'a':'first','b':'second'},'initial_formats':{'x':{'bits':16,'shape':[]}}}
    alias=lower(alias_program,['first','second'])
    for i,o in enumerate(alias['objects'].values()):o['external_address']=60_000_000+i
    shared_alias=rewrite(alias)
    alias_plans={name:plan(shared_alias if shared else alias,actors,0,width=w,rank_policy=rank,service_timing=timing)
        for name,w,rank,shared in (('original_future_greedy',1,'future_copies',False),
            ('reuse_future_greedy',1,'future_copies',True),('reuse_dp',8,'copy_cost',True))}
    for v in (-32768,32767):cases.append((alias,{('x',0):v},alias_plans,{'kind':'distinct-original-output-commits','value':v}))
    bench=(out/'tb_resident_probe.sv').read_text()
    observer=''' task automatic check_reuse(input integer actor,input integer address,input integer ext,input integer expected);
  logic[127:0] observed;
  if(actor==2)observed=external_memory[ext];
  else if(actor==0)access(0,address,0,observed);else u_access(0,address,0,observed);
  if(observed!==fixture[expected])$fatal(1,"reused SRAM/backed value changed case=%0d",case_id);
 endtask
 task automatic check_commit(input integer ext,input integer expected);
  if(external_memory[ext]!==fixture[expected])$fatal(1,"original output commit missing case=%0d",case_id);
 endtask
'''
    bench=bench.replace('endmodule',observer+'endmodule');(out/'tb_resident_probe.sv').write_text(bench,newline='\n')
    vectors=[];lines=[];records=[];maxexternal=0;stale=None;commit_marker=None
    def vector(v):vectors.append(v);return len(vectors)-1
    for g,values,bodies,description in cases:
        for strategy in ('original_future_greedy','reuse_future_greedy','reuse_dp'):
            body=bodies[strategy];shared=bool(body.get('value_reuse'));graph=rewrite(g) if shared else g
            if shared:verify(graph,g)
            replay(graph,body,values);audit(body,timing);gold=execute(g,values)
            addresses=sorted({body['zero_address']}|{o['external_address'] for o in g['objects'].values()})
            amap={a:i for i,a in enumerate(addresses)};maxexternal=max(maxexternal,len(addresses));cid=len(records)
            codes={name:0 if a['kind']=='M' else 1 for name,a in body['actors'].items()}
            if sorted(codes.values())!=[0,1]:raise ValueError('probe actor ABI differs')
            if any(a['words']>1024 for a in body['actors'].values()):raise ValueError('probe exceeds physical SRAM')
            offsets={name:(1024-a['words'] if cid%2 else 0) for name,a in body['actors'].items()}
            lines.append(f'begin_case({cid});\n');initial={body['zero_address']:0}
            for o in graph['objects'].values():
                if o['kind']=='produced':continue
                word=(o['literal'] if 'literal' in o else values[(o['tensor'],o['index'])])&0xffffffff
                address=o['external_address']
                if address in initial and initial[address]!=word:raise ValueError('probe external source alias')
                initial[address]=word
            for a,w in initial.items():lines.append(f'external_memory[{amap[a]}]=fixture[{vector(w)}];\n')
            def at(e,k):return e[k]+offsets[e['actor']]
            for ei,e in enumerate(body['events']):
                kind=e['op'];actor=codes[e['actor']]
                if kind in ('LOAD','LOAD_ZERO'):line=f"load_word({actor},{at(e,'address')},{amap[e['external_address']]});\n"
                elif kind in ('STORE','STORE_COMMIT'):
                    line=f"store_word({actor},{at(e,'address')},{amap[e['external_address']]},{vector(gold[e['record']])});\n"
                    if kind=='STORE_COMMIT' and commit_marker is None:commit_marker=line
                elif kind=='M_TERM':line=f"m_term({at(e,'a')},{0 if e['reuse_b'] else at(e,'b')},{int(e['reuse_b'])},{e['k']},{e['coefficient']},{e['scale_shift']},{int(e['clear'])});\n"
                elif kind=='M_FINAL':line=f"m_final({at(e,'address')},{e['width']},{e['shift']},{vector(gold[e['record']])});\n"
                elif kind=='E':
                    args=[x+offsets[e['actor']] for x in e['inputs']]+[0]*(3-len(e['inputs']))
                    line='e_command('+','.join(map(str,[len(e['inputs']),*args,at(e,'address'),e['opcode'],e['shift'],vector(gold[e['record']])]))+');\n'
                elif kind=='REUSE':
                    line=f"check_reuse({actor if e['where']=='S' else 2},{at(e,'address') if e['where']=='S' else 0},{amap[e['external_address']] if e['where']=='external' else 0},{vector(gold[e['record']])});\n"
                    if stale is None and e['where']=='S':stale=(line,actor,at(e,'address'),gold[e['record']])
                elif kind=='DISCARD':line=f'// DISCARD metadata native frontier; word is not read until recomputed: {ei}\n'
                else:raise ValueError('unknown reuse event')
                lines.append(line)
            for primitive,record in g['live_out'].items():
                lines.append(f"check_commit({amap[g['objects'][record]['external_address']]},{vector(gold[record])});\n")
            work=Counter(e['op'] for e in body['events'])
            expected={'loads':body['external_load_words'],'stores':body['external_store_words'],'m':work['M_FINAL'],'e':work['E']}
            if expected['m']+expected['e']+work['REUSE']!=len(g['operations']):raise ValueError('logical native work lost')
            lines.append('end_case('+','.join(map(str,expected.values()))+');\n')
            records.append({'id':cid,'description':description,'strategy':strategy,'expected':expected,
                'graph':graph,'original_graph':g,'values':[[n,i,v] for (n,i),v in values.items()],
                'plan':body,'logical_native_operations':len(g['operations']),'reused_operations':work['REUSE'],
                'physical_window_offsets':offsets})
    if stale is None or commit_marker is None:raise ValueError('probe lacks retained-word/alias-commit negative coverage')
    cases=''.join(lines);(out/'cases.svh').write_text(cases,newline='\n')
    line,actor,address,value=stale
    corruption=f"begin logic[127:0] ignored; {'access' if actor==0 else 'u_access'}(1,{address},128'h{value^1:032x},ignored); end\n"
    for kind,negative in (('stale',cases.replace(line,corruption+line,1)),('commit',cases.replace(commit_marker,'// injected omitted original commit\n',1))):
        (out/('negative-'+kind+'.svh')).write_text(negative,newline='\n')
        (out/('tb_negative_'+kind+'.sv')).write_text(bench.replace('`include "cases.svh"','`include "negative-'+kind+'.svh"'),newline='\n')
    (out/'vectors.hex').write_text(''.join(f'{v:032x}\n' for v in vectors),newline='\n')
    (out/'vectors_size.svh').write_text(f'localparam integer VECTOR_WORDS={len(vectors)},EXTERNAL_WORDS={maxexternal},CASE_COUNT={len(records)};\n',newline='\n')
    here=Path(__file__).parent
    for name in ('native_reuse_probe.py','native_reuse.py','resident_records.py','resident_bounds.py','resident_replay.py','resident_timing.py'):
        shutil.copyfile(here/name,out/('reuse-generator-'+name))
    files={f.relative_to(out).as_posix():sha(f) for f in out.rglob('*') if f.is_file()}
    manifest={'kind':'native-resident-record-v1','cases':records,'sha256':files,'origin_timing':timing,
        'origin_sha256':sha(origin/'manifest.json'),'input_sha256':{str(f):sha(f) for f in (boundary/'programs.json',irfile,regionsfile)},
        'scope':'actual-weight boundary and synthetic S32 conditional reuse/recompute programs on frozen P/M/feeder/E/S, all original output commits',
        'excluded':'full model/MC/LC/DMA/physical/SystemC/energy/token/s','cycles':'observer reads and held responses included; not performance'}
    (out/'manifest.json').write_text(json.dumps(manifest,separators=(',',':'))+'\n');print(json.dumps({'cases':len(records),'selected_regions':sorted(selected)}))


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('origin','boundary','ir','regions','out'):p.add_argument(n,type=Path)
    a=p.parse_args();prepare(a.origin,a.boundary,a.ir,a.regions,a.out)
