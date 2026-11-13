"""Register finite native loops as event services with explicit boundary leases."""
from collections import defaultdict
from copy import deepcopy

from canonicalize import canonicalize
from event_deploy import digest
from streaming_ir import compile_graph
from verify_primitive_cost import verify as verify_native


def lower(model, hardware, primitive_program, profile):
    """Reuse the typed front end and keep repeat bodies compact in the search."""
    if not model.get('sha256') or primitive_program['source_sha256'] != model['sha256']:
        raise ValueError('integer program is from a different model')
    if 'event_model' in hardware:
        raise ValueError('finite-loop lowering needs the native resource inventory')
    model = canonicalize(model)
    primitives = primitive_program['instructions']
    formats = {**primitive_program['initial_formats'], **{node['id']: node for node in primitives}}
    trace = [
        {'id': task['id'], 'shape': model['values'][task['outputs'][0]]['shape'],
         'exponent': formats[primitive_program['value_bindings'][task['outputs'][0]]]['exponent']}
        for task in model['tasks']
    ]
    ir = compile_graph(model, hardware, trace, profile, primitive_program)
    audit = verify_native(ir)
    if not audit['passed']:
        raise ValueError('native finite-loop contract failed verification')
    resolved = ir['hardware']
    by_task = {row['id']: row for row in ir['program'] if 'body' in row}
    primitive_ids = defaultdict(list)
    for node in primitives:
        primitive_ids[node['kernel']].append(node['id'])
    groups = {}
    site_inventory = {}
    for name, group in resolved['leaf_inventory'].items():
        site = group['site']
        resolved['sites'][site]['bytes'] = 16 * resolved['sites'][site]['words']
        groups[name] = {'site': site}
        site_inventory[site] = group
    if 'control_groups' not in resolved:
        resolved['control_groups'] = groups
    placement = {info['site']: name for name, info in resolved['control_groups'].items()}
    if placement.keys() != site_inventory.keys() or len(placement) != len(resolved['control_groups']):
        raise ValueError('finite-loop groups differ from the native control sites')
    spec = {'kind': 'qualified-event-model-v1', 'windows': {}, 'services': {}, 'routes': {},
            'value_bytes': {}, 'native_loop_library': {
                'source_model_sha256': model['sha256'],
                'integer_program_sha256': digest(primitive_program),
                'dependencies': {task['id']: task['after'] for task in ir['tasks']},
                'templates': ir['native_templates'], 'program': primitive_program,
                'external_regions': ir['external_regions'], 'primitive_regions': ir['primitive_regions'],
                'constants': ir['native_constants'], 'operands': ir['native_operand_components'],
                'address_views': [row['address_view'] for row in ir['program'] if 'address_view' in row],
                'offline_weight_recipes': model.get('offline_weight_recipes', []),
                'abi': ir['native_call_abi'], 'scope': ir['timing_scope']}}
    tasks = []
    for task in ir['tasks']:
        source = by_task[task['id']]
        bindings = []
        for original in task['bindings']:
            binding = deepcopy(original)
            service = task['id'] + '@' + binding['id']
            if service in spec['services']:
                raise ValueError('duplicate native loop binding')
            footprint = binding['scratch_by_site']
            sites = {site: {'control': placement[site], 'base_word': 0, 'words': count}
                     for site, count in footprint.items()}
            for site in sites:
                if site_inventory[site]['io_resource'] not in binding['resources']:
                    raise ValueError('native loop scratch lacks its site IO lease')
            spec['services'][service] = {
                'ticks': binding['ticks'], 'claims': dict.fromkeys(binding['resources'], 1),
                'nets': binding['nets'], 'read_bytes': binding['external_read_words'] * 16,
                'write_bytes': binding['external_write_words'] * 16, 'finite_loop': {
                    'task_id': task['id'],
                    'body': source['body'], 'primitives': primitive_ids[task['id']],
                    'macro_binding': binding['macro_binding'], 'participants': sites,
                    'io_site': binding['site'], 'scratch_layout': source['S_layout'],
                    'scratch_external': source['temporary_external_region'],
                    'completion': 'native_loop_final_ack',
                },
            }
            binding['nets'] = []
            binding['event_stages'] = [{'service': service}]
            bindings.append(binding)
        tasks.append({'id': task['id'], 'after': task['after'], 'bindings': bindings})
    resolved['event_model'] = spec
    return {'tasks': tasks}, resolved, audit
