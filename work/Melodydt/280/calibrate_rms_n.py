"""Replay real RMS N inputs and estimate paired boundary-propagated cell power.

This covers the N core only. No E, SRAM, scan/apply wrapper, wire RC, internal
gate activity or timing signoff is claimed. --smoke uses synthetic data only.
"""
import argparse
from hashlib import sha256
import json
from math import isqrt
from pathlib import Path
import re
import subprocess

from verify_arithmetic_capture import rounded


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def clip_ports(raw, target, ports, first, last, testbench='tb_rms_n_activity', time_divisor=3):
    """Clip initialized boundary activity; legacy N defaults retime 100 to 300 MHz."""
    if time_divisor < 1:
        raise ValueError('invalid waveform time divisor')
    names, stack, selected = {}, [], {}
    events = []
    with raw.open() as stream:
        for line in stream:
            fields = line.split()
            if fields[:1] == ['$scope']:
                stack.append(fields[2])
            elif fields[:1] == ['$upscope']:
                stack.pop()
            elif fields[:1] == ['$var'] and stack[-2:] == [testbench, 'dut']:
                if fields[4] in ports:
                    if int(fields[2]) != len(ports[fields[4]]['bits']):
                        raise ValueError('port width mismatch')
                    names[fields[4]] = (fields[3], fields[2])
            elif fields[:1] == ['$enddefinitions']:
                break
        if set(names) != set(ports):
            raise ValueError('missing RTL boundary ports')
        ids = {v[0] for v in names.values()}
        time = 0
        for line in stream:
            fields = line.split()
            if line.startswith('#'):
                time = int(line[1:])
            elif fields and fields[0][0] in '01xz':
                ident, value = fields[0][1:], fields[0][0]
                if ident in ids:
                    events.append((time, ident, value))
            elif len(fields) == 2 and fields[0][0] in 'bB' and fields[1] in ids:
                events.append((time, fields[1], fields[0][1:]))
    for time, ident, value in events:
        if time <= first:
            selected[ident] = value
    if set(selected) != ids or any(set(v) - set('01') for v in selected.values()):
        raise ValueError('uninitialized activity window')
    with target.open('w') as stream:
        stream.write('$timescale 1ps $end\n$scope module dut $end\n')
        for name, (ident, width) in names.items():
            bus_range = ' [{}:0]'.format(int(width)-1) if int(width) > 1 else ''
            stream.write('$var wire {} {} {}{} $end\n'.format(width, ident, name, bus_range))
        stream.write('$upscope $end\n$enddefinitions $end\n#0\n')
        for ident, value in selected.items():
            stream.write('b{} {}\n'.format(value, ident))
        previous_time = 0
        for time, ident, value in events:
            if first < time <= last:
                if set(value) - set('01'):
                    raise ValueError('unknown boundary activity')
                tick = ((time - first) + time_divisor//2) // time_divisor
                if tick != previous_time:
                    stream.write('#{}\n'.format(tick))
                    previous_time = tick
                stream.write('b{} {}\n'.format(value, ident))
        stream.write('#{}\n'.format(((last - first) + time_divisor//2) // time_divisor))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('root', 'bundle', 'output'):
        parser.add_argument(key, type=Path)
    parser.add_argument('--capture', type=Path)
    parser.add_argument('--smoke', action='store_true')
    args = parser.parse_args()
    if bool(args.capture) == args.smoke:
        parser.error('choose exactly one of --capture and --smoke')
    out = args.output
    out.mkdir()
    mapped = args.root / 'common-arithmetic-01/run-38828028/block_v2_n'
    source = args.root / 'common-arithmetic-01/rtl'
    receipt = json.loads((mapped / 'receipt.json').read_text())
    for path, expected in receipt['inputs_sha256'].items():
        if digest(Path(path)) != expected:
            raise ValueError('mapped source changed')
    if digest(mapped / 'mapped.v') != receipt['outputs_sha256']['mapped.v']:
        raise ValueError('mapped netlist changed')
    platform = Path('/OpenROAD-flow-scripts/flow/platforms/nangate45')
    lib = platform / 'lib/NangateOpenCellLibrary_typical.lib'
    if digest(lib) != receipt['liberty_sha256']:
        raise ValueError('mapping liberty changed')
    ports = json.loads((mapped / 'mapped.json').read_text())['modules']['block_v2_n']['ports']
    executable = Path.home() / 'LLMHardware/opt/verilator-5.042/bin/verilator'
    subprocess.run([str(executable), '--version'], stdout=(out/'verilator-version.txt').open('w'), check=True)
    cmd = [str(executable), '--binary', '--timing', '--trace', '--trace-depth', '2',
           '--assert', '-Wno-fatal', '-j', '12', '--top-module', 'tb_rms_n_activity',
           '--Mdir', str(out/'obj'), '-I'+str(source),
           str(source/'block_v2_n.sv'), str(source/'block_v2_n_group.sv'),
           str(args.bundle/'tb_rms_n_activity.sv')]
    with (out/'build.log').open('w') as log:
        subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, check=True)
    if args.smoke:
        samples = [dict(source=[(i-32)*101 for i in range(64)], words=16, shift=0,
                        extra=0, epsilon=4295, signature='synthetic-smoke-only')]
    else:
        accepted = args.capture.with_name('arithmetic-capture-check.json')
        if not json.loads(accepted.read_text())['passed']:
            raise ValueError('capture not accepted')
        samples = json.loads(args.capture.read_text())['samples']
    results = []
    for index, sample in enumerate(samples):
        path = out / ('sample-%03d' % index)
        path.mkdir()
        values = [rounded(x << sample['shift'], sample['extra']) for x in sample['source']]
        if len(values) != sample['words']*4 or any(not -32768 <= x <= 32767 for x in values):
            raise ValueError('invalid narrowed inputs')
        eps = max(1, rounded(sample['epsilon'], 2*sample['extra']))
        factor = (1 << 38) // isqrt((sum(x*x for x in values) << 14)//sample['words'] + (eps << 16))
        lines = ['{} {} {}'.format(sample['words'], eps, factor)]
        for word in range(sample['words']):
            lines.append('{:016x}'.format(sum((v & 65535) << (16*i) for i, v in enumerate(values[word*4:word*4+4]))))
        (path/'vectors.txt').write_text('\n'.join(lines)+'\n')
        raw = path/'rtl.vcd'
        with (path/'run.log').open('w') as log:
            subprocess.run([str(out/'obj/Vtb_rms_n_activity'), '+vectors='+str(path/'vectors.txt'), '+wave='+str(raw)],
                           stdout=log, stderr=subprocess.STDOUT, check=True)
        log = (path/'run.log').read_text()
        matches = re.findall(r'RMS_N_PASS words=(\d+) active_start=(\d+) active_end=(\d+) idle_end=(\d+)', log)
        if len(matches) != 1:
            raise ValueError('RTL acceptance missing')
        words, start, end, idle_end = map(int, matches[0])
        if words != sample['words'] or idle_end-end != end-start:
            raise ValueError('unequal paired windows')
        powers = {}
        for name, first, last in [('active', start, end), ('idle', end, idle_end)]:
            wave = path/(name+'.vcd')
            clip_ports(raw, wave, ports, first, last)
            tcl = '\n'.join([
                'read_liberty {'+str(lib)+'}',
                'read_lef {'+str(platform/'lef/NangateOpenCellLibrary.tech.lef')+'}',
                'read_lef {'+str(platform/'lef/NangateOpenCellLibrary.macro.mod.lef')+'}',
                'read_verilog {'+str(mapped/'mapped.v')+'}', 'link_design block_v2_n',
                'create_clock -name core -period 3.333333333333 [get_ports clk]',
                'set_input_transition 0.05 [all_inputs]', 'read_vcd -scope dut {'+str(wave)+'}',
                'report_activity_annotation', 'report_power -digits 9'])+'\n'
            script=path/(name+'.tcl');script.write_text(tcl)
            with (path/(name+'.log')).open('w') as stream:
                subprocess.run(['openroad','-no_init','-threads','4','-exit',str(script)], stdout=stream, stderr=subprocess.STDOUT, check=True)
            log=(path/(name+'.log')).read_text()
            totals=re.findall(r'(?m)^Total\s+([\d.eE+-]+)\s+([\d.eE+-]+)\s+([\d.eE+-]+)\s+([\d.eE+-]+)',log)
            annotation=re.findall(r'Annotated (\d+) pin activities\.',log)
            if len(totals)!=1 or len(annotation)!=1 or re.search(r'(?m)^(Error:|\[ERROR)',log):
                raise ValueError('power output invalid')
            if 'problem parsing bus' in log:
                raise ValueError('VCD bus declaration rejected')
            if int(annotation[0]) < sum(len(p['bits']) for p in ports.values()):
                raise ValueError('incomplete boundary annotation')
            powers[name]=dict(power_w=dict(zip(('internal','switching','leakage','total'),map(float,totals[0]))),
                              annotated=int(annotation[0]),wave_sha256=digest(wave),power_log_sha256=digest(path/(name+'.log')))
        window_ps=((end-start)+1)//3
        result=dict(signature=sample['signature'], words=words, factor=factor, rtl_factor_equal=True,
                    window_ps=window_ps, n_leaf_commands=words+3, power=powers,
                    incremental_nj=(powers['active']['power_w']['total']-powers['idle']['power_w']['total'])*window_ps/1000,
                    input_sha256=digest(path/'vectors.txt'),run_log_sha256=digest(path/'run.log'))
        (path/'receipt.json').write_text(json.dumps(result,indent=2)+'\n')
        results.append(result)
        print('RMS_N_CALIBRATION_SAMPLE_PASS',index,sample['signature'],flush=True)
    result=dict(scope='N core RMS begin/stats/finalize/factor only; E, scan/apply wrappers and SRAM excluded',
                synthetic=args.smoke, clock_mhz=300, wire_parasitics_loaded=False,
                activity='RTL boundary VCD propagated through mapped cells; no internal gate replay',
                timing_signoff=False, mapped_netlist_sha256=digest(mapped/'mapped.v'),
                liberty_sha256=digest(lib), capture_sha256=digest(args.capture) if args.capture else None,
                verilator_sha256=digest(executable), testbench_sha256=digest(args.bundle/'tb_rms_n_activity.sv'),
                samples=results)
    (out/'calibration.json').write_text(json.dumps(result,indent=2)+'\n')
    print('RMS_N_CALIBRATION_PASS',len(results),flush=True)


if __name__ == '__main__':
    main()
