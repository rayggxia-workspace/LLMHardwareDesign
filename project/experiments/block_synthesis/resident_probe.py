"""Emit finite-S residency events on frozen, unchanged native P/E/S RTL.

The host models acknowledged full-word external transport only. Every high16,
low-negative flag and arithmetic operation must execute in M/E. Synthetic
boundary fixtures and serial probe cycles do not qualify model token/s.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import random
import shutil

from column_tile_probe import EXTRA_RTL,analyse as check_origin
from native_pointwise import execute,lower
from resident_records import plan
from resident_replay import replay
from resident_survey import reference
from row_tile_probe import BANK_SHA,RTL,sha


def fixture_program():
    def n(name,op,args,bits=32,**attrs):
        return {'id':name,'kernel':'resident-probe','op':op,'inputs':args,'shape':[],
                'bits':bits,'exponent':0,'attributes':attrs}
    return {'instructions':[n('a','Add',['x','y','x'],signs=[1,-1,1]),
            n('p','Product',['a','y'],shift=29),n('s','Convert',['p'],bits=16,shift=11),
            n('u','Product',['s','one'],shift=-1),n('z','Add',['u','a'],signs=[-1,1])],
        'outputs':{'out':'z'},'initial_formats':{'x':{'bits':32,'shape':[]},
            'y':{'bits':32,'shape':[]},'one':{'bits':16,'shape':[],'literal':1}}}


def prepare(root,bank,irfile,regionfile,out,*,cases=8,width=8):
    origin=json.loads((root/'manifest.json').read_text())
    if check_origin(root,root/'simulate.log',emit=False)!=json.loads((root/'summary.json').read_text()):
        raise ValueError('frozen native origin qualification differs')
    if sha(bank)!=BANK_SHA:raise ValueError('unqualified SRAM bank')
    if not 1<=cases<=12 or width<1:raise ValueError('invalid bounded resident probe')
    out.mkdir(parents=True,exist_ok=False)
    for relative in RTL+EXTRA_RTL:
        name='rtl/'+relative;source=root/name
        if sha(source)!=origin['sha256'][name]:raise ValueError('native RTL changed '+name)
        dest=out/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,dest)
    shutil.copyfile(bank,out/bank.name)
    for name in ('manifest.json','summary.json','tb_row_tile_probe.sv'):
        shutil.copyfile(root/name,out/('origin-'+name))
    row=root/'tb_row_tile_probe.sv'
    if sha(row)!=origin['sha256'][row.name]:raise ValueError('native P handshake source changed')
    original=row.read_text();common=original[original.index(' `include "vectors_size.svh"'):original.index(' logic[63:0] inputs_mem')]
    for old,new in (('.load_a_base(10\'d0)','.load_a_base(load_a_address)'),
                    ('.load_b_base(10\'d16)','.load_b_base(load_b_address)')):
        if common.count(old)!=1:raise ValueError('unexpected native feeder interface')
        common=common.replace(old,new)
    common=common.replace(' logic [3:0] rows=1;',' logic [3:0] rows=1;\n logic[9:0] load_a_address=0,load_b_address=0;')
    (out/'p_resident_common.svh').write_text(common,newline='\n')
    here=Path(__file__).parent
    sources=['resident_probe.py','tb_resident_probe.sv','native_pointwise.py','resident_records.py',
             'resident_bounds.py','resident_replay.py','resident_survey.py']
    for name in sources:shutil.copyfile(here/name,out/name)
    ir=json.loads(irfile.read_text());rs=json.loads(regionfile.read_text());zero=ir['native_constants']['0']['address_words']
    graphs=[(r['graphs'][0],ir['primitive_program'],'source-closed-ffn') for r in rs]
    p=fixture_program();g=lower(p,[n['id'] for n in p['instructions']])
    # The synthetic diagnostic has its own explicitly reserved backing region.
    for i,o in enumerate(g['objects'].values()):o['external_address']=10_000_000+i
    graphs.append((g,p,'s32-edge-diagnostic'))
    vectors=[];lines=[];records=[];maxexternal=0;rng=random.Random(220144)
    def vector(value):
        if not 0<=value<1<<128:raise ValueError('fixture word outside 128 bits')
        vectors.append(value);return len(vectors)-1
    for gi,(graph,program,scope) in enumerate(graphs):
        # Small physical windows deliberately exercise replacement; actual
        # accepted banks stay 16KiB, and no event may use an address above it.
        actors={'P':{'kind':'M','words':32,'stride':8,'load_ticks':20,'store_ticks':22},
                'U':{'kind':'E','words':3,'stride':1,'load_ticks':20,'store_ticks':22}}
        candidates={name:plan(graph,actors,zero,width=w,spill_all=spill,rank_policy=rank)
            for name,w,spill,rank in (('spill',1,True,'copy_cost'),('greedy',1,False,'copy_cost'),
                                     ('future_dp',width,False,'future_copies'))}
        if any(v['status']!='planned' for v in candidates.values()):raise ValueError('resident qualification needs a legal finite-S plan')
        addresses=sorted({zero}|{o['external_address'] for o in graph['objects'].values()})
        amap={a:i for i,a in enumerate(addresses)};maxexternal=max(maxexternal,len(addresses))
        for trial in range(cases):
            values={}
            for o in graph['objects'].values():
                if o['kind']!='external' or 'literal' in o:continue
                edges=(0,1,-1,32767,-32768,-2147483648,2147483647)
                raw=edges[trial] if scope=='s32-edge-diagnostic' and trial<len(edges) else (
                    edges[trial] if trial<5 else rng.randrange(-(1<<20),1<<20))
                if o['bits']==16:raw=max(-32768,min(32767,raw))
                values[(o['tensor'],o['index'])]=raw
            gold=execute(graph,values);ref=reference(program,graph,values)
            for name,key in graph['primitive_outputs'].items():
                v=gold[key]&0xffffffff;actual=v-(1<<32) if v&(1<<31) else v
                if actual!=ref[name]:raise ValueError('original pointwise integer reference differs')
            for name,candidate in candidates.items():
                replay(graph,candidate,values)
                offsets={'P':(0,248,504,760,992)[trial%5],'U':(0,254,510,766,1021)[trial%5]}
                def address(event,key):
                    value=event[key]+offsets[event['actor']]
                    if not 0<=value<1024:raise ValueError('native resident address outside physical S')
                    return value
                cid=len(records);lines.append(f'begin_case({cid});\n')
                initial={zero:0}
                for key,o in graph['objects'].items():
                    if o['kind']=='produced':continue
                    raw=o['literal'] if 'literal' in o else values[(o['tensor'],o['index'])]
                    addr=o['external_address'];word=raw&0xffffffff
                    if addr in initial and initial[addr]!=word:raise ValueError('conflicting external fixtures')
                    initial[addr]=word
                for addr,word in sorted(initial.items()):lines.append(f'external_memory[{amap[addr]}]=fixture[{vector(word)}];\n')
                for event in candidate['events']:
                    kind=event['op'];actor=0 if event['actor']=='P' else 1
                    if kind in ('LOAD','LOAD_ZERO'):
                        lines.append(f"load_word({actor},{address(event,'address')},{amap[event['external_address']]});\n")
                    elif kind=='STORE':
                        lines.append(f"store_word({actor},{address(event,'address')},{amap[event['external_address']]},{vector(gold[event['record']])});\n")
                    elif kind=='M_TERM':
                        lines.append(f"m_term({address(event,'a')},{0 if event['reuse_b'] else address(event,'b')},{int(event['reuse_b'])},{event['k']},{event['coefficient']},{event['scale_shift']},{int(event['clear'])});\n")
                    elif kind=='M_FINAL':
                        lines.append(f"m_final({address(event,'address')},{event['width']},{event['shift']},{vector(gold[event['record']])});\n")
                    elif kind=='E':
                        args=[x+offsets[event['actor']] for x in event['inputs']]+[0]*(3-len(event['inputs']))
                        if any(not 0<=x<1024 for x in args):raise ValueError('native E source outside physical S')
                        lines.append('e_command('+','.join(map(str,[len(event['inputs']),*args,address(event,'address'),event['opcode'],event['shift'],vector(gold[event['record']])]))+');\n')
                    else:raise ValueError('unqualified resident event')
                counts=Counter(n['kind'] for n in graph['operations'])
                expect={'loads':candidate['external_load_words'],'stores':candidate['external_store_words'],
                        'm':counts['M'],'e':counts['E']}
                lines.append('end_case('+','.join(map(str,expect.values()))+');\n')
                records.append({'id':cid,'region':gi,'primitives':graph['primitives'],'trial':trial,
                    'strategy':name,'scope':scope,'expected':expect,'copy_ticks':candidate['copy_ticks'],
                    'actors':actors,'physical_window_offsets':offsets,
                    'external_addresses':addresses,'values':[[n,i,v] for (n,i),v in values.items()],
                    'graph':graph,'plan':candidate})
    (out/'vectors.hex').write_text(''.join(f'{v:032x}\n' for v in vectors),newline='\n')
    (out/'vectors_size.svh').write_text(f'localparam integer VECTOR_WORDS={len(vectors)},EXTERNAL_WORDS={maxexternal},CASE_COUNT={len(records)};\n',newline='\n')
    (out/'cases.svh').write_text(''.join(lines),newline='\n')
    (out/'compile.f').write_text('tb_resident_probe.sv\n'+''.join('rtl/'+x+'\n' for x in RTL+EXTRA_RTL if x.endswith('.sv'))+bank.name+'\n',newline='\n')
    files={p.relative_to(out).as_posix():sha(p) for p in out.rglob('*') if p.is_file()}
    manifest={'kind':'native-resident-record-v1','cases':records,'sha256':files,
        'input_sha256':{'ir':sha(irfile),'regions':sha(regionfile),'origin':sha(root/'manifest.json')},
        'scope':'unchanged P/M/feeder/S and compact E/S; real K1/K2, high16 extraction, Min/Select, arbitrary finite addresses, S write ACK and held responses',
        'excluded':'actual-weight full-model numeric, common scheduler candidate registration, MC/LC/DMA timing, physical, SystemC, energy, token/s',
        'cycles':'serial observation includes deliberately held completions and extra SRAM result reads; not calibrated performance'}
    (out/'manifest.json').write_text(json.dumps(manifest,separators=(',',':'))+'\n',newline='\n')


def analyse(directory,log,*,write_summary=True):
    # Icarus emits ASCII JSON. Parse those bytes directly, preserving the raw
    # log hash even when WSL also writes a non-UTF8 launcher diagnostic.
    manifest=json.loads((directory/'manifest.json').read_text());content=log.read_bytes()
    if manifest['kind']!='native-resident-record-v1':raise ValueError('unexpected resident probe')
    for file,expected in manifest['sha256'].items():
        if sha(directory/file)!=expected:raise ValueError('resident probe source changed '+file)
    if content.count(b'PASS native resident record programs')!=1 or b'FATAL' in content:
        raise ValueError('resident native program did not pass')
    prefix=b'RESIDENT_CASE '
    rows=[json.loads(line.lstrip(b'\0')[len(prefix):]) for line in content.split(b'\n')
          if line.lstrip(b'\0').startswith(prefix)]
    if len(rows)!=len(manifest['cases']):raise ValueError('resident case coverage differs')
    for actual,case in zip(rows,manifest['cases']):
        if actual['id']!=case['id'] or actual['cycles']<1 or any(actual[k]!=v for k,v in case['expected'].items()):
            raise ValueError('resident native event counts differ')
    profile_prefix=b'RESIDENT_PROFILE '
    profiles=[json.loads(line.lstrip(b'\0')[len(profile_prefix):]) for line in content.split(b'\n')
              if line.lstrip(b'\0').startswith(profile_prefix)]
    expected=Counter()
    for case in manifest['cases']:
        for event in case.get('plan',{}).get('events',[]):
            if event['op']=='M_TERM':
                expected[('P',0)]+=1;expected[('P',1+event['k'])]+=1
                expected[('feeder',int(event['reuse_b']))]+=1
            elif event['op']=='M_FINAL':expected[('P',16+64*(1 if event['width']==16 else 2)+event['shift'])]+=1
            elif event['op']=='E':expected[('E',event['opcode']+16*len(event['inputs'])+64*event['shift'])]+=1
    observed={}
    for row in profiles:
        key=(row['boundary'],row['key'])
        if key in observed or not 0<row['min']<=row['max']:raise ValueError('invalid resident passive profile')
        observed[key]=row['samples']
    # Old protocol-only evidence has no profiles; it remains readable but
    # cannot be used to construct the new measured-time service contract.
    if profiles and observed!=dict(expected):raise ValueError('resident profile sample coverage differs')
    result={'passed':True,'cases':len(rows),'records':rows,'manifest_sha256':sha(directory/'manifest.json'),
        'log_sha256':sha(log),'passive_profiles':profiles,
        'scope':manifest['scope'],'excluded':manifest['excluded'],'cycles':manifest['cycles']}
    if write_summary:
        (directory/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps({k:v for k,v in result.items() if k!='records'}))
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='command',required=True)
    a=sub.add_parser('prepare')
    for name in ('root','bank','ir','regions','out'):a.add_argument(name,type=Path)
    a.add_argument('--cases',type=int,default=8);a.add_argument('--width',type=int,default=8)
    a=sub.add_parser('analyse');a.add_argument('directory',type=Path);a.add_argument('log',type=Path)
    a=p.parse_args()
    if a.command=='prepare':prepare(a.root,a.bank,a.ir,a.regions,a.out,cases=a.cases,width=a.width)
    else:analyse(a.directory,a.log)
