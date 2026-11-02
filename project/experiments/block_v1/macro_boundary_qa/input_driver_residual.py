"""Explain input slack residuals; never correct observations or qualify a model.

Finite contract: the canonical single-clock T6K SDC, ideal parent wires,
split models from the native-driver probe, one component per input context.
"""
import argparse
import json
from pathlib import Path
import re

from audit import require, file_sha, load_json
from candidate_request import validate_binding
from native_pair import verify, scalar


def input_delays(sdc):
    pattern = re.compile(r'set_input_delay ([0-9.eE+-]+) -clock \[get_clocks \{core\}\] -(min|max) -add_delay \[get_ports \{([^{}]+)\}\]')
    result = {}
    for line in sdc.splitlines():
        if line.strip().startswith('set_input_delay'):
            match = pattern.fullmatch(line.strip())
            require(match is not None, 'unsupported input delay syntax')
            value, analysis, pin = match.groups()
            key = (pin, analysis)
            require(key not in result, 'duplicate input delay')
            result[key] = scalar(value)
    require(result, 'missing input delays')
    return result


def components(log):
    result = {}
    for line in log.splitlines():
        if line.startswith('QA127_DRIVER_COMPONENT\t'):
            row = line.split('\t')
            require(len(row) == 5 and row[2] in ('^', 'v') and row[3] in ('min', 'max'), 'malformed component')
            _, pin, edge, analysis, value = row
            key = (pin, {'^': 'rise', 'v': 'fall'}[edge], analysis)
            require(key not in result, 'duplicate component')
            result[key] = scalar(value) * 1e9
    require(result, 'missing native components')
    return result


def decompose(flat, abstract, native, delays):
    def indexed(observed):
        rows = [r for r in observed['observations'] if r['key'][0] == 'input']
        indexed = {tuple(r['key']): r for r in rows}
        require(len(indexed) == len(rows) and rows, 'duplicate/missing input observation')
        return indexed
    full, macro = indexed(flat), indexed(abstract)
    require(full.keys() == macro.keys(), 'input observation coverage')
    require(set(native) == {key[1:] for key in full}, 'native component coverage')
    require(set(delays) == {(key[1], key[3]) for key in full}, 'SDC delay coverage')
    rows = []
    for key, a in macro.items():
        _, pin, edge, analysis = key
        require(a['startpoint'] == pin and full[key]['startpoint'] == pin, 'input path start identity')
        source = native[(pin, edge, analysis)]
        parent = scalar(a['arrival_ns']) - delays[(pin, analysis)]
        predicted = (source - parent) * (1 if analysis == 'max' else -1)
        actual = scalar(a['slack_ns']) - scalar(full[key]['slack_ns'])
        rows.append({'pin': pin, 'edge': edge, 'analysis': analysis,
            'source_component_ps': source * 1000, 'parent_component_ps': parent * 1000,
            'actual_slack_delta_ps': actual * 1000, 'predicted_slack_delta_ps': predicted * 1000,
            'unexplained_residual_ps': (actual - predicted) * 1000})
    slew = {}
    for direction in ('input', 'output'):
        values = [abs(x-y)*1000 for pin, a in flat['ports'].items() if a['direction'] == direction
                  for x, y in zip(a['slew_ns'], abstract['ports'][pin]['slew_ns'])]
        slew[direction] = {'coordinates': len(values), 'maximum_absolute_difference_ps': max(values),
                          'over_original_1ps_diagnostic_count': sum(v > 1 for v in values)}
    return {'input_observation_count': len(rows), 'rows': rows, 'port_slew': slew,
            'maximum_unexplained_residual_ps': max(abs(r['unexplained_residual_ps']) for r in rows),
            'worst_actual': sorted(rows, key=lambda r: -abs(r['actual_slack_delta_ps']))[:4],
            'qualified_hard_macro': False, 'flat_abstract_boundary_qualified': False,
            'scope': 'Explanation of recorded input aggregate slack only; observations and existing acceptance result unchanged; component log rounded to six significant digits'}


def execute(probe, measured):
    probe, measured = Path(probe).resolve(), Path(measured).resolve()
    request_path = probe/'probe-request.json'
    proof = load_json((probe/'probe-receipt.json').read_bytes())
    require(proof['schema'] == 'block-v1-candidate-split-probe/1' and proof['passed'] is True, 'probe receipt')
    sealed = {Path(p): sha for p, sha in proof['inputs'].items()}
    sealed.update({probe/name: sha for name, sha in proof['outputs'].items()})
    require(all(file_sha(p) == sha for p, sha in sealed.items()), 'probe inputs/outputs changed')
    request = load_json(request_path.read_bytes())
    require(request['evidence_kind'] == 'native-control' and request['macro_delay_model'] == 'split-min-max'
            and request['abstract_parent_interconnect'] == 'ideal', 'residual probe scope')
    origins = [p for p, sha in sealed.items() if sha == request['probe_origin_request_sha256']]
    require(len(origins) == 1, 'original candidate request coverage')
    original = load_json(origins[0].read_bytes())
    paths = {r: (origins[0].parent/e['path']).resolve() for r, e in original['files'].items()}
    require(validate_binding(original, paths) == proof['original_candidate_binding'], 'original candidate binding')
    binding = verify(measured, request_path)
    require(binding['receipt_sha256'] == proof['measurement']['receipt_sha256'], 'probe measurement identity')
    views = [load_json((measured/v/'observed.json').read_bytes()) for v in ('flat', 'abstract')]
    require(proof['measurement']['context_accepted'] is True, 'measurement context')
    native = components((probe/'max.log').read_text())
    require(native == components((probe/'min.log').read_text()), 'different native export contexts')
    result = decompose(*views, native, input_delays(paths['sdc'].read_text()))
    result.update(schema='block-v1-input-driver-residual/1', derivation_completed=True,
        producer_sha256=file_sha(Path(__file__)), native_measurement_binding=binding,
        inputs={str(p): file_sha(p) for p in [probe/'probe-receipt.json', measured/'receipt.json',
            measured/'flat/observed.json', measured/'abstract/observed.json', probe/'max.log', probe/'min.log', paths['sdc']]})
    require(all(file_sha(p) == sha for p, sha in sealed.items()), 'probe changed during analysis')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('probe', 'measured', 'output'): parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args()
    result = execute(args.probe, args.measured)
    with args.output.open('x', encoding='utf-8') as output:
        output.write(json.dumps(result, indent=2, allow_nan=False)+'\n')
    print(json.dumps({key: result[key] for key in ('input_observation_count', 'maximum_unexplained_residual_ps', 'port_slew')}))
