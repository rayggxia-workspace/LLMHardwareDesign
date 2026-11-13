"""Use a hash-locked compiled gate model to calibrate true accumulating streams.

Only the new C++ driver is rebuilt. No mutable original attempt, model source
or hardware gets edited. Active/idle pairs finish with the same S64 state.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def call(cmd, log):
    with log.open('w') as f:
        r = subprocess.run(list(map(str, cmd)), stdout=f, stderr=subprocess.STDOUT)
    if r.returncode:
        raise RuntimeError('command failed: ' + str(log))


def main():
    p = argparse.ArgumentParser()
    p.add_argument('compiled_model', type=Path)
    p.add_argument('model_manifest', type=Path)
    p.add_argument('verilator_include', type=Path)
    p.add_argument('operands', type=Path)
    p.add_argument('physical', type=Path)
    p.add_argument('liberty', type=Path)
    p.add_argument('output', type=Path)
    p.add_argument('--workers', type=int, default=6)
    p.add_argument('--cores-per-power', type=int, default=10)
    p.add_argument('--begin-k', type=int, default=1000)
    p.add_argument('--count-k', type=int, default=16)
    a = p.parse_args()
    if min(a.workers, a.cores_per_power, a.count_k) < 1 or not 0 <= a.begin_k < a.begin_k+a.count_k <= 2048:
        raise ValueError('invalid window/resources')
    import os
    if os.environ.get('SLURM_NTASKS'):
        if a.workers*a.cores_per_power > int(os.environ['SLURM_NTASKS'])*int(os.environ['SLURM_CPUS_PER_TASK']):
            raise ValueError('worker demand exceeds allocation')
    a.output.mkdir(exist_ok=False)
    manifest = json.loads(a.model_manifest.read_text())
    for name, digest in manifest['files_sha256'].items():
        if Path(name).name != name or sha(a.compiled_model/name) != digest:
            raise ValueError('compiled model drift')
    if sha(a.physical/'6_final.v') != manifest['source_gate_v_sha256']:
        raise ValueError('compiled model belongs to another physical netlist')
    source = Path(__file__).parent
    binary = a.output/'m-stream'
    cmd = ['g++', '-std=c++17', '-O1', '-DVM_TRACE=1', '-DVM_TRACE_VCD=1', '-DVM_TRACE_FST=0',
           '-DVM_TRACE_SAIF=0', '-DVM_TIMING=0', '-DVM_COVERAGE=0',
           '-I'+str(a.compiled_model), '-I'+str(a.verilator_include), '-I'+str(a.verilator_include/'vltstd'),
           source/'m_activity.cpp', a.compiled_model/'Vblock_v2_m__ALL.a']
    cmd += [a.compiled_model/x for x in ['verilated.o','verilated_vcd_c.o','verilated_threads.o']]
    cmd += ['-pthread','-latomic','-o',binary]
    call(cmd, a.output/'build.log')
    capture = json.loads((a.operands/'receipt.json').read_text())
    streams = capture['accumulating_streams']
    if len(streams) != 6:
        raise ValueError('expected three cohorts and two real Q columns')

    def worker(s):
        path = a.operands/s['file']
        if Path(s['file']).name != s['file'] or sha(path) != s['sha256']:
            raise ValueError('operand stream drift')
        rows = [[int(v) for v in line.split()] for line in path.read_text().splitlines()]
        if len(rows) != 6144:
            raise ValueError('not a complete K2048 stream')
        # Independent reconstruction uses unsigned low16, not the driver's
        # explicit third correction product, then a Python arbitrary-size dot.
        expected = 0
        for k in range(a.begin_k+a.count_k):
            low, high, flag = rows[3*k:3*k+3]
            if [low[2],high[2],flag[2]] != [0,16,16] or not low[1]==high[1]==flag[1] or flag[0] != int(low[0]<0):
                raise ValueError('invalid component encoding')
            expected += ((low[0]&65535)+(high[0]<<16))*low[1]
        result = {}
        for mode in ['stream','stream-idle']:
            out = a.output/('cohort-%d-col-%d-%s'%(s['cohort'],s['column'],mode))
            out.mkdir()
            vcd = out/'gate.vcd'
            call([binary,path,vcd,mode,a.begin_k,a.count_k],out/'functional.log')
            text = (out/'functional.log').read_text()
            events = [json.loads(x[9:]) for x in text.splitlines() if x.startswith('ACTIVITY ')]
            if len(events)!=1 or not events[0]['passed'] or events[0]['s64_prefix']!=expected:
                raise ValueError('independent prefix arithmetic differs')
            if set(map(int,re.findall(r'(?m)^EXECUTE_CYCLES (\d+)$',text))) != {22}:
                raise ValueError('native Execute timing changed')
            if mode=='stream' and events[0]['cycles'] != a.count_k*3*27:
                raise ValueError('actual accumulation body is not 27 cycles per component')
            functional = out/'functional.json'
            functional.write_text(json.dumps({'timing':events[0]})+'\n')
            call([sys.executable,source/'analyze_activity.py',a.physical,a.liberty,vcd,functional,
                  out/'power','--cores',a.cores_per_power],out/'analysis.log')
            result[mode] = json.loads((out/'power/receipt.json').read_text())
        active, idle = result['stream'], result['stream-idle']
        result['observed_incremental_j_per_component'] = (
            active['power_w']['total']-idle['power_w']['total'])*active['window']['window_ps']*1e-12/(a.count_k*3)
        result['cohort'], result['column'] = s['cohort'], s['column']
        return result

    with ThreadPoolExecutor(max_workers=a.workers) as pool:
        results = list(pool.map(worker,streams))
    report = {'scope':'sampled real S64 accumulation prefixes; not complete Qwen energy',
              'begin_k':a.begin_k,'count_k':a.count_k,'independent_prefix_numeric_passed':True,
              'compiled_model_manifest_sha256':sha(a.model_manifest), 'binary_sha256':sha(binary),
              'driver_sha256':sha(source/'m_activity.cpp'),'source_sha256':sha(Path(__file__)),
              'build_command':list(map(str,cmd)),'records':results,
              'full_model_timing_qualified':False,'full_model_energy_qualified':False}
    (a.output/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'calibrated_prefix_pairs':len(results),'full_model_energy_qualified':False}))


if __name__=='__main__':
    main()
