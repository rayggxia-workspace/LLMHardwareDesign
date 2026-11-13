"""Qualify an exact multi-row S32 Add aggregation on unchanged P/M/S RTL.

Starts with explicit external S16 component records, after the existing split32
preparation. Preparation is not free and is not qualified by this probe. No
packing, extra accumulators or inter-macro bypass is assumed.
"""
import argparse
import json
from pathlib import Path
import random
import re
import shutil

from row_tile_probe import BANK_SHA,RTL,sha


def components(value):
    low=(value+32768)%65536-32768
    return low,value>>16,int(low<0)


def prepare(root,bank,out):
    # Reuse the real qualified P/S interface and handshake tasks verbatim.
    from column_tile_probe import analyse as check_origin
    origin=json.loads((root/'manifest.json').read_text())
    if check_origin(root,root/'simulate.log',emit=False)!=json.loads((root/'summary.json').read_text()):
        raise ValueError('origin qualification differs')
    if sha(bank)!=BANK_SHA:raise ValueError('unqualified bank model')
    out.mkdir(parents=True,exist_ok=False)
    for relative in RTL:
        name='rtl/'+relative;source=root/name
        if sha(source)!=origin['sha256'][name]:raise ValueError('origin RTL changed')
        target=out/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
    shutil.copyfile(bank,out/bank.name)
    for file in ('manifest.json','summary.json'):
        shutil.copyfile(root/file,out/('origin-'+file))
    here=Path(__file__).parent
    original=root/'tb_row_tile_probe.sv'
    if sha(original)!=origin['sha256']['tb_row_tile_probe.sv']:raise ValueError('origin handshake source changed')
    old=original.read_text()
    common=old[old.index(' `include "vectors_size.svh"'):old.index(' logic[63:0] inputs_mem')]
    (out/'p_add_common.svh').write_text(common,newline='\n')
    shutil.copyfile(here/'tb_s32_add_probe.sv',out/'tb_s32_add_probe.sv')
    shutil.copyfile(here/'s32_add_probe.py',out/'s32_add_probe.py')
    words=[];cases=[];rng=random.Random(220130)
    edges=[-2147483648,2147483647,-65537,-32769,-32768,-1,0,1,32767,32768,65535,65536]
    for rows in range(1,9):
        for inputs in (2,3,5,17):
            for kind in ('positive-saturate','negative-saturate','cancellation','random'):
                if kind=='positive-saturate':values=[[2147483647]*inputs for _ in range(rows)]
                elif kind=='negative-saturate':values=[[-2147483648]*inputs for _ in range(rows)]
                elif kind=='cancellation':values=[[edges[(j+rr)%len(edges)] for j in range(inputs)] for rr in range(rows)]
                else:values=[[rng.randrange(-(1<<31),1<<31) for _ in range(inputs)] for _ in range(rows)]
                for signs in ([1]*inputs,[-1 if i%2==0 else 1 for i in range(inputs)],[-1]*inputs):
                    start=len(words)
                    # Immutable fixture data is already a declared external
                    # prepared record. Only the low S16 lane is consumed.
                    for operand in range(inputs):
                        for part in range(3):
                            for row in values:words.append(components(row[operand])[part]&65535)
                    signbase=len(words);words.extend(s&65535 for s in signs)
                    gold=len(words);sums=[sum(x*s for x,s in zip(row,signs)) for row in values]
                    words.extend(v&((1<<64)-1) for v in sums)
                    final=len(words);words.extend(min((1<<31)-1,max(-(1<<31),v))&0xffffffff for v in sums)
                    cases.append({'id':len(cases),'rows':rows,'inputs':inputs,'kind':kind,'prepared':start,
                        'gold':gold,'final':final,'values':values,'sums':sums,'signs':signs,'signbase':signbase})
    (out/'vectors.hex').write_text(''.join(f'{w:016x}\n' for w in words),newline='\n')
    (out/'vectors_size.svh').write_text(f'localparam integer VECTOR_WORDS={len(words)};\n',newline='\n')
    (out/'cases.svh').write_text(''.join(f"run_add({c['id']},{c['rows']},{c['inputs']},{c['prepared']},{c['gold']},{c['final']},{c['signbase']});\n" for c in cases),newline='\n')
    (out/'compile.f').write_text('tb_s32_add_probe.sv\n'+''.join('rtl/'+x+'\n' for x in RTL if x.endswith('.sv'))+bank.name+'\n',newline='\n')
    # Overwritten row fixtures are included only in their final form; all
    # active RTL and the exact copied handshake source remain auditable.
    files={p.relative_to(out).as_posix():sha(p) for p in out.rglob('*') if p.is_file() and p.name!='manifest.json'}
    manifest={'kind':'native-s32-add-row-aggregate-v1','cases':cases,'sha256':files,
        'origin_manifest_sha256':sha(root/'manifest.json'),
        'input_abi':'external prepared signed low16/high16/low-negative flag, powers0/16/16',
        'scope':'unchanged P/M/S plus actual feeder, native full sum, final S32 saturation and SRAM ACK',
        'excluded':'split32 preparation cost/RTL, complete compiler/MC/LC/DMA, system cycles, physical or energy'}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',newline='\n')


