"""Calibrate accepted private-P-S feeder packets, including held A/B and done.

Uses unchanged task-owned RTL/gate models. A valid packet fixture is not an
M/LC service or whole-model energy result. Captured operands supply activity,
while an independent SRAM array and address formula check every packet.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path
import subprocess
import sys


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def unused_debug_bits(netlist):
    """Prove the seven low trace-wire bits have no physical cell references."""
    widths = {'feeder.p_row': 3, 'feeder.queue_row[0]': 3, 'feeder.queue_row[1]': 3,
              '$auto$alumacc.cc:548:replace_alu$1113.P': 2}
    body = netlist.read_text()
    evidence = {}
    for name, width in widths.items():
        pattern = re.compile(re.escape('\\'+name)+r'\s*(\[[^\]]+\])?')
        declaration, physical_references = 0, 0
        for line in body.splitlines():
            for found in pattern.finditer(line):
                if line.strip() == ('wire [%d:0] ' % (width-1))+chr(92)+name+' ;':
                    declaration += 1
                elif found.group(1) == '[%d]' % (width-1):
                    physical_references += 1
                else:
                    raise ValueError('low debug bit has a physical reference: '+name)
        if declaration != 1 or not physical_references:
            raise ValueError('incomplete unused-debug-bit proof: '+name)
        evidence[name] = {'width': width, 'ignored_bits_for_comparison_only': list(range(width-1)),
                          'all_physical_references_are_highest_bit': physical_references}
    return evidence


def vcd_parts(path, unused=()):
    # The original VCD is retained and fed unchanged to every power analysis.
    # Only comparison masks the seven bits proved unconnected in the netlist.
    data = path.read_bytes()
    end = data.index(b'$enddefinitions $end')+len(b'$enddefinitions $end')
    header, values = data[:end], data[end:]
    selected = {}
    for line in header.splitlines():
        fields = line.split()
        if fields[:1] == [b'$var'] and fields[4].decode() in unused:
            selected[fields[3]] = fields[4].decode()
    if set(selected.values()) != set(unused):
        raise ValueError('comparison proof does not cover VCD debug-wire definitions')
    canonical = hashlib.sha256()
    for line in values.splitlines(keepends=True):
        if line.startswith(b'b'):
            fields = line.split()
            if len(fields) == 2 and fields[1] in selected:
                bits = fields[0][1:]
                width = unused[selected[fields[1]]]['width']
                if len(bits) != width or set(bits)-set(b'01'):
                    raise ValueError('expected a concrete trace wire of audited width')
                line = b'b'+bits[:1]+b'0'*(width-1)+b' '+fields[1]+b'\n'
        canonical.update(line)
    return (hashlib.sha256(header).hexdigest(), hashlib.sha256(values).hexdigest(),
            canonical.hexdigest())


def call(args, log):
    with log.open('wb') as out:
        result = subprocess.run(list(map(str, args)), stdout=out, stderr=subprocess.STDOUT)
    if result.returncode:
        raise RuntimeError('failed; see '+str(log))


def functional(log):
    row, = [json.loads(s[11:]) for s in log.read_text().splitlines() if s.startswith('FUNCTIONAL ')]
    if not row['timing']['passed'] or not row['same_final_memory']:
        raise ValueError('feeder functional check failed')
    return row


def main():
    p = argparse.ArgumentParser()
    for name in ('binaries', 'model_archive', 'operands', 'physical', 'liberty', 'bank_liberty', 'old_activity', 'output'):
        p.add_argument(name, type=Path)
    p.add_argument('--cores', type=int, default=1)
    p.add_argument('--host-attempts', type=int, default=1,
                   help='bounded retries only for Python SIGSEGV, never failed validation')
    a = p.parse_args()
    if a.cores < 1 or not 1 <= a.host_attempts <= 3:
        raise ValueError('positive cores required')
    a.output.mkdir(exist_ok=False)
    model_manifest = json.loads((a.model_archive/'manifest.json').read_text())
    for n, item in model_manifest.items():
        if sha(a.model_archive/n) != item['sha256']:
            raise ValueError('accepted compiled model drift')
    if sha(a.physical/'6_final.v') != 'b93d064cb07d3978efe280cbddec91fb2c24d74c932078a808680705ca01e32d':
        raise ValueError('accepted compact P S netlist drift')
    if sha(a.bank_liberty) != '47f8de1c22d27beb51982c73ab745e1f3f2b5a7819e53bcb6da73980ce077189':
        raise ValueError('original bank power library drift')
    unused = unused_debug_bits(a.physical/'6_final.v')
    reference_header = vcd_parts(a.old_activity/'p-read/gate-active-1-143.vcd')[0]
    initials = [(1, 143), (2, 143), (2, 144)]
    cases = [('b1', 1, 4, 1, 1, 0, 0), ('b1-reuse', 1, 4, 1, 1, 1, 0),
             ('b1-stalled', 1, 4, 1, 1, 0, 1), ('b8', 8, 4, 1, 1, 0, 0),
             ('b8-reuse', 8, 4, 1, 1, 1, 0), ('b8-stalled', 8, 4, 1, 1, 0, 1)]
    rows = []
    for name, *parameters in cases:
        out = a.output/name
        out.mkdir()
        timings, gate_values, paths = {}, {}, {}
        for mode in ('active', 'idle'):
            values, compared = [], []
            for kind in ('rtl', 'gate'):
                for initial, seed in initials:
                    label = '%s-%s-%d-%d' % (kind, mode, initial, seed)
                    vcd, log = out/(label+'.vcd'), out/(label+'.log')
                    command = [a.binaries/kind, a.operands, vcd, mode, *parameters,
                               '+verilator+rand+reset+'+str(initial), '+verilator+seed+'+str(seed)]
                    call(command, log)
                    row = functional(log)
                    (out/(label+'.json')).write_text(json.dumps(row, indent=2)+'\n')
                    if mode in timings and row != timings[mode]:
                        raise ValueError('feeder timing or metadata differs across RTL/gate/initialization')
                    timings[mode] = row
                    if kind == 'gate':
                        header, wave, real_bits = vcd_parts(vcd, unused)
                        if header != reference_header:
                            raise ValueError('complete S gate definition header differs from existing physical pin audit')
                        values.append(wave)
                        compared.append(real_bits)
                        if initial == 1 and seed == 143:
                            paths[mode] = (vcd, out/(label+'.json'))
            if len(set(compared)) != 1:
                raise ValueError('physically referenced gate value/timestamp streams differ across three initializations')
            gate_values[mode] = {'raw_sha256': values, 'raw_streams_equal': len(set(values)) == 1,
                                 'physically_referenced_stream_sha256': compared[0]}
        if timings['active']['timing']['window_ps'] != timings['idle']['timing']['window_ps']:
            raise ValueError('active/idle clock windows differ')
        summaries, power_by_initial = {}, {}
        for mode in ('active', 'idle'):
            records = []
            for initial, seed in initials:
                label = 'gate-%s-%d-%d' % (mode, initial, seed)
                vcd, receipt = out/(label+'.vcd'), out/(label+'.json')
                # Retain every failed host attempt. The same input/source must
                # be used; arithmetic, power coverage and validation never change.
                input_hashes = {str(f): sha(f) for f in (vcd, receipt, Path(__file__).with_name('analyze_activity.py'))}
                attempts = []
                for attempt in range(1, a.host_attempts+1):
                    label = '%s-%d-%d-host%d' % (mode, initial, seed, attempt)
                    power, log = out/('power-'+label), out/('analysis-'+label+'.log')
                    command = [sys.executable, '-X', 'faulthandler', Path(__file__).with_name('analyze_activity.py'),
                        a.physical, a.liberty, vcd, receipt, power, '--cores', a.cores,
                        '--scope', 'dut/local_s_p', '--extra-lib', a.bank_liberty,
                        '--escape-sta-backslashes', '--sample-label', 'P S feeder']
                    with log.open('wb') as stream:
                        run = subprocess.run(list(map(str, command)), stdout=stream, stderr=subprocess.STDOUT)
                    if {str(f): sha(f) for f in (vcd, receipt, Path(__file__).with_name('analyze_activity.py'))} != input_hashes:
                        raise ValueError('host retry input/source identity changed')
                    attempts.append({'attempt': attempt, 'returncode': run.returncode,
                                     'log': str(log), 'output': str(power), 'input_sha256': input_hashes})
                    (out/('host-attempts-%s-%d-%d.json' % (mode, initial, seed))).write_text(json.dumps(attempts, indent=2)+'\n')
                    if run.returncode == 0:
                        record = json.loads((power/'receipt.json').read_text())
                        record['host_attempts'] = attempts
                        records.append(record)
                        break
                    if run.returncode != -11 or attempt == a.host_attempts:
                        raise RuntimeError('failed host analysis; see '+str(log))
            power_by_initial[mode] = records
            summaries[mode] = records[0]
            if any(r['power_w'] != records[0]['power_w'] for r in records):
                raise ValueError('unmodified gate activity power differs across three initializations')
        delta = summaries['active']['power_w']['total']-summaries['idle']['power_w']['total']
        if delta < 0:
            raise ValueError('negative feeder energy subtraction; preserve rather than clamp')
        row = {'case': name, 'timing': timings['active']['timing'],
            'gate_RTL_three_initializations_equal': True,
            'physically_referenced_gate_value_timestamp_streams_equal': True,
            'seven_unconnected_trace_bits_comparison_audit': unused,
            'original_audited_VCD_definition_header_sha256': reference_header,
            'incremental_window_j': delta*timings['active']['timing']['window_ps']*1e-12,
            'idle_w': summaries['idle']['power_w']['total'],
            'power': summaries, 'three_initial_power': power_by_initial, 'gate_waveform_sha256': gate_values}
        row['incremental_feeder_job_j'] = row['incremental_window_j']/row['timing']['jobs']
        # Window includes six ordinary quiesce transactions. Their contribution
        # is deliberately retained, not secretly credited as feeder savings.
        row['includes_six_quiesce_transactions'] = True
        (out/'receipt.json').write_text(json.dumps(row, indent=2)+'\n')
        rows.append(row)
        print(json.dumps({k: row[k] for k in ('case', 'timing', 'incremental_feeder_job_j', 'idle_w')}), flush=True)
    result = {'scope': __doc__, 'rows': rows,
        'sources_sha256': {n: sha(Path(__file__).with_name(n)) for n in
            ('s_feeder_activity.cpp', 's_activity.cpp', 's_feeder_activity.py', 'analyze_activity.py')},
        'binary_sha256': {k: sha(a.binaries/k) for k in ('rtl', 'gate')},
        'model_archive_manifest_sha256': sha(a.model_archive/'manifest.json'),
        'operand_sha256': sha(a.operands), 'passed': True,
        'full_model_numeric_qualified': False, 'full_system_timing_qualified': False,
        'total_energy_qualified': False,
        'limitations': ['representative captured packet payloads, not complete M numeric execution',
            'zero-delay activity, no glitches; original Lib/RC retained',
            'idle clocks/leakage are separate; six quiesce transactions retained in increments',
            'existing identical-header/ODB/Lib pin audit reused, not a new physical implementation',
            'no whole-model or M/LC/DMA/interconnect qualification']}
    (a.output/'receipt.json').write_text(json.dumps(result, indent=2)+'\n')


if __name__ == '__main__':
    main()
