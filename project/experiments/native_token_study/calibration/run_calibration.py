"""Server-only native P timing calibration. Requires an actual Slurm allocation."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import time

from generate_bench import generate
from timing_contract import m_leaf_latency, command_done_latency, load_done_latency, verify_frozen_points

HERE = Path(__file__).resolve().parent
V = Path('/public/home/yuzelu/opt/eda/verilator-5-042-repro02/bin/verilator')
BANK = Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-155/bank-views-011/generation/bank/s_sram_256x128_freepdk45.v')
BANK_SHA = '6c1c1ca9d183ab7c4c74df056c9730cf352d165301546126e29b644a45ef9de7'
SOURCES = [
 'project/rtl/block_local_s/block_local_s_arbiter.sv',
 'project/rtl/block_local_s/popt_s_policy_arbiter.sv',
 'project/rtl/s_sram/block_feed_s16k_sram.sv',
 'project/rtl/s_sram/block_feed_s16k_bank_rw.sv',
 'project/rtl/s_sram/local_s_p.sv',
 'project/rtl/block_feed_v1/block_feed_loader.sv',
 'project/rtl/block_v2/block_v2_m.sv',
 'project/rtl/block_v2/block_v2_m_context.sv',
 'project/rtl/block_v2/block_v2_g.sv',
] + ['project/rtl/pu_leaf_base/' + s + '.sv' for s in
     ('pu_p_group', 'pu_p_store_control', 'pj_feed_hold', 'pj_mem_port', 'pj_sram_client')]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def audit(rows):
    assert len({r['case'] for r in rows if r['kind'] == 'load'}) == 12
    commands = loads = io = 0
    for ix, r in enumerate(rows):
        assert r['latency'] == r['done'] - r['accepted']
        if r['kind'] == 'command':
            commands += 1
            op = r['op']
            leaf = m_leaf_latency((r['K'] + 7) // 8, r['Awide'], r['Bwide'], r['rows']) if op in (10, 13) else 3 if op == 5 else 0
            assert r['leaf_latency'] == leaf, ('leaf', r, leaf)
            assert r['latency'] == command_done_latency(leaf, bool(r['store'])), ('wrapper', r)
            assert r['stores'] == r['store'], ('write ACK count', r)
            data = int(r['data_hex'],16)
            if op == 4:
                assert (data & 65535) == 1 and r['scale_shift'] == (data >> 16) and r['scale_shift'] in (0,15,30)
            if op == 13:
                limb = (data >> 15) & 7
                assert limb < 3 and r['scale_shift'] == 15 * limb
                assert ((data >> 18) & 65535) == limb * r['K']
                assert ((data >> 2) & 1) == (limb == 0) and ((data >> 3) & 1) == (limb == 2)
            if ix and rows[ix-1]['kind'] == 'command' and rows[ix-1]['case'] == r['case']:
                prev = rows[ix-1]
                assert r['accepted'] - prev['accepted'] == prev['latency'] + 2, ('accept interval', prev, r)
        elif r['kind'] == 'load':
            loads += 1
            t, count, bw = r['tiles'], r['rows'], r['Bwide']
            assert r['latency'] == load_done_latency(t, count, bool(bw)), ('LOAD', r)
            assert r['A'] == count * t and r['B'] == (1 + bw) * t
            assert r['wide'] == ((1 if count else 0) + 1 + bw) * t
        elif r['kind'] == 'io':
            io += 1
            assert r['latency'] == 4, ('ordinary external128 response', r)
            if ix and rows[ix-1]['kind'] == 'io':
                assert r['accepted'] - rows[ix-1]['accepted'] == 6
        else:
            raise AssertionError('unknown event')
    assert io == 8 and loads == 108
    assert sum(r['kind']=='command' and r['op']==14 for r in rows) == 96
    assert sum(r['kind']=='command' and r['op']==13 for r in rows) == 288
    return dict(passed=True, commands=commands, loads=loads, io=io, cases=12,
                release_commands=96, context_compute_commands=288)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--repo', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--manifest', type=Path, required=True)
    p.add_argument('--workers', type=int, default=4)
    a = p.parse_args()
    allocation = int(os.environ.get('SLURM_CPUS_PER_TASK', '0'))
    if not os.environ.get('SLURM_JOB_ID') or not 1 <= a.workers <= min(4, allocation):
        raise ValueError('server Slurm allocation required, at most four workers')
    a.repo = a.repo.resolve(); a.out = a.out.resolve()
    manifest = json.loads(a.manifest.read_text())
    if not re.fullmatch('[0-9a-f]{40}', manifest['source_commit']):
        raise ValueError('real frozen commit required')
    for name, digest in manifest['code_sha256'].items():
        if sha(a.repo/name) != digest:
            raise ValueError('source lock mismatch: ' + name)
    if not set(SOURCES).issubset(manifest['code_sha256']):
        raise ValueError('manifest omits actual RTL source')
    if sha(BANK) != BANK_SHA:
        raise ValueError('SRAM macro identity drift')
    a.out.mkdir(parents=True, exist_ok=False)
    report = dict(passed=False, source_commit=manifest['source_commit'], source_sha256={s: sha(a.repo/s) for s in SOURCES},
        helper_sha256={s:sha(HERE/s) for s in ('run_calibration.py','generate_bench.py','timing_contract.py','timing_body.sv.inc')},
        manifest_sha256=sha(a.manifest), bank_sha256=BANK_SHA, versions={'python':platform.python_version()},
        prior_measured_points=verify_frozen_points(), commands=[], runs=[],
        scope='actual native P cycles for zero-backpressure serial controller; no DDR, physical clock, S32 conversion, S96 merge, or token/s qualification')

    def execute(command, log):
        command = list(map(str, command)); began = time.monotonic()
        result = subprocess.run(command, cwd=a.repo, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        target = a.out/log; target.write_bytes(result.stdout)
        report['commands'].append(dict(command=command, exit_code=result.returncode, seconds=time.monotonic()-began, log=log, sha256=sha(target)))
        if result.returncode:
            raise RuntimeError(log + ' failed: ' + result.stdout.decode(errors='replace')[-1800:])
        return result.stdout.decode(errors='replace')

    try:
        report['versions']['verilator'] = execute([V, '--version'], 'verilator-version.log').strip()
        report['versions']['gcc'] = execute(['g++', '--version'], 'gcc-version.log').splitlines()[0]
        bench = a.out/'tb_token_timing.sv'; generate(a.repo, bench)
        report['generated_bench_sha256'] = sha(bench)
        canonical = None
        for label, bank_rw, policy in [('serial-original-backend',0,0), ('serial-enabled-backend',1,1)]:
            obj = a.out/('obj-'+label)
            execute([V, '--binary', '--timing', '--assert', '--timescale', '1ns/1ps', '-Wno-fatal',
                     '--x-initial','unique','--x-assign','unique','-j',a.workers,
                     '-I'+str(a.repo/'project/rtl/block_v2'), '--top-module','tb_token_timing','--Mdir',obj,
                     '-GBANK_RW='+str(bank_rw), '-GPOLICY='+str(policy), bench,
                     *[a.repo/s for s in SOURCES], BANK], label+'-build.log')
            for mode, seed in ((1,143),(2,143),(2,144)):
                log = '{}-{}-{}.log'.format(label,mode,seed)
                output = execute([obj/'Vtb_token_timing', '+verilator+rand+reset+'+str(mode), '+verilator+seed+'+str(seed)], log)
                if 'PASS TOKEN_TIMING actual P' not in output:
                    raise ValueError('missing successful RTL receipt')
                events = [json.loads(line[4:]) for line in output.splitlines() if line.startswith('CAL ')]
                checked = audit(events)
                if canonical is None: canonical = events
                elif events != canonical: raise ValueError('serial timing/numeric receipt differs by backend or random initialization')
                report['runs'].append(dict(label=label,mode=mode,seed=seed,checks=checked,events=events,log=log,sha256=sha(a.out/log)))
        # Useful timing points are reported once, rather than averaging schedules.
        report['passed'] = True
    finally:
        (a.out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(passed=True,result=str(a.out/'result.json'),sha256=sha(a.out/'result.json'))))


if __name__ == '__main__':
    main()
