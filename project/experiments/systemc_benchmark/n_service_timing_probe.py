"""Audit actual N service RTL/gate responses against a clocked SystemC model.

The experiment covers serialized resident commands only. Group arithmetic
answers are checked independently with integer isqrt; Exp answers come from
the frozen native reference. Neither S packet construction nor LC/DMA timing,
full-model quality, power or system performance is qualified here.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rows(path, fields):
    found = {}
    for line in path.read_text().splitlines():
        if line.startswith('ROW '):
            _, index, *values = line.split()
            if int(index) in found or len(values) != fields:
                raise ValueError('duplicate or malformed response: '+str(path))
            found[int(index)] = list(map(int, values))
    return found


def main():
    p = argparse.ArgumentParser()
    for name in ('source', 'runs', 'cached_native_objects', 'frozen', 'output'):
        p.add_argument(name, type=Path)
    a = p.parse_args()
    generation = json.loads((a.source/'generation.json').read_text())
    for name, digest in generation['files_sha256'].items():
        if sha(a.source/name) != digest:
            raise ValueError('fixture/source drift: '+name)
    if sha(a.frozen/'wide_program.py') != '03d68c3a02a73bf2787d05c1222439b0a412a83f8fa8b5178e69631e0f4d95d5':
        raise ValueError('frozen compiler source drift')
    old_source = a.frozen/'streaming_ir.py'
    old = old_source.read_text()
    if "'n_soft_stats':leaf('N','Stats(count=1)'" not in old:
        raise ValueError('legacy Exp recipe has changed; re-audit its semantics')
    fixtures = []
    for line in (a.source/'fixtures.tsv').read_text().splitlines():
        mode, pack, length, expected, *values = map(int, line.split())
        if len(values) != length:
            raise ValueError('truncated N payload')
        if mode in (1, 2):
            sq = sum(x*x for x in values) << 16
            if mode == 1:
                sq //= length
            if expected != (1 << 38)//math.isqrt(sq+(1 << 16)):
                raise ValueError('native factor disagrees with independent integer reference')
        fixtures.append({'mode': mode, 'pack': pack, 'length': length,
                         'expected': expected, 'values': values})
    if len(fixtures) != generation['fixtures']:
        raise ValueError('incomplete generated fixtures')
    wanted = set(range(len(fixtures)))
    previous = None
    inputs = [a.source/name for name in generation['files_sha256']]
    inputs += [a.source/'generation.json', old_source, a.frozen/'wide_program.py', Path(__file__)]
    comparisons = []
    for kind in ('rtl', 'gate'):
        for seed in ('1-143', '2-143', '2-144'):
            path = a.runs/(kind+'-'+seed+'.log')
            actual = rows(path, 2)
            if set(actual) != wanted or any(actual[i][1] != f['expected'] for i, f in enumerate(fixtures)):
                raise ValueError('incomplete or wrong native response: '+str(path))
            result, = [json.loads(line[7:]) for line in path.read_text().splitlines() if line.startswith('RESULT ')]
            if result['services'] != len(fixtures) or not result['exact_response_checks_passed']:
                raise ValueError('native response assertions did not finish')
            if previous is not None and previous != actual:
                raise ValueError('RTL/gate/initialization timing or payload differs')
            previous = actual
            inputs.append(path)
            comparisons.append({'kind': kind, 'initial_seed': seed, 'services': len(actual), 'passed': True})
        inputs += [a.runs/('n-'+kind), a.runs/('build-'+kind+'.log')]
        obj = a.cached_native_objects/('obj-'+kind)
        inputs += [obj/name for name in ('Vblock_v2_n__ALL.a', 'verilated.o', 'verilated_vcd_c.o', 'verilated_threads.o')]
    modeled = rows(a.runs/'systemc.log', 1)
    if set(modeled) != wanted or any(modeled[i][0] != previous[i][0] for i in wanted):
        raise ValueError('independent SystemC timing differs from native responses')
    inputs += [a.runs/'systemc.log', a.runs/'systemc-n-service', a.runs/'build-systemc.log']
    legacy = {tuple(f['values']): f for f in fixtures if f['mode'] == 3}
    exp = []
    for f in fixtures:
        if f['mode'] != 0:
            continue
        before = legacy[tuple(f['values'])]
        if before['expected'] != 32768:
            raise ValueError('one-value maximum did not produce exp(0)')
        exp.append({'input_raw_Q10': f['values'][0], 'legacy_Stats1_result': before['expected'],
                    'correct_Stats2_x_zero_result': f['expected'],
                    'different': before['expected'] != f['expected']})
    if not any(row['input_raw_Q10'] < 0 and row['different'] for row in exp):
        raise ValueError('negative-input lowering gap was not demonstrated')
    a.output.mkdir(exist_ok=False)
    rejections = []
    for i, text in enumerate(('4 1 1\n', '1 0 1\n', '1 9 1\n', '1 1 0\n',
                              '1 1 65536\n', '0 1 2\n', '1 1 1\n1\n', '1 1 1 extra\n')):
        path = a.output/('invalid-%d.tsv'%i)
        path.write_text(text)
        run = subprocess.run([str(a.runs/'systemc-n-service'), str(path)],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (a.output/('invalid-%d.log'%i)).write_bytes(run.stdout+run.stderr)
        if not run.returncode or b'unsupported N service descriptor' not in run.stderr:
            raise ValueError('invalid N descriptor did not fail')
        rejections.append({'descriptor_text': text, 'rejected': True})
    result = {'scope': __doc__, 'passed': True, 'services': len(fixtures),
        'native_comparisons': comparisons, 'native_service_executions': len(fixtures)*6,
        'SystemC_version': '3.0.1', 'clock_hz': 300000000,
        'SystemC_input_contains_no_measured_service_latency': True,
        'different_timings': 0, 'exp_semantic_comparison': exp,
        'invalid_descriptors': rejections,
        'legacy_native_lowering_valid_for_NExp': False,
        'corrected_native_NExp_recipe': 'Begin softmax; Stats(count2, packed [x,0]); Finalize; Exp(count1,x)',
        'packet_formatter_and_LC_lowering_qualified': False,
        'DP_gain_claimed': False, 'hardware_modified': False,
        'full_model_quality_qualified': False, 'system_timing_qualified': False,
        'total_energy_qualified': False, 'inputs_sha256': {str(path): sha(path) for path in inputs}}
    (a.output/'receipt.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({'passed': True, 'native_service_executions': len(fixtures)*6,
                      'SystemC_services': len(modeled), 'different_timings': 0,
                      'legacy_Exp_mismatching_inputs': sum(row['different'] for row in exp)}))


if __name__ == '__main__':
    main()
