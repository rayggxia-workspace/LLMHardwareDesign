"""Measure a Qwen decoder layer with its archived executable event contracts."""
import argparse
from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from time import perf_counter

from event_deploy import digest
from event_loop_control import decode
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


def evaluate(event_ir, hardware, layer_path, width, depths, budget):
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
    results = []
    for depth in depths:
        started = perf_counter()
        # The same frontier and depth check used by typed tile lowering. The
        # native entry currently emits whole commands with no tile-owner tags.
        result = compile_event_ir({'tasks': tasks}, active, width=width, budget=budget,
                                  tile_limit=depth or None, emit_outputs=True)
        seconds = round(perf_counter() - started, 6)
        if result['status'] != 'planned' or not result['verification']['passed']:
            raise ValueError(f'depth {depth}: {result["status"]} or failed verification')
        program = result['outputs']['program']
        decoded = decode(program, result['resolved_hardware'])
        if (len(program['mother']) - 1 != len(tasks)
                or len(decoded['instructions']) != len(arithmetic['instructions'])):
            raise ValueError('emitted control does not dispatch the entire layer')
        plan = result['plan']
        results.append({'depth': depth, 'seconds': seconds, 'dispatches': len(program['mother']) - 1,
                        'candidate_bindings': sum(len(task['bindings']) for task in tasks),
                        'model_ticks': plan['makespan'], 'expanded': plan['expanded'],
                        'merged': plan['merged'], 'pruned': plan['pruned'],
                        'peak_bucket_states': plan['peak_bucket_states'],
                        'depth_pruned': plan.get('tile_depth_pruned', 0),
                        'read_bytes': plan['external_read_bytes'],
                        'write_bytes': plan['external_write_bytes'], 'nets': len(plan['nets']),
                        'wire_cost': plan['wire_cost']})
    return {'layer_path': layer_path, 'width': width, 'wire_budget': budget,
            'tasks': len(tasks), 'integer_instructions': len(source_tasks),
            'input_dependencies': incoming, 'decoded_integer_instructions': len(arithmetic['instructions']), 'source_onnx_sha256': source['source_model_sha256'],
            'integer_program_sha256': source['integer_program_sha256'],
            'qualified_tile_recipes': sum('tile' in recipe for recipe in spec.get('recipes', ())),
            'tile_owned_tasks': sum('tile_parent' in task for task in tasks),
            'native_completion_contracts': dict(completions), 'cases': results}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('event_ir', type=Path)
    parser.add_argument('hardware', type=Path)
    parser.add_argument('--layer-path', required=True)
    parser.add_argument('--width', type=int, default=8)
    parser.add_argument('--budget', type=int, default=10)
    parser.add_argument('--depth', nargs='+', type=int, default=[0, 1, 2, 3])
    args = parser.parse_args()
    report = evaluate(read(args.event_ir), read(args.hardware), args.layer_path,
                      args.width, args.depth, args.budget)
    report['input_sha256'] = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in (args.event_ir, args.hardware)
    }
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