def analyse(directory,log,*,emit=True):
    manifest=json.loads((directory/'manifest.json').read_text());text=log.read_text()
    if manifest['kind']!='native-s32-add-row-aggregate-v1':raise ValueError('unexpected Add probe')
    for file,expected in manifest['sha256'].items():
        if sha(directory/file)!=expected:raise ValueError('Add input changed '+file)
    if text.count('PASS native S32 Add row aggregate')!=1 or 'FATAL' in text:raise ValueError('Add probe not passed')
    records=[json.loads(m[1]) for m in re.finditer(r'^ADD_CASE (\{.*\})$',text,re.MULTILINE)]
    if len(records)!=len(manifest['cases']):raise ValueError('Add case coverage differs')
    for expected,actual in zip(manifest['cases'],records):
        r,n=expected['rows'],expected['inputs']
        needed={'id':expected['id'],'a_fires':3*n*r,'b_fires':2,'wide_reads':2+3*n*((r+3)//4),'write_acks':r}
        if any(actual.get(k)!=v for k,v in needed.items()):raise ValueError('Add native counts differ')
        if actual['cycles']<=0:raise ValueError('invalid Add cycles')
    profiles=[json.loads(m[1]) for m in re.finditer(r'^ADD_PROFILE (\{.*\})$',text,re.MULTILINE)]
    if len(profiles)!=8*6:raise ValueError('Add passive profile coverage differs')
    for r in range(1,9):
        cases=[c for c in manifest['cases'] if c['rows']==r];commands=sum(3*c['inputs'] for c in cases)
        expected={('p-command',4,0,None):commands,('p-command',10,0,None):commands,
            ('p-command',3,0,None):r*len(cases),('p-command',5,1,None):r*len(cases),
            ('feeder',None,None,0):len(cases),('feeder',None,None,1):commands-len(cases)}
        observed={}
        for p in profiles:
            if p['rows']!=r:continue
            key=(p['boundary'],p.get('op'),p.get('store'),p.get('reuse_b'))
            if key in observed or p['min']!=p['max'] or p['min']<1:raise ValueError('nonconstant/duplicate Add profile')
            observed[key]=p['samples']
        if observed!=expected:raise ValueError('Add profile sample counts differ')
    result={'passed':True,'cases':len(records),'rows':list(range(1,9)),'input_counts':[2,3,5,17],
        'manifest_sha256':sha(directory/'manifest.json'),'log_sha256':sha(log),
        'records':records,'passive_profiles':profiles,'scope':manifest['scope'],'excluded':manifest['excluded']}
    if emit:
        (directory/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps({k:v for k,v in result.items() if k not in ('records','passive_profiles')}))
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='command',required=True)
    a=sub.add_parser('prepare');a.add_argument('root',type=Path);a.add_argument('bank',type=Path);a.add_argument('out',type=Path)
    a=sub.add_parser('analyse');a.add_argument('directory',type=Path);a.add_argument('log',type=Path)
    a=p.parse_args()
    if a.command=='prepare':prepare(a.root,a.bank,a.out)
    else:analyse(a.directory,a.log)
