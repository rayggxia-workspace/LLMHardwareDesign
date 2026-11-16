"""Independent model vectors and strict Verilator full-K merge/raw checks."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import random
import subprocess
from oracle import a_digits, b_digits, finish, partials, S32_MIN, S32_MAX


def pack(values, bits):
    return sum((int(v) & ((1 << bits) - 1)) << (i * bits) for i, v in enumerate(values))


def memory_scalar(index):
    v = [S32_MIN, S32_MAX, -1, 0, 127, 32768, -32769]
    raw = (index * 1103515245 + 12345) & 0xffffffff
    value = raw - (1 << 32) if raw & (1 << 31) else raw
    return v[index % 11] if index % 11 < len(v) else value


def packer_vectors(out, rng):
    lines=[]
    settings=[]
    for weight in (0,1):
        for major in (0,1):
            for digit in range(5 if weight else 3):
                for k_count,n_count in ((16,4 if weight else 1),(7,3 if weight else 1),(1,1)):
                    settings.append((weight,major,digit,rng.randrange(0,4),1 if not major else 128,
                                     128 if not major else 1,k_count,n_count,0))
    for inject in (1,2):settings.append((1,1,4,0,128,1,16,4,inject))
    settings += [(0,0,3,0,1,1,16,1,0),(1,0,5,0,1,128,16,4,0),
                 (0,0,0,0,1,1,0,1,0),(1,0,0,0,1,1,16,0,0),
                 (1,0,0,0xfffffffc,0xffffffff,1,16,4,0)]
    for tag,(weight,major,digit,base,ks,ns,kc,nc,inject) in enumerate(settings):
        error=int(not 1<=kc<=16 or not 1<=nc<=4 or digit>(4 if weight else 2) or (not weight and nc!=1))
        result=[0]*(64 if weight else 16); cached=None; reads=0
        if not error:
            for element in range(64 if weight else 16):
                ki,ni=(element//4,element%4) if weight and major else (element%16,element//16 if weight else 0)
                if ki>=kc or ni>=nc:continue
                scalar=base+ki*ks+ni*ns
                if scalar>=1<<34:error=1;break
                address=scalar//4
                if address!=cached:
                    reads+=1;cached=address
                    if inject:error=1;break
                x=memory_scalar(scalar)
                destination=ni*16+ki if weight else element
                result[destination]=b_digits(x)[digit] if weight else a_digits(x)[digit]
        fields=[tag,weight,major,digit,base,ks,ns,kc,nc,inject,error,0 if error else pack(result,8 if weight else 16),reads]
        lines.append(' '.join(format(v,'x') for v in fields))
    (out/'packer.txt').write_text('\n'.join(lines)+'\n')
    # Only the final intentional >16KiB-address example is omitted: actual
    # private S must never wrap that request through its native ten-bit port.
    (out/'real-packer.txt').write_text('\n'.join(lines[:-1])+'\n')
    return len(lines)


def source_vectors(out):
    lines=[];count=0
    for major in (0,1):
        for digit in range(5):
            for length,n in ((128,8),(127,3),(1,1)):
                base,ks,ns=0,8 if major else 1,1 if major else 128
                lines.append(' '.join(format(v,'x') for v in (length,n,digit,major,base,ks,ns)))
                for beat in range(17):
                    if beat==16:word=pack([0x3c00 if j<n else 0 for j in range(8)],16)
                    else:
                        ko,no=(beat//2)*16,(beat%2)*4
                        values=[b_digits(memory_scalar(base+(ko+k)*ks+(no+c)*ns))[digit]
                                if ko+k<length and no+c<n else 0 for c in range(4) for k in range(16)]
                        word=pack(values,8)
                    lines.append(format(word,'x'))
                count+=1
    (out/'source.txt').write_text('\n'.join(lines)+'\n');return count


def product_vectors(out,seed,checkpoint):
    rng=random.Random(seed);samples=[]
    witness=json.loads(checkpoint.read_text())
    for role in ('QK','AV'):
        sample=next(v for v in witness if v['role']==role)
        samples.append(dict(A=sample['A'],B=sample['B'],shift=sample['node']['attributes']['shift'],major=int(role=='AV')))
    for k,n in ((129,3),(512,8)):
        edge=[S32_MIN,S32_MAX,-1,0,1,32768,-32769]
        samples.append(dict(A=[rng.choice(edge) for _ in range(k)],
                            B=[[rng.choice(edge) for _ in range(n)] for _ in range(k)],shift=63,major=1))
    lines=[];count=0
    for sample in samples:
        a,b,shift=sample['A'],sample['B'],sample['shift'];n=len(b[0])
        lines.append(f'{len(a)} {n} {shift} {sample["major"]}')
        lines.extend(format(x&0xffffffff,'x') for x in a)
        lines.extend(format(x&0xffffffff,'x') for row in b for x in row)
        lines.append(format(pack([finish(sum(x*row[c] for x,row in zip(a,b)),shift) for c in range(n)]+[0]*(8-n),32),'x'))
        for packet in partials(a,b):
            lines.append(format(pack(packet['raw']+[0]*(8-n),32),'x'));count+=1
    (out/'product.txt').write_text('\n'.join(lines)+'\n')
    return dict(cases=len(samples),partials=count,source='actual checkpoint QK/AV plus K129/K512 signed edges')


def generate(out, seed, checkpoint):
    rng = random.Random(seed); vectors = []; raw_vectors = []; tag = 0
    def emit(kind, key=1, full=128, kk=0, length=128, n=8, ai=0, bi=0,
             shift=16, raw=None, error=0, done=0, result=None):
        nonlocal tag
        raw = [0] * 8 if raw is None else raw + [0] * (8-len(raw))
        result = [0] * 8 if result is None else result + [0] * (8-len(result))
        fields = [kind, key, tag, full, kk, length, n, ai, bi, shift, pack(raw, 32),
                  error, done, pack(result, 32)]
        vectors.append(' '.join(format(int(v), 'x') for v in fields)); tag += 1

    samples = []
    for i, k in enumerate((1, 2, 16, 127, 128, 129, 512)):
        n = i % 8 + 1
        edges = [S32_MIN, S32_MAX, -1, 0, 1, 127, 128, 32768, -32769]
        a = [rng.choice(edges) if j % 2 else rng.randrange(S32_MIN, S32_MAX+1) for j in range(k)]
        b = [[rng.choice(edges) if (j+c) % 2 else rng.randrange(S32_MIN, S32_MAX+1)
              for c in range(n)] for j in range(k)]
        samples.append(dict(A=a, B=b, shift=(0, 1, 16, 31, 47, 63, 32)[i], role='boundary'))
    if checkpoint:
        for sample in json.loads(checkpoint.read_text()):
            samples.append(dict(A=sample['A'], B=sample['B'],
                                shift=sample['node']['attributes']['shift'], role=sample['role']))
    for index, sample in enumerate(samples):
        a, b, shift = sample['A'], sample['B'], sample['shift']; n = len(b[0]); key = (seed << 64) + index
        emit(0, key, len(a), n=n, shift=shift)
        emit(0, key+1, len(a), n=n, error=1)
        packets = list(partials(a, b))
        for j, packet in enumerate(packets):
            args = dict(key=key, full=len(a), kk=packet['kk'], length=packet['length'], n=n,
                        ai=packet['ai'], bi=packet['bi'], raw=packet['raw'])
            if j % 13 == 0:
                emit(1, **dict(args, key=key+1), error=1)
                emit(1, **dict(args, ai=3), error=1)
                emit(1, **dict(args, raw=[S32_MIN]*n), error=1)
            final = j == len(packets)-1
            result = [finish(sum(x*row[c] for x,row in zip(a,b)), shift) for c in range(n)] if final else None
            emit(1, **args, done=int(final), result=result)
            # Existing native M computes one zero-padded K128 signed digit.
            if len(raw_vectors) < 360:
                aa = [a_digits(x)[packet['ai']] for x in a[packet['kk']:packet['kk']+packet['length']]]
                bb = [[b_digits(x)[packet['bi']] for x in row] for row in b[packet['kk']:packet['kk']+packet['length']]]
                aa += [0] * (128-len(aa)); bb += [[0]*n for _ in range(128-len(bb))]
                # Beat-major, then N-major sixteen K bytes matches M port.
                payload = [bb[beat*16+k][c] if c<n else 0
                           for beat in range(8) for c in range(8) for k in range(16)]
                raw_vectors.append(' '.join(format(v, 'x') for v in
                    [len(raw_vectors), n, pack(aa,16), pack(payload,8), pack(packet['raw']+[0]*(8-n),32)]))
        emit(1, key, len(a), n=n, error=1)
    # Invalid/cancel/reuse must not retain hidden live owners.
    emit(0, full=0, error=1); emit(0, n=0, error=1); emit(0, n=9, error=1)
    emit(0, key=99); emit(2, key=100, error=1); emit(2, key=99, done=1)
    emit(2, key=99, error=1); emit(3, error=1)
    (out/'merge.txt').write_text('\n'.join(vectors)+'\n')
    (out/'raw.txt').write_text('\n'.join(raw_vectors)+'\n')
    packer_count=packer_vectors(out,rng)
    return dict(merge_commands=len(vectors), raw_groups=len(raw_vectors), samples=len(samples),
                packer_commands=packer_count,
                checkpoint_roles=sorted({v['role'] for v in samples if v['role']!='boundary'}),
                vectors_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (out/'merge.txt',out/'raw.txt',out/'packer.txt')})


def main(args):
    assert os.environ.get('SLURM_JOB_ID'), 'simulation requires Slurm compute allocation'
    args.out.mkdir(exist_ok=False, parents=True)
    report = generate(args.out, args.seed, args.checkpoint)
    report['local_source_records']=source_vectors(args.out)
    report['vectors_sha256']['source.txt']=hashlib.sha256((args.out/'source.txt').read_bytes()).hexdigest()
    report['product']=product_vectors(args.out,args.seed,args.checkpoint)
    report['vectors_sha256']['product.txt']=hashlib.sha256((args.out/'product.txt').read_bytes()).hexdigest()
    rtl = args.source/'project/rtl/w8a16_v1'; exp=args.source/'project/experiments/w8a16_dynamic'
    for name, files in [('merge',[rtl/'dynamic_s32_merge.sv']),
                        ('packer',[rtl/'dynamic_s32_packer.sv']),
                        ('raw',[rtl/'m_group_s32.sv',rtl/'scale_group_s32.sv'])]:
        build=args.out/('obj-'+name)
        cmd=[str(args.verilator),'--binary','--timing','--assert','--x-initial','unique','--x-assign','unique',
             '--Wall','-Wno-BLKSEQ','-Wno-TIMESCALEMOD',
             '--top-module','tb_'+name,'--Mdir',str(build),'-j','10',str(exp/('tb_'+name+'.sv'))]+[str(p) for p in files]
        with (args.out/(name+'-build.log')).open('w') as log:
            subprocess.run(cmd,check=True,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT)
        for initial in (0,1,2):
            with (args.out/(name+'-'+str(initial)+'.log')).open('w') as log:
                subprocess.run([str(build/('Vtb_'+name)),'+vectors='+str(args.out/(name+'.txt')),
                                '+verilator+seed+'+str(args.seed),'+verilator+rand+reset+'+str(initial)],
                               check=True,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT)
    upstream=args.source.parent/'upstream'; name='real-packer'; build=args.out/('obj-'+name)
    cmd=[str(args.verilator),'--binary','--timing','--assert','--x-initial','unique','--x-assign','unique',
         '--Wall','-Wno-BLKSEQ','--timescale-override','1ns/1ps','-DREAL_S',
         '--top-module','tb_packer','--Mdir',str(build),'-j','10',str(exp/'native_s_lint.vlt'),
         str(exp/'tb_packer.sv'),str(rtl/'dynamic_s32_packer.sv'),
         str(upstream/'local_s_base.sv'),str(upstream/'block_feed_s16k_sram.sv'),
         str(upstream/'s_sram_256x128_freepdk45.v')]
    with (args.out/(name+'-build.log')).open('w') as log:
        subprocess.run(cmd,check=True,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT)
    for initial in (0,1,2):
        for ideal in (0,1):
            with (args.out/(name+'-'+str(initial)+'-'+str(ideal)+'.log')).open('w') as log:
                subprocess.run([str(build/'Vtb_packer'),'+vectors='+str(args.out/'real-packer.txt'),
                                '+ideal='+str(ideal),'+verilator+seed+'+str(args.seed),
                                '+verilator+rand+reset+'+str(initial)],check=True,
                               stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT)
    name='weight-source';build=args.out/('obj-'+name)
    cmd=[str(args.verilator),'--binary','--timing','--assert','--x-initial','unique','--x-assign','unique',
         '--Wall','-Wno-BLKSEQ','--timescale-override','1ns/1ps',
         '--top-module','tb_weight_source','--Mdir',str(build),'-j','10',str(exp/'native_s_lint.vlt'),
         str(exp/'tb_weight_source.sv'),str(rtl/'dynamic_s32_packer.sv'),str(rtl/'dynamic_s32_weight_source.sv'),
         str(upstream/'local_s_base.sv'),str(upstream/'block_feed_s16k_sram.sv'),str(upstream/'s_sram_256x128_freepdk45.v')]
    with (args.out/(name+'-build.log')).open('w') as log:
        subprocess.run(cmd,check=True,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT)
    for initial in (0,1,2):
        with (args.out/(name+'-'+str(initial)+'.log')).open('w') as log:
            subprocess.run([str(build/'Vtb_weight_source'),'+vectors='+str(args.out/'source.txt'),
                            '+verilator+seed+'+str(args.seed),'+verilator+rand+reset+'+str(initial)],
                           check=True,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT)
    name='product';build=args.out/('obj-'+name)
    modules=['m_native_leaf_s32','m_native_s32','weight_records','m_group_s32',
             'projection_context_s32','scale_group_s32','dynamic_s32_merge',
             'dynamic_s32_packer','dynamic_s32_weight_source']
    cmd=[str(args.verilator),'--binary','--timing','--assert','--x-initial','unique','--x-assign','unique',
         '--Wall','-Wno-BLKSEQ','--timescale-override','1ns/1ps',
         '--top-module','tb_product','--Mdir',str(build),'-j','10',str(exp/'native_s_lint.vlt'),str(exp/'tb_product.sv')]
    cmd += [str(rtl/(n+'.sv')) for n in modules]+[str(upstream/p) for p in
            ('local_s_base.sv','block_feed_s16k_sram.sv','s_sram_256x128_freepdk45.v')]
    with (args.out/(name+'-build.log')).open('w') as log:
        subprocess.run(cmd,check=True,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT)
    for initial in (0,1,2):
        with (args.out/(name+'-'+str(initial)+'.log')).open('w') as log:
            subprocess.run([str(build/'Vtb_product'),'+vectors='+str(args.out/'product.txt'),
                            '+verilator+seed+'+str(args.seed),'+verilator+rand+reset+'+str(initial)],
                           check=True,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT)
        with (args.out/(name+'-'+str(initial)+'-ideal.log')).open('w') as log:
            subprocess.run([str(build/'Vtb_product'),'+vectors='+str(args.out/'product.txt'),'+ideal=1',
                            '+verilator+seed+'+str(args.seed),'+verilator+rand+reset+'+str(initial)],
                           check=True,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT)
    report.update(passed=True, seed=args.seed, slurm_job=os.environ.get('SLURM_JOB_ID'),
                  scope='independent merge, native raw M/scale-one and real SRAM packer; not whole provider/program')
    (args.out/'result.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True);parser.add_argument('--seed',type=int,required=True)
    parser.add_argument('--checkpoint',type=Path);parser.add_argument('--verilator',type=Path,required=True)
    main(parser.parse_args())
