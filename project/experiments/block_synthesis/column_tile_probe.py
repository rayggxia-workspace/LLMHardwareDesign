"""Unchanged native M/E/S path: multi-column Dot followed by real S32 scatter.

Complete-word host transport models explicitly required copies between private
stores. It supplies neither CPU arithmetic nor calibrated DMA/LC timing.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import random
import re
import shutil
import subprocess

from row_tile_probe import BANK_SHA, RTL, final_s32, sha


EXTRA_RTL = ['block_v2/block_v2_e.sv', 'block_v2/block_v2_e_compact.sv',
             'pu_leaf_base/pu_compact_e_service.sv']


def prepare(source_root, bank_model, output, rtl_ref, long_k=0):
    if sha(bank_model) != BANK_SHA:
        raise ValueError('unqualified SRAM bank model')
    output.mkdir(parents=True, exist_ok=False)
    sources = {}
    for relative in RTL+EXTRA_RTL:
        original = source_root/'project/rtl'/relative
        reference = subprocess.check_output(['git', 'show', rtl_ref+':project/rtl/'+relative],
                                            cwd=source_root)
        if original.read_bytes().replace(b'\r\n',b'\n') != reference.replace(b'\r\n',b'\n'):
            raise ValueError('RTL differs from requested frozen reference: '+relative)
        target = output/'rtl'/relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(original, target)
        sources['rtl/'+relative] = sha(target)
    shutil.copyfile(bank_model, output/bank_model.name)
    sources[bank_model.name] = sha(bank_model)
    here = Path(__file__).parent
    for name in ('column_tile_probe.py','tb_column_tile_probe.sv','row_tile_probe.py'):
        shutil.copyfile(here/name, output/name)
        sources[name] = sha(output/name)
    # One source of truth for the existing P/S handshake tasks. Preserve its
    # original frozen source too, so the generated include is reproducible.
    row_bench = (here/'tb_row_tile_probe.sv').read_text()
    start = row_bench.index(' `include "vectors_size.svh"')
    end = row_bench.index(' logic[63:0] inputs_mem')
    common = row_bench[start:end]
    (output/'p_probe_common.svh').write_text(common, newline='\n')
    shutil.copyfile(here/'tb_row_tile_probe.sv',output/'tb_row_tile_probe.sv')
    for name in ('p_probe_common.svh','tb_row_tile_probe.sv'):
        sources[name] = sha(output/name)
    words, cases, groups = [], [], []

    def add(a, b, kind, group):
        r, k, n = len(a), len(b), len(b[0])
        abase = len(words)
        words.extend(x&((1<<64)-1) for row in a for x in row)
        bbase = len(words)
        words.extend(x&((1<<64)-1) for row in b for x in row)
        goldbase = len(words)
        gold = [sum(a[rr][kk]*b[kk][cc] for kk in range(k))
                for rr in range(r) for cc in range(n)]
        if any(not -(1<<63) <= x < (1<<63) for x in gold):
            raise ValueError('S64 golden overflow')
        words.extend(x&((1<<64)-1) for x in gold)
        finalbase = len(words)
        words.extend(final_s32(x,s)&0xffffffff for x in gold for s in (0,8,16,24))
        case = {'id':len(cases),'group':group,'kind':kind,'rows':r,'columns':n,'k':k,
                'a':abase,'b':bbase,'gold':goldbase,'final':finalbase,'golden_s64':gold}
        cases.append(case)
        return case['id']

    shapes = [(1,n,k) for n in range(1,9) for k in (1,3,17)]
    shapes += [(2,4,7),(3,5,3),(5,7,3),(6,8,1),(7,3,7),(8,8,7)]
    if long_k:
        if not 1 <= long_k <= 2048:
            raise ValueError('long K outside finite probe scope')
        shapes.append((2,8,long_k))
    edge_a = [-2147483648,2147483647,-65537,-32769,-32768,-1,0,1,32767,32768,65535,65536]
    edge_b = [-32768,32767,-129,-1,0,1,127,128]
    for group,(r,n,k) in enumerate(shapes):
        rng = random.Random(2207+group)
        a = [[edge_a[(rr*k+kk+group)%len(edge_a)] if kk%3!=2 else
              rng.randint(-(1<<31),(1<<31)-1) for kk in range(k)] for rr in range(r)]
        b = [[edge_b[(kk*n+cc+group)%len(edge_b)] if kk%3!=2 else
              rng.randint(-32768,32767) for cc in range(n)] for kk in range(k)]
        tile = add(a,b,'tile',group)
        # Full numeric golden checks include long K. Serial end-to-end controls
        # use small cases to keep this native protocol probe bounded in runtime.
        serial = [] if k>17 else [add([row],[[bb[cc]] for bb in b],'serial',group)
                                  for row in a for cc in range(n)]
        groups.append({'id':group,'rows':r,'columns':n,'k':k,'tile':tile,'serial':serial})
    # Selected products form exact half-even ties of both signs at shift8.
    group = len(groups)
    a = [[128],[-128],[384],[-384]]
    tile = add(a,[[1,-1,32767,-32768]],'tile',group)
    serial = [add([row],[[b]],'serial',group) for row in a for b in (1,-1,32767,-32768)]
    groups.append({'id':group,'rows':4,'columns':4,'k':1,'tile':tile,'serial':serial,
                   'purpose':'signed ties and S32 saturation'})
    (output/'vectors.hex').write_text(''.join(f'{w:016x}\n' for w in words),newline='\n')
    (output/'vectors_size.svh').write_text(f'localparam integer VECTOR_WORDS={len(words)};\n',newline='\n')
    (output/'cases.svh').write_text(''.join(
        f"run_matrix({c['id']},{c['rows']},{c['columns']},{c['k']},{c['a']},{c['b']},{c['gold']},{c['final']});\n"
        for c in cases),newline='\n')
    compile_files = ['tb_column_tile_probe.sv']+[
        'rtl/'+name for name in RTL+EXTRA_RTL if name.endswith('.sv')]+[bank_model.name]
    (output/'compile.f').write_text(''.join(name+'\n' for name in compile_files),newline='\n')
    for name in ('vectors.hex','vectors_size.svh','cases.svh','compile.f'):
        sources[name] = sha(output/name)
    manifest = {'kind':'native-column-tile-scatter-probe-v2','cases':cases,'groups':groups,
                'source_root':str(source_root),'rtl_reference':rtl_ref,
                'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=source_root,text=True).strip(),
                'sha256':sources,'vector_words':len(words),
                'scope':'Prepared S32 A three components / static S16 B, native B[n*8+k] layout; R<=8/N<=8/Ksegment1; full K S64, final RNE; native E+M canonical scalar scatter',
                'excluded':['compiler registration','full LC/MC','physical connection acceptance',
                            'measured DRAM traffic','calibrated DMA/LC timing','energy','system throughput'],
                'transport':'Host copies complete 128-bit words, with real private S request/ACK and E service; no host arithmetic/scatter.'}
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',newline='\n')
    print(json.dumps({'cases':len(cases),'groups':len(groups),'vector_words':len(words),'output':str(output)}))


def analyse(directory, log, *, emit=True):
    manifest = json.loads((directory/'manifest.json').read_text())
    if manifest['kind'] not in ('native-column-tile-scatter-probe-v1','native-column-tile-scatter-probe-v2'):
        raise ValueError('unsupported probe manifest')
    for name, expected in manifest['sha256'].items():
        if sha(directory/name) != expected:
            raise ValueError('probe input changed: '+name)
    text = log.read_text()
    records = {}
    for match in re.finditer(r'^COLUMN_TILE (\{.*\})$',text,re.MULTILINE):
        row = json.loads(match[1])
        if row['id'] in records:
            raise ValueError('duplicate case')
        records[row['id']] = row
    if (text.count('PASS native column tile and scalar scatter probe')!=1 or
        'FATAL' in text or set(records)!={c['id'] for c in manifest['cases']}):
        raise ValueError('probe incomplete')
    for case in manifest['cases']:
        r,n,k = case['rows'],case['columns'],case['k']
        scatter = 4*r*n
        packed = 4*r*((n+3)//4)
        expected = {'rows':r,'columns':n,'k':k,
                    'a_fires':3*r*k+3*scatter,
                    'b_fires':2*k+6*scatter,
                    'wide_reads':k*(2+3*((r+3)//4))+9*scatter,
                    'store_acks':r*((n+1)//2)+packed+scatter,
                    'e_store_acks':packed,'e_commands':packed,
                    'dot_a_stage_words':3*r*k,'dot_b_stage_words':n*k}
        for field,value in expected.items():
            if records[case['id']][field]!=value:
                raise ValueError(f'case {case["id"]} {field}: {records[case["id"]][field]} != {value}')
    groups = []
    for group in manifest['groups']:
        tile = records[group['tile']]
        serial = [records[i] for i in group['serial']]
        groups.append({'rows':group['rows'],'columns':group['columns'],'k':group['k'],
            'tile_cycles':tile['cycles'],'serial_cycles':sum(c['cycles'] for c in serial) if serial else None,
            'tile_dot_a_stage_words':tile['dot_a_stage_words'],
            'serial_dot_a_stage_words':sum(c['dot_a_stage_words'] for c in serial) if serial else None,
            'tile_dot_b_stage_words':tile['dot_b_stage_words'],
            'serial_dot_b_stage_words':sum(c['dot_b_stage_words'] for c in serial) if serial else None,
            'e_store_acks':tile['e_store_acks']})
    profiles = [json.loads(m[1]) for m in re.finditer(r'^COLUMN_PROFILE (\{.*\})$',text,re.MULTILINE)]
    if manifest['kind']=='native-column-tile-scatter-probe-v2':
        expected_profiles = Counter()
        def add(boundary,r,op,store,reuse,count):
            expected_profiles[(boundary,r,op,store,reuse,None)] += count
        for case in manifest['cases']:
            r,n,k = case['rows'],case['columns'],case['k']
            scatter,packed = 4*r*n,4*r*((n+3)//4)
            for boundary in ('p-command','native-m'):
                for op,count in ((4,3*k),(10,3*k),(3,r*((n+1)//2)),(5,packed)):
                    store = int(op in (3,5)) if boundary=='p-command' else None
                    add(boundary,r,op,store,None,count)
                for op,count in ((4,3*scatter),(10,3*scatter),(5,scatter)):
                    store = int(op==5) if boundary=='p-command' else None
                    add(boundary,1,op,store,None,count)
            add('feeder',r,None,None,0,k)
            add('feeder',r,None,None,1,2*k)
            add('feeder',1,None,None,0,3*scatter)
            expected_profiles[('e-service',None,8,None,None,15)] += packed
        observed = {}
        for p in profiles:
            key = (p['boundary'],p.get('rows'),p.get('op'),p.get('store'),p.get('reuse_b'),p.get('shift'))
            if key in observed or not 0 < p['min'] <= p['max']:
                raise ValueError('invalid/duplicate passive profile')
            observed[key] = p['samples']
        if observed != dict(expected_profiles):
            raise ValueError('passive profile sample conservation')
    result = {'passed_cases':len(records),'groups':groups,'manifest_sha256':sha(directory/'manifest.json'),
              'log_sha256':sha(log),'scope':manifest['scope'],'excluded':manifest['excluded'],
              'timing_note':'Testbench cycles include serialized host word transport and intentional stalls; not product time or algorithm20.',
              'passive_profiles':profiles,
              'profile_boundary':'Rising-edge timestamp difference: acceptance to first completion, excludes completion-take stalls. P/E service includes actual private S ACK; not LC/DMA timing.'}
    phase_rows=[tuple(map(int,m)) for m in re.findall(
        r'^MATERIALIZED_PHASE id=(\d+) packed=(\d+) flags=(\d+) refill=(\d+)$',text,re.MULTILINE)]
    if manifest.get('execution_order')=='packed-external-three-phase-v1' and not phase_rows:
        raise ValueError('missing materialized native phase coverage')
    if phase_rows:
        expected=[(c['id'],4*c['rows']*((c['columns']+3)//4),
                   4*c['rows']*((c['columns']+3)//4),16) for c in manifest['cases']]
        if phase_rows!=expected:raise ValueError('materialized native phase coverage/ACK refill differs')
        result['materialized_order']={'cases':len(phase_rows),'local_packed_poisoned':True,
            'scope':'all packed captured before E, full-word external flag objects, actual zero refill before native scatter; serialized host transport, not controller/DMA/system timing'}
    if emit:
        (directory/'summary.json').write_text(json.dumps(result,indent=2)+'\n',newline='\n')
        print(json.dumps(result,indent=2))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command',required=True)
    p = sub.add_parser('prepare')
    p.add_argument('--source-root',type=Path,required=True)
    p.add_argument('--bank-model',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--rtl-ref',required=True)
    p.add_argument('--long-k',type=int,default=0)
    p = sub.add_parser('analyse')
    p.add_argument('directory',type=Path)
    p.add_argument('log',type=Path)
    args = parser.parse_args()
    if args.command=='prepare':
        prepare(args.source_root,args.bank_model,args.output,args.rtl_ref,args.long_k)
    else:
        analyse(args.directory,args.log)
