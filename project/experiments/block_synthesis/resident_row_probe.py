"""Measure unchanged finite-S multi-row M services, including K2 and S16.

Inputs here are explicitly prepared external words. This qualifies a service,
not free preparation, a complete batched compiler or system performance.
"""
from collections import Counter
import hashlib
import json
from pathlib import Path
import random
import shutil


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def prepare(origin,bank,output,formats):
    from row_tile_probe import BANK_SHA,RTL
    origin=Path(origin);bank=Path(bank);output=Path(output)
    manifest=json.loads((origin/'manifest.json').read_text())
    if sha(bank)!=BANK_SHA:raise ValueError('unqualified SRAM bank')
    formats=sorted(set(tuple(x) for x in formats))
    if not formats or any(w not in (16,32) or type(s)!=int or not 0<=s<=63 for w,s in formats):
        raise ValueError('explicit native final formats required')
    output.mkdir(exist_ok=False)
    for relative in RTL:
        name='rtl/'+relative;source=origin/name
        if sha(source)!=manifest['sha256'][name]:raise ValueError('origin RTL changed: '+name)
        target=output/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
    common=origin/'p_resident_common.svh'
    if sha(common)!=manifest['sha256'][common.name]:raise ValueError('origin handshake source changed')
    shutil.copyfile(common,output/common.name);shutil.copyfile(bank,output/bank.name)
    here=Path(__file__).parent
    for name in ('resident_row_probe.py','tb_resident_row_probe.sv'):shutil.copyfile(here/name,output/name)
    vectors=[];cases=[];rng=random.Random(220200)
    edges=[0,1,-1,32767,-32768,65535,-65536,2147483647,-2147483648]
    def append(values):
        at=len(vectors);vectors.extend(x&((1<<128)-1) for x in values);return at
    def s16(x,i):
        value=(x>>(16*i))&65535;return value-65536 if value>=32768 else value
    for rows in range(1,9):
        for k in (1,2):
            for bits,shift in formats:
                for trial in range(2):
                    # Multiple terms exercise live accumulators, signed scale,
                    # a real B-bank hit, and a later cold B replacement.
                    terms=[(1,1,0),(1,-1,16),(65536 if k==2 else -1,1,0)]
                    data=[[edges[(rr+ti+rows)%len(edges)] if trial==0 else rng.randrange(-(1<<31),1<<31)
                           for rr in range(rows)] for ti in range(len(terms))]
                    gold=[]
                    for rr in range(rows):
                        acc=0
                        for ti,(b,coefficient,scale) in enumerate(terms):
                            a=data[ti][rr]&0xffffffff;b=b&0xffffffff
                            acc+=sum(s16(a,j)*s16(b,j) for j in range(k))*coefficient*(1<<scale)
                            if not -(1<<63)<=acc<1<<63:raise ValueError('probe S64 overflow')
                        q,r=divmod(acc,1<<shift)
                        value=q+int(shift>0 and (2*r>1<<shift or 2*r==1<<shift and q%2))
                        value=max(-(1<<(bits-1)),min((1<<(bits-1))-1,value));gold.append(value&0xffffffff)
                    a_base=append([v&0xffffffff for row in data for v in row])
                    term_base=append([value&0xffffffff for t in terms for value in t])
                    gold_base=append(gold);cid=len(cases)
                    # Exercise accepted aligned endpoints and interleaved banks.
                    abase,bbase,dst=((0,16,512),(248,504,760),(992,976,1016))[cid%3]
                    cases.append({'id':cid,'rows':rows,'k':k,'width':bits,'shift':shift,
                        'terms':terms,'values':data,'gold':gold,'a_base':abase,'b_base':bbase,'dst':dst,
                        'inputbase':a_base,'termbase':term_base,'goldbase':gold_base})
    (output/'vectors.hex').write_text(''.join(f'{x:032x}\n' for x in vectors),newline='\n')
    (output/'vectors_size.svh').write_text(f'localparam integer VECTOR_WORDS={len(vectors)},CASE_COUNT={len(cases)};\n',newline='\n')
    (output/'cases.svh').write_text(''.join('run_row('+','.join(map(str,[c['id'],c['rows'],c['k'],len(c['terms']),
        c['a_base'],c['b_base'],c['dst'],c['inputbase'],c['termbase'],c['goldbase'],c['width'],c['shift']]))+');\n' for c in cases),newline='\n')
    (output/'compile.f').write_text('tb_resident_row_probe.sv\n'+''.join('rtl/'+x+'\n' for x in RTL if x.endswith('.sv'))+bank.name+'\n',newline='\n')
    frozen={p.relative_to(output).as_posix():sha(p) for p in output.rglob('*') if p.is_file()}
    result={'kind':'native-resident-row-services-v1','cases':cases,'formats':[list(f) for f in formats],
        'sha256':frozen,'origin_manifest_sha256':sha(origin/'manifest.json'),
        'scope':'unchanged P/M/feeder/16KiB S, explicit prepared words, multi-row K1/K2 and final S16/S32 SRAM ACK',
        'excluded':'preparation, cross-S paths, compiler mapping, MC/LC/DMA/SystemC, DRAM, physical, energy and token/s'}
    (output/'manifest.json').write_text(json.dumps(result,indent=2)+'\n');return result


