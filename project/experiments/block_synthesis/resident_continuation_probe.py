"""Prove consecutive resident iterations on unchanged native P/E/S RTL.

One begin_case/reset per chain, never per element. Inputs vary each element;
constants/guards/B bank can survive only the emitted predecessor program.
Synthetic source-region fixtures do not qualify full-model execution/time.
"""
import argparse
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
import shutil

from native_pointwise import execute,lower
from resident_continuation import compile_loop
from resident_loop_replay import element
from resident_probe import analyse
from resident_replay import replay
from resident_timing import read_qualification
from row_tile_probe import sha
from verify_resident_continuation import verify


def prepare(origin,out,*,steps=8,width=8):
    if not 3<=steps<=32:raise ValueError('bounded continuation probe extent required')
    timing=read_qualification(origin,[origin/('simulate-'+str(i)+'.log') for i in range(3)])
    original=json.loads((origin/'manifest.json').read_text());out.mkdir(exist_ok=False,parents=True)
    for file in original['sha256']:
        dest=out/file;dest.parent.mkdir(exist_ok=True,parents=True);shutil.copyfile(origin/file,dest)
    # All DUT sources and passive monitors are copied byte-for-byte. Add
    # observer-only SRAM reads for inherited guards: unused lanes need not
    # corrupt the selected arithmetic output, but still have to obey the
    # conservative guard contract. These reads are never external transfers.
    bench_path=out/'tb_resident_probe.sv';bench=bench_path.read_text()
    observer=''' task automatic check_guard(input integer actor,input integer address);
  logic[127:0] observed;
  if(actor==0)access(0,address,0,observed);else u_access(0,address,0,observed);
  if(observed!==128'd0)$fatal(1,"inherited SRAM guard contract changed case=%0d address=%0d",case_id,address);
 endtask
'''
    bench_path.write_text(bench.replace('endmodule',observer+'endmodule'),newline='\n')
    here=Path(__file__).parent
    for name in ('resident_continuation_probe.py','resident_continuation.py','verify_resident_continuation.py',
                 'resident_records.py','resident_replay.py','resident_loop_replay.py','native_pointwise.py',
                 'resident_bounds.py','resident_timing.py'):
        shutil.copyfile(here/name,out/('generator-'+name))
    graphs={}
    for row in original['cases']:
        g=row['graph'];key=json.dumps(g,sort_keys=True)
        if row['scope']=='s32-edge-diagnostic':
            # The old scalar diagnostic reserved one word per object. The
            # new multi-element diagnostic explicitly reserves disjoint arrays.
            g=deepcopy(g)
            for i,o in enumerate(g['objects'].values()):o['external_address']=10_000_000+64*i
        graphs.setdefault(key,g)
    # A minimal scalar widening forces an invariant B bank across elements.
    p={'instructions':[{'id':'widen','op':'Convert','inputs':['x'],'shape':[],
                        'bits':32,'exponent':0,'attributes':{'shift':0}}],
       'outputs':{'out':'widen'},'initial_formats':{'x':{'bits':16,'shape':[]}}}
    g=lower(p,['widen'])
    for i,o in enumerate(g['objects'].values()):o['external_address']=50_000_000+64*i
    graphs['bank-retention-diagnostic']=g
    vectors=[];lines=[];records=[];maxexternal=0;cross_bank=0;guard_marker=None;bank_marker=None
    def vector(value):vectors.append(value);return len(vectors)-1
    edges=(0,1,-1,32767,-32768,-2147483648,2147483647,65535)
    for gi,g in enumerate(graphs.values()):
        loop={'kind':'direct-scalar-or-element-loop-v1','elements':steps,'shape':[steps],
              'sources':{o['tensor']:'scalar' if 'literal' in o else 'element'
                         for o in g['objects'].values() if o['kind']=='external'}}
        for capacity in ('tight','full'):
            actors={'P':{'kind':'M','words':32 if capacity=='tight' else 1024,'stride':8,'load_ticks':20,'store_ticks':22},
                    'U':{'kind':'E','words':3 if capacity=='tight' else 1024,'stride':1,'load_ticks':20,'store_ticks':22}}
            for strategy,w,spill,rank in (('spill',1,True,'copy_cost'),('greedy',1,False,'copy_cost'),
                                         ('future_dp',width,False,'future_copies')):
                sequence=compile_loop(g,loop,actors,0,width=w,spill_all=spill,rank_policy=rank,service_timing=timing)
                verify(g,loop,sequence,actors,0,timing)
                r={'graph':g,'loop':loop,'plan':sequence['programs'][0],'continuation_loop':sequence}
                resolved=[element(r,i) for i in range(steps)]
                addresses=sorted({0}|{o['external_address'] for graph,_ in resolved for o in graph['objects'].values()})
                amap={a:i for i,a in enumerate(addresses)};maxexternal=max(maxexternal,len(addresses))
                cid=len(records);offsets={'P':0 if capacity=='full' else 992,'U':0 if capacity=='full' else 1021}
                lines.append(f'begin_case({cid});\n');session=None;events=[]
                for index,(graph,body) in enumerate(resolved):
                    mark=f'// CONTINUATION_STEP case={cid} index={index}\n';lines.append(mark)
                    if index:
                        for actor,row in body['initial_continuation']['actors'].items():
                            for cell in row['padding']:
                                for offset in range(1,8):
                                    lines.append(f"check_guard({0 if actor=='P' else 1},{cell*8+offset+offsets[actor]});\n")
                    values={}
                    for o in graph['objects'].values():
                        if o['kind']=='external' and 'literal' not in o:
                            v=edges[index%len(edges)];limit=1<<(o['bits']-1)
                            values[(o['tensor'],o['index'])]=max(-limit,min(limit-1,v))
                    actual=replay(graph,body,values,session=session,return_session=True);session=actual['session']
                    gold=execute(graph,values)
                    initial={0:0}
                    for o in graph['objects'].values():
                        if o['kind']=='produced':continue
                        value=o['literal'] if 'literal' in o else values[(o['tensor'],o['index'])]
                        if o['external_address'] in initial and initial[o['external_address']]!=value&0xffffffff:
                            raise ValueError('probe initial external source alias')
                        initial[o['external_address']]=value&0xffffffff
                    for addr,value in sorted(initial.items()):lines.append(f'external_memory[{amap[addr]}]=fixture[{vector(value)}];\n')
                    first_m=next((e for e in body['events'] if e['op']=='M_TERM'),None)
                    if index and first_m:
                        inherited=body['initial_continuation']['actors']['P']['padding']
                        if guard_marker is None and first_m['a']//8 in inherited:
                            guard_marker=(mark,first_m['a']+offsets['P']+1)
                        if first_m['reuse_b']:
                            cross_bank+=1
                            if bank_marker is None:bank_marker=mark
                    def addr(e,key):return e[key]+offsets[e['actor']]
                    for e in body['events']:
                        kind=e['op'];actor=0 if e['actor']=='P' else 1
                        if kind in ('LOAD','LOAD_ZERO'):
                            line=f"load_word({actor},{addr(e,'address')},{amap[e['external_address']]});\n"
                        elif kind=='STORE':
                            line=f"store_word({actor},{addr(e,'address')},{amap[e['external_address']]},{vector(gold[e['record']])});\n"
                        elif kind=='M_TERM':
                            line=f"m_term({addr(e,'a')},{0 if e['reuse_b'] else addr(e,'b')},{int(e['reuse_b'])},{e['k']},{e['coefficient']},{e['scale_shift']},{int(e['clear'])});\n"
                        elif kind=='M_FINAL':
                            line=f"m_final({addr(e,'address')},{e['width']},{e['shift']},{vector(gold[e['record']])});\n"
                        elif kind=='E':
                            args=[v+offsets[e['actor']] for v in e['inputs']]+[0]*(3-len(e['inputs']))
                            line='e_command('+','.join(map(str,[len(e['inputs']),*args,addr(e,'address'),e['opcode'],e['shift'],vector(gold[e['record']])]))+');\n'
                        else:raise ValueError('unknown continuation probe event')
                        lines.append(line);events.append(e)
                work=Counter(n['kind'] for n in g['operations']);total=sequence['totals']
                expected={'loads':total['external_load_words'],'stores':total['external_store_words'],
                          'm':steps*work['M'],'e':steps*work['E']}
                lines.append('end_case('+','.join(map(str,expected.values()))+');\n')
                records.append({'id':cid,'region':gi,'strategy':strategy,'capacity':capacity,'elements':steps,
                                'expected':expected,'sequence':sequence,'graph':g,'loop':loop,'physical_window_offsets':offsets,
                                'plan':{'events':events}})
    if cross_bank<1 or guard_marker is None or bank_marker is None:raise ValueError('probe did not exercise guard/bank continuation')
    cases=''.join(lines);(out/'cases.svh').write_text(cases,newline='\n')
    (out/'vectors.hex').write_text(''.join(f'{v:032x}\n' for v in vectors),newline='\n')
    (out/'vectors_size.svh').write_text(f'localparam integer VECTOR_WORDS={len(vectors)},EXTERNAL_WORDS={maxexternal},CASE_COUNT={len(records)};\n',newline='\n')
    # Separate source files for corruption experiments preserve the positive
    # program. Changing an inherited guard or clearing the B bank must fail.
    mark,address=guard_marker
    (out/'negative-guard.svh').write_text(cases.replace(mark,mark+f"begin logic[127:0] ignored; access(1,{address},128'd1,ignored); end\n",1),newline='\n')
    (out/'negative-bank.svh').write_text(cases.replace(bank_marker,bank_marker+'@(negedge clk);reset=1;repeat(4)@(negedge clk);reset=0;repeat(4)@(negedge clk);\n',1),newline='\n')
    bench=(out/'tb_resident_probe.sv').read_text()
    for kind in ('guard','bank'):
        (out/('tb_negative_'+kind+'.sv')).write_text(bench.replace('`include "cases.svh"','`include "negative-'+kind+'.svh"'),newline='\n')
    files={p.relative_to(out).as_posix():sha(p) for p in out.rglob('*') if p.is_file()}
    manifest={'kind':'native-resident-record-v1','cases':records,'sha256':files,
        'origin_manifest_sha256':sha(origin/'manifest.json'),'origin_timing':timing,
        'cross_iteration_B_bank_reuse':cross_bank,
        'guard_observation':'inherited guards are read independently before each warm body, including unused arithmetic lanes; observer cycles are excluded from service slots',
        'scope':'unchanged P/M/feeder/E/S, multiple consecutive finite-S elements per reset, actual ACK/held responses and varying synthetic operands',
        'excluded':'actual-weight full model, full controller/DMA, SystemC, calibrated system timing/energy/token/s or physical',
        'cycles':'serial diagnostic cycles include held responses and observer reads; not performance'}
    (out/'manifest.json').write_text(json.dumps(manifest,separators=(',',':'))+'\n',newline='\n')
    print(json.dumps({'cases':len(records),'elements':steps*len(records),'cross_bank':cross_bank,'out':str(out)}))


if __name__=='__main__':
    p=argparse.ArgumentParser();s=p.add_subparsers(dest='command',required=True)
    a=s.add_parser('prepare');a.add_argument('origin',type=Path);a.add_argument('out',type=Path)
    a.add_argument('--steps',type=int,default=8);a.add_argument('--width',type=int,default=8)
    a=s.add_parser('analyse');a.add_argument('directory',type=Path);a.add_argument('log',type=Path)
    a=p.parse_args()
    if a.command=='prepare':prepare(a.origin,a.out,steps=a.steps,width=a.width)
    else:analyse(a.directory,a.log)
