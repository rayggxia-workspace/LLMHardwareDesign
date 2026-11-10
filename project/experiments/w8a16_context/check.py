"""Independent finite RF ownership/K-order scoreboard plus Fraction arithmetic."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import random
import subprocess


def generate(source, output, seed):
    spec = importlib.util.spec_from_file_location("numeric_oracle", source / "project/experiments/w8a16_m/check.py")
    oracle = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(oracle)
    rng = random.Random(seed)
    contexts = {}
    rows = []
    counts = dict(create=0, restore=0, step=0, spill=0, drop=0, fault=0, numeric_fault=0)
    input_widths = [3, 4, 128, 32, 16, 16, 8, 4, 1, 6, 256, 256, 256, 128]
    output_widths = [3, 4, 128, 32, 16, 8, 4, 16, 1, 256, 1]

    def command(kind, slot, key, full=256, offset=0, group=128, n=8, final=0,
                shift=0, partial=None, previous=None, bias=None, scales=None):
        partial = partial if partial is not None else [rng.randrange(-32768, 32768) for _ in range(8)]
        previous = previous if previous is not None else [rng.randrange(-10000, 10000) for _ in range(8)]
        bias = bias if bias is not None else [rng.randrange(-100, 100) for _ in range(8)]
        scales = scales if scales is not None else [0x3800] * 8
        old = contexts.get(slot)
        data = [0] * 8
        error = 0
        next_k = offset if kind < 2 else offset + group if kind == 2 else old['next'] if old else 0
        if kind < 2:
            error = int(old is not None or not 1 <= n <= 8 or group not in (16, 128) or
                        full == 0 or full % group != 0 or offset >= full or offset % group != 0 or
                        (kind == 0 and offset != 0) or (kind == 1 and offset == 0))
            if not error:
                data = [0] * 8 if kind == 0 else previous[:n] + [0] * (8 - n)
                contexts[slot] = dict(owner=key, full=full, next=offset, group=group, n=n, data=data)
        elif kind == 2:
            error = int(old is None or old['owner'] != key or old['full'] != full or
                        old['next'] != offset or old['group'] != group or old['n'] != n or
                        next_k > full or bool(final) != (next_k == full))
            if not error:
                data, error = oracle.scale_reference(partial, scales, old['data'], bias, n, False, final, shift)
                counts['numeric_fault'] += error
                if not error:
                    if final:
                        del contexts[slot]
                    else:
                        contexts[slot] = dict(old, next=next_k, data=data)
        elif kind in (3, 4):
            error = int(old is None or old['owner'] != key)
            if not error:
                data = old['data'] if kind == 3 else [0] * 8
                del contexts[slot]
        else:
            error = 1
        if error:
            data, next_k = [0] * 8, 0
        tag = len(rows)
        inp = [kind, slot, key, tag, full, offset, group, n, final, shift,
               oracle.vec(partial, 32), oracle.vec(previous, 32), oracle.vec(bias, 32), oracle.vec(scales, 16)]
        metadata = [0, 0, 0] if error else [full, group, n] if kind < 2 else [old['full'], old['group'], old['n']]
        out = [kind, slot, key, tag] + metadata + [next_k, int(kind == 2 and bool(final)), oracle.vec(data, 32), error]
        rows.append(oracle.pack(list(zip(input_widths, inp)) + list(zip(output_widths, out))))
        counts[['create', 'restore', 'step', 'spill', 'drop'][kind] if kind < 5 else 'fault'] += 1
        counts['fault'] += error if kind < 5 else 0

    # Fill every physical context, reject a seventeenth owner alias, exercise
    # every cursor/identity check without changing the preserved valid state.
    for s in range(16):
        command(0, s, (seed << 64) + s)
    command(0, 0, 0xBAD)
    for s in range(16):
        key = contexts[s]['owner']
        command(2, s, key + (1 << 96))
        command(2, s, key, offset=128, final=1)
        command(2, s, key, final=1)
        command(2, s, key, partial=[2147483647] * 8, scales=[0x4000] * 8)
        command(2, s, key)
        snapshot = dict(contexts[s])
        # A malformed but irrelevant command payload cannot falsify metadata
        # of the actual context being spilled.
        command(3, s, key, full=640, group=16, n=1)
        # Snapshot persistence/ACK is the external bounded service's duty.
        command(1, s, key, offset=128, previous=snapshot['data'])
        command(2, s, key, offset=128, final=1)
        command(2, s, key, offset=128, final=1)
    # Head uses group16, eight independent FP16 rounding steps per K128.
    # Consecutive same-slot updates explicitly require RF forwarding.
    for iteration in range(64):
        key = (seed << 96) + 1000 + iteration
        command(0, 0, key, group=16, full=128)
        for k in range(0, 128, 16):
            command(2, 0, key, group=16, full=128, offset=k, final=int(k == 112),
                    scales=[rng.choice([1, 0x3400, 0x3800, 0x3C00]) for _ in range(8)])
    # 86 Down output groups exceed the 16-entry RF. Spill/restore through a
    # test memory dictionary; no implicit expansion of the DUT register file.
    saved = {}
    for k in range(0, 512, 128):
        for col in range(86):
            key = (seed << 96) + 100000 + col
            slot = col % 16
            if k:
                command(1, slot, key, full=512, offset=k, previous=saved[col])
            else:
                command(0, slot, key, full=512)
            command(2, slot, key, full=512, offset=k, final=int(k == 384))
            if k != 384:
                saved[col] = contexts[slot]['data']
                command(3, slot, key)
    for _ in range(2500):
        slot = rng.randrange(16)
        old = contexts.get(slot)
        if not old:
            group = rng.choice([16, 128])
            command(0, slot, rng.getrandbits(128), full=group * rng.choice([2, 4, 8]), group=group, n=rng.randrange(1, 9))
        else:
            kind = rng.choices([2, 3, 4], [8, 1, 1])[0]
            key = old['owner'] if rng.randrange(8) else old['owner'] ^ (1 << 127)
            command(kind, slot, key, full=old['full'], offset=old['next'], group=old['group'], n=old['n'],
                    final=int(old['next'] + old['group'] == old['full']))
    for slot in list(contexts):
        command(4, slot, contexts[slot]['owner'])
    command(5, 0, 1)
    assert not contexts
    width, response_width = sum(input_widths + output_widths), sum(output_widths)
    oracle.write_vectors(output / 'context.hex', rows, width)
    (output / 'counts.vh').write_text(f'`define CONTEXT_COUNT {len(rows)}\n`define CONTEXT_WIDTH {width}\n`define RESPONSE_WIDTH {response_width}\n')
    return counts, len(rows)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--seed', type=int, required=True)
    p.add_argument('--verilator', required=True)
    args = p.parse_args()
    if not os.environ.get('SLURM_JOB_ID'):
        raise RuntimeError('RTL simulation requires Slurm compute')
    args.out.mkdir(parents=True, exist_ok=False)
    counts, count = generate(args.source, args.out, args.seed)
    # Also exercise the standalone elastic scaler with independent commands
    # at II=1. RF recurrence stalls must not hide stage ordering/hold bugs.
    scale_spec = importlib.util.spec_from_file_location("scale_oracle", args.source / "project/experiments/w8a16_m/check.py")
    scale_oracle = importlib.util.module_from_spec(scale_spec)
    scale_spec.loader.exec_module(scale_oracle)
    scale_count, scale_good = scale_oracle.generate_scale(random.Random(args.seed), args.out)
    with (args.out / 'counts.vh').open('a', encoding='utf-8') as log:
        log.write(f'`define SCALE_COUNT {scale_count}\n')
    environment = dict(os.environ)
    environment.pop('VERILATOR_ROOT', None)
    build = [args.verilator, '--binary', '--timing', '--assert', '--x-initial', 'unique', '--x-assign', 'unique', '-Wall', '-Wno-BLKSEQ', '-Wno-TIMESCALEMOD',
             '--top-module', 'tb_context', '-j', '10', '-I' + str(args.out), '--Mdir', str(args.out / 'obj')]
    build += [str(args.source / path) for path in ('project/rtl/w8a16_v1/scale_group_s32.sv',
              'project/rtl/w8a16_v1/projection_context_s32.sv', 'project/experiments/w8a16_context/tb_context.sv')]
    with (args.out / 'build.log').open('w') as log:
        subprocess.run(build, cwd=args.out, env=environment, stdout=log, stderr=subprocess.STDOUT, check=True)
    for initial in range(3):
        name = 'simulation.log' if initial == 0 else f'simulation-{initial}.log'
        with (args.out / name).open('w') as log:
            subprocess.run([str(args.out / 'obj/Vtb_context'), f'+verilator+seed+{args.seed}', f'+verilator+rand+reset+{initial}'],
                           cwd=args.out, env=environment, stdout=log, stderr=subprocess.STDOUT, check=True)
        assert 'PASS context ' in (args.out / name).read_text()
        assert 'peak_head_run=8 peak_inflight=3' in (args.out / name).read_text()
        (args.out / 'context-timing.csv').rename(args.out / f'context-timing-{initial}.csv')
    scale_build = [args.verilator, '--binary', '--timing', '--assert', '--x-initial', 'unique', '--x-assign', 'unique', '-Wall', '-Wno-BLKSEQ', '-Wno-TIMESCALEMOD',
                   '--top-module', 'tb_scale', '-j', '10', '-I' + str(args.out), '--Mdir', str(args.out / 'obj-scale'),
                   str(args.source / 'project/rtl/w8a16_v1/scale_group_s32.sv'),
                   str(args.source / 'project/experiments/w8a16_m/tb_scale.sv')]
    with (args.out / 'scale-build.log').open('w') as log:
        subprocess.run(scale_build, cwd=args.out, env=environment, stdout=log, stderr=subprocess.STDOUT, check=True)
    for initial in range(3):
        name = 'scale-simulation.log' if initial == 0 else f'scale-simulation-{initial}.log'
        with (args.out / name).open('w') as log:
            subprocess.run([str(args.out / 'obj-scale/Vtb_scale'), f'+verilator+seed+{args.seed}', f'+verilator+rand+reset+{initial}'],
                           cwd=args.out, env=environment, stdout=log, stderr=subprocess.STDOUT, check=True)
        assert 'PASS scale ' in (args.out / name).read_text()
    report = dict(seed=args.seed, vectors=count, initializations=3, finite_pipeline_owners=3, same_owner_head_II=1,
                  metadata_pipeline_bits=930, counts=counts, scale_vectors=scale_count, scale_good=scale_good,
                  hashes={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in args.out.iterdir() if p.is_file()},
                  qualification='finite projection RF unit, not full M/control/memory/physical acceptance')
    (args.out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