def analyse(directory,log):
    directory=Path(directory);raw=Path(log).read_bytes();m=json.loads((directory/'manifest.json').read_text())
    if m['kind']!='native-resident-row-services-v1':raise ValueError('wrong row service manifest')
    for name,value in m['sha256'].items():
        if sha(directory/name)!=value:raise ValueError('row input changed: '+name)
    if raw.count(b'PASS native resident row services')!=1 or b'FATAL' in raw:raise ValueError('row probe did not pass')
    def records(prefix):
        return [json.loads(line[len(prefix):]) for line in raw.splitlines() if line.startswith(prefix)]
    rows=records(b'ROW_CASE ');profiles=records(b'ROW_PROFILE ')
    if len(rows)!=len(m['cases']):raise ValueError('row case count differs')
    expected_profiles=Counter()
    for case,observed in zip(m['cases'],rows):
        r=case['rows'];terms=case['terms'];cold=sum(i==0 or t[0]!=terms[i-1][0] for i,t in enumerate(terms))
        needed={'id':case['id'],'a_fires':r*len(terms),'b_fires':2*cold,
                'wide_reads':2*cold+len(terms)*((r+3)//4),'write_acks':r}
        if any(observed.get(k)!=v for k,v in needed.items()) or observed.get('cycles',0)<1:
            raise ValueError('row native counters differ')
        expected_profiles.update({('P',r,0):len(terms),('P',r,case['k']):len(terms),
            ('P',r,64+(1 if case['width']==16 else 2)*64+case['shift']):r,
            ('feeder',r,0):cold,('feeder',r,1):len(terms)-cold})
    seen={};values={'P':{},'feeder':{}}
    for p in profiles:
        key=(p['boundary'],p['rows'],p['key'])
        if key in seen or p['min']<1 or p['min']!=p['max']:raise ValueError('row service profile varies or duplicates')
        seen[key]=p['samples'];values[p['boundary']].setdefault(str(p['rows']),{})[str(p['key'])]=p['max']+1
    if seen!=dict(expected_profiles):raise ValueError('row profile coverage differs')
    return {'passed':True,'cases':len(rows),'records':rows,'profile':values,'manifest_sha256':sha(directory/'manifest.json'),
            'log_sha256':sha(log),'scope':m['scope'],'excluded':m['excluded']}


def qualification(directory,logs):
    if len(logs)!=3 or len({Path(p).resolve() for p in logs})!=3:raise ValueError('three distinct SRAM states required')
    reports=[analyse(directory,p) for p in logs]
    if any(r['profile']!=reports[0]['profile'] for r in reports[1:]):raise ValueError('row service depends on SRAM initial state')
    m=json.loads((Path(directory)/'manifest.json').read_text())
    return {'kind':'native-resident-row-services-v1','profile':reports[0]['profile'],'formats':m['formats'],
        'rtl_sha256':{k:v for k,v in m['sha256'].items() if k.startswith('rtl/')},
        'proof':{'manifest_sha256':reports[0]['manifest_sha256'],'logs_sha256':[r['log_sha256'] for r in reports],
                 'cases_per_initialization':[r['cases'] for r in reports]},'scope':m['scope'],'excluded':m['excluded']}
