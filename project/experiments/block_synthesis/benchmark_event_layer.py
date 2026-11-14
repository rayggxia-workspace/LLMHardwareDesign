"""Measure a Qwen decoder layer with its archived executable event contracts."""
import argparse
from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from time import perf_counter

from event_deploy import digest
from event_loop_control import decode, replay
from event_native_range import lower_ranges
from event_native_residency import lower_residency
from run import compile_event_ir


def read(path):
    with path.open() as stream:
        return json.load(stream)


def slice_program(program, ids, layer_path):
    instructions = program['instructions']
    by_id = {op['id']: op for op in instructions}
    scoped = {op['id'] for op in instructions if op['kernel'].startswith(layer_path)}
    outputs = sorted({name for op in instructions if op['id'] not in scoped
                      for name in op['inputs'] if name in scoped})
    outputs.extend(name for name in program['outputs'].values() if name in scoped and name not in outputs)
    if not outputs:
        raise ValueError('no externally visible result at the layer boundary')

    needed, inputs = set(), set()

    def require(name):
        if name in needed or name in inputs:
            return
        op = by_id.get(name)
        if (op is None
                or (op['kernel'] not in ids and
                    not (op['id'] in scoped and op['op'] in ('Constant', 'View', 'Mask')))):
            inputs.add(name)
            return
        needed.add(name)
        for operand in op['inputs']:
            require(operand)

    for op in instructions:
        if op['kernel'] in ids:
            require(op['id'])
    for name in outputs:
        require(name)
    formats = {**by_id, **program.get('predicates', {}), **program['initial_formats']}
    return {**program,
            'instructions': [op for op in instructions if op['id'] in needed],
            'outputs': {name: name for name in outputs},
            'initial_formats': {name: {k: formats[name][k] for k in ('shape', 'exponent', 'bits')
                                       if k in formats.get(name, {})} for name in sorted(inputs)},
            'value_bindings': {value: name for value, name in program['value_bindings'].items()
                               if name in needed or name in inputs}}


def evaluate(event_ir, hardware, layer_path, width, depths, budget, fixture=None, modes=('range',)):
    # Select only the requested workload. Incoming edges define layer inputs
    # already available at the start; keep every intra-layer edge.
    tasks = [deepcopy(task) for task in event_ir['tasks'] if task['id'].startswith(layer_path)]
    if not tasks:
        raise ValueError(f'no tasks under {layer_path}')
    ids = {task['id'] for task in tasks}
    incoming = sorted({parent for task in tasks for parent in task['after']} - ids)
    for task in tasks:
        task['after'] = [parent for parent in task['after'] if parent in ids]

    spec = hardware['event_model']
    source = spec['native_loop_library']
    source_tasks = [op for op in source['program']['instructions'] if op['kernel'].startswith(layer_path)]
    services = {stage['service'] for task in tasks for binding in task['bindings']
                for stage in binding['event_stages']}
    completions = Counter(spec['services'][service].get('finite_loop', {}).get('completion')
                          for service in services)
    arithmetic = slice_program(source['program'], ids, layer_path)
    active = {**hardware, 'event_model': {
        **spec, 'services': {service: spec['services'][service] for service in sorted(services)},
        'native_loop_library': {**source, 'program': arithmetic, 'integer_program_sha256': digest(arithmetic),
                                'dependencies': {task['id']: task['after'] for task in tasks}},
    }}
    whole = {'tasks': tasks}
    ranged, ranged_hardware = lower_ranges(whole, active)
    layouts = {'whole': (whole, active), 'range': (ranged, ranged_hardware)}
    if 'sram' in modes:
        layouts['sram'] = lower_residency(ranged, ranged_hardware)
    if 'force-ddr' in modes:
        layouts['force-ddr'] = lower_residency(ranged, ranged_hardware, spill=True)
    results = []
    reference = None

    def report_overlap(plan, ir, target):
        spans = target['event_model']['native_loop_library'].get('ranges', {})
        if not spans:
            return 0
        ends = {row['id']: row['end'] for row in plan['tasks']}
        starts = {row['id']: row['start'] for row in plan['tasks']}
        last = {}
        for task, span in spans.items():
            last[span['kernel']] = max(last.get(span['kernel'], 0), ends[task])
        return sum(starts[task['id']] < last[spans[parent]['kernel']]
                   for task in ir['tasks'] if task['id'] in spans
                   for parent in task['after'] if parent in spans
                   and spans[parent]['kernel'] != spans[task['id']]['kernel'])

    trials = [(depth, mode) for depth in depths for mode in (modes if depth else ('whole',))]
    for depth, mode in trials:
        started = perf_counter()
        ir, target = layouts[mode]
        result = compile_event_ir(ir, target, width=width, budget=budget,
                                  tile_limit=depth or None, emit_outputs=True)
        seconds = round(perf_counter() - started, 6)
        if result['status'] != 'planned' or not result['verification']['passed']:
            raise ValueError(f'depth {depth}: {result["status"]} or failed verification')
        program = result['outputs']['program']
        decoded = decode(program, result['resolved_hardware'])
        commands = [cmd for local in program['locals'].values() for cmd in local]
        if (len({cmd['sequence'] for cmd in commands if cmd['op'] == 'RUN_LOOP'}) != len(ir['tasks'])
                or len(decoded['instructions']) != len(arithmetic['instructions'])):
            raise ValueError('emitted control does not dispatch the entire layer')
        if fixture:
            import numpy as np

            initial, ids, oracle = fixture
            actual = replay(program, result['resolved_hardware'], initial, ids, oracle)
            if reference is None:
                reference = actual
            if actual.keys() != reference.keys():
                raise ValueError('different final tensor identities')
            for name, value in actual.items():
                if value.exponent != reference[name].exponent:
                    raise ValueError('different output exponent')
                np.testing.assert_array_equal(value.raw, reference[name].raw)
                np.testing.assert_array_equal(value.mask, reference[name].mask)
        plan = result['plan']
        from event_residency_stats import handoff_stats

        residency = handoff_stats(plan, target['event_model'])
        results.append({'mode': mode, 'depth': depth, 'seconds': seconds, 'bit_exact_vs_whole': fixture is not None, 'dispatches': len(program['mother']) - 1,
                        'candidate_bindings': sum(len(task['bindings']) for task in ir['tasks']),
                        'model_ticks': plan['makespan'], 'expanded': plan['expanded'],
                        'merged': plan['merged'], 'pruned': plan['pruned'],
                        'peak_bucket_states': plan['peak_bucket_states'],
                        'depth_pruned': plan.get('tile_depth_pruned', 0),
                        'early_tile_edges': report_overlap(plan, ir, target),
                        'read_bytes': plan['external_read_bytes'],
                        'write_bytes': plan['external_write_bytes'], 'nets': len(plan['nets']),
                        'wire_cost': plan['wire_cost'], **residency})
    return {'layer_path': layer_path, 'width': width, 'wire_budget': budget,
            'tasks': len(tasks), 'integer_instructions': len(source_tasks),
            'input_dependencies': incoming, 'decoded_integer_instructions': len(arithmetic['instructions']), 'source_onnx_sha256': source['source_model_sha256'],
            'integer_program_sha256': source['integer_program_sha256'],
            'automatically_ranged_operators': len({task['tile_parent'] for task in ranged['tasks']
                                                 if 'tile_parent' in task}),
            'tile_owned_tasks': sum('tile_parent' in task for task in ranged['tasks']),
            'native_completion_contracts': dict(completions), 'cases': results}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('event_ir', type=Path)
    parser.add_argument('hardware', type=Path)
    parser.add_argument('--layer-path', required=True)
    parser.add_argument('--width', type=int, default=8)
    parser.add_argument('--budget', type=int, default=10)
    parser.add_argument('--depth', nargs='+', type=int, default=[0, 1, 2, 3])
    parser.add_argument('--numeric-fixture', type=Path, nargs=4, metavar=('ONNX', 'WEIGHTS', 'ACTIVATIONS', 'ORACLE'))
    parser.add_argument('--modes', nargs='+', choices=('range', 'force-ddr', 'sram'), default=['range', 'force-ddr', 'sram'])
    parser.add_argument('--input-ids', type=int, nargs='+', default=[1, 2])
    args = parser.parse_args()
    fixture = None
    oracle = None
    try:
        if args.numeric_fixture:
            if args.depth[0] != 0:
                raise ValueError('numerical comparison requires depth 0 first')
            from frontend import import_onnx
            from full_integer import Interpreter, Oracle
            from wide_program import execute

            onnx, weights_path, calibration, executable = args.numeric_fixture
            model = import_onnx(onnx)
            hardware = read(args.hardware)
            source = hardware['event_model']['native_loop_library']
            if model['sha256'] != source['source_model_sha256']:
                raise ValueError('numeric fixture uses a different graph')
            weights = read(weights_path)
            weights['_root'] = str(weights_path.parent.parent)
            oracle = Oracle([str(executable.resolve())])
            initial = Interpreter(model, weights, read(calibration), oracle).initial
            ids = [args.input_ids]
            embedding = [op for op in source['program']['instructions']
                         if op['op'] == 'Gather' and 'input_ids' in op['inputs']]
            if len(embedding) != 1:
                raise ValueError('expected one input embedding')
            op, = embedding
            initial.update(execute({'instructions': [op], 'outputs': {op['id']: op['id']}},
                                   initial, ids, oracle))
            fixture = initial, ids, oracle
        report = evaluate(read(args.event_ir), read(args.hardware), args.layer_path,
                          args.width, args.depth, args.budget, fixture, args.modes)
    finally:
        if oracle is not None:
            oracle.close()
    if args.numeric_fixture:
        report['input_ids'] = args.input_ids
        report['numeric_manifest_sha256'] = {
            path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in args.numeric_fixture
        }
    report['input_sha256'] = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in (args.event_ir, args.hardware)
    }
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
