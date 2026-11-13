"""Exercise both search policies against real U late-port endpoint views."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import sys

from event_deploy import handoff
from run import compile_event_graph, load_module, retry_event_graph, write
from test_event_compiler import fixture as transfer_graph


def fixture():
    groups = ('U0', 'U1')
    fmt = {'shape': [8], 'dtype': 'INT16', 'format': {'bits': 16, 'exponent': -10, 'lanes': 8}}
    inputs = ['x', 'gamma', 'bias']
    outputs = ['y' + str(i) for i in range(36)]
    graph = {'inputs': inputs, 'outputs': outputs[-1:], 'values': dict.fromkeys(inputs + outputs, fmt),
             'tasks': [{'id': 'row-' + str(i), 'op': 'NReplayEPair', 'attributes': {'parity': i % 2},
                        'inputs': [outputs[i-1] if i else 'x', 'gamma', 'bias'],
                        'outputs': [output]} for i, output in enumerate(outputs)]}
    hardware = {'topology_id': 'u-pair-physical-endpoint-regression', 'sites': {}, 'resources': {},
                'control_groups': {}, 'nets': {}}
    event = {'kind': 'qualified-event-model-v1', 'windows': {}, 'services': {}, 'routes': {},
             'recipes': [], 'initial_copies': {}}
    hardware['event_model'] = event
    for index, group in enumerate(groups):
        site = group + '.S'
        hardware['sites'][site] = {'bytes': 16384, 'words': 1024}
        hardware['control_groups'][group] = {'site': site}
        ports = dict.fromkeys((group + suffix for suffix in ('.N', '.E', '.S.port', '.LC')), 1)
        hardware['resources'].update(ports)
        for slot, name in enumerate(('even', 'odd', 'gamma', 'bias')):
            event['windows'][group + '.' + name] = {'site': site, 'offset': slot * 16, 'bytes': 16}
        for name, value in (('even', 'x'), ('gamma', 'gamma'), ('bias', 'bias')):
            event['initial_copies'][group + '.' + name] = value
        demand = group + '.N_to_E'
        hardware['nets'][demand] = {'cost': 1, 'signals': [
            {'name': 'data', 'width': 128, 'driver': group + '/n_to_e_data[{bit}]',
             'sinks': [group + '/e_direct_a_data[{bit}]']},
            {'name': 'valid', 'width': 1, 'driver': group + '/n_to_e_valid',
             'sinks': [group + '/e_direct_a_valid']},
            {'name': 'ready', 'width': 1, 'driver': group + '/e_direct_a_ready',
             'sinks': [group + '/n_to_e_ready']},
        ]}
        service = group + '.native_pair'
        event['services'][service] = {'ticks': 6 + index * 2, 'claims': ports,
                                      'control_site': site, 'nets': [demand]}
        for parity, (source, target) in enumerate((('even', 'odd'), ('odd', 'even'))):
            event['recipes'].append({'op': 'NReplayEPair', 'attributes': {'parity': parity},
                'inputs': [fmt] * 3, 'outputs': [fmt], 'binding': {
                    'id': service, 'site': site, 'event_stages': [{
                        'service': service, 'input_policy': 'resident',
                        'inputs': {group + '.' + source: 'in:0', group + '.gamma': 'in:1', group + '.bias': 'in:2'},
                        'outputs': {group + '.' + target: 'out:0'},
                    }],
                }})
    return graph, hardware


def rules(base, stack):
    geometry = stack['geometry_um']
    dbu = base['dbu_per_micron']
    convert = lambda microns: round(microns * dbu)
    via = {'cut': convert(geometry['cut_width']), 'spacing': convert(geometry['cut_spacing']),
           'lower_enclosure': convert(geometry['enclosure']), 'upper_enclosure': convert(geometry['enclosure'])}
    return {'technology': {'bounds': base['bounds_dbu'], 'origin': [convert(geometry['track_offset_x']),
             convert(geometry['track_offset_y'])], 'pitch': convert(
                stack['placement_start']['regular_via_center_pitch_um']),
             'width': convert(geometry['width']), 'spacing': convert(geometry['spacing']),
             'via10': via, 'via11': via}}


def product_cases(contract, adapter, validate, route, verify):
    """Run the two-output contract on a synthetic physical base."""
    graph, hardware = transfer_graph(4)
    link = 'P0-P1'
    groups = ('P0', 'P1')
    hardware['control_groups'] = {name: {'site': name, 'control_net': f'control.{name}'} for name in groups}
    for group in groups:
        hardware['nets'][f'control.{group}'] = {'cost': 1, 'signals': [
            {'name': 'command', 'width': 1, 'driver': f'mother.cmd.{group}', 'sinks': [f'{group}.control.cmd']},
            {'name': 'done', 'width': 1, 'driver': f'{group}.control.done', 'sinks': [f'mother.done.{group}']},
        ]}
    hardware['event_model']['routes']['direct'].update(
        transport_abi='ready-valid-commit', transport_width_bits=128)
    base = {'schema_version': contract.VERSION, 'base_id': 'synthetic-product',
            'state': 'candidate', 'dbu_per_micron': 1, 'endpoints': {}, 'fixed_native_nets': {},
            'views': {kind: {'path': f'fixture.{kind}', 'sha256': '0' * 64} for kind in ('odb', 'netlist', 'gds')}}
    from event_deploy import route_catalog

    _, _, members, _ = contract.expand(dict.fromkeys(hardware['nets'], []), route_catalog(hardware))
    for index, member in enumerate(members):
        for pin, role, x in [(member['driver'], 'driver', 20), (member['sinks'][0], 'sink', 100)]:
            y = 20 + index * 10
            base['endpoints'][pin] = {'odb_term': pin, 'native_net': pin, 'role': role,
                'assembly': pin.split('.')[0], 'm10_shapes': [
                    {'layer': 'M10', 'object': pin, 'rect_dbu': [x - 2, y - 2, x + 2, y + 2]},
                ]}
    via = {'cut': 2, 'spacing': 2, 'lower_enclosure': 0, 'upper_enclosure': 0}
    technology = {'technology': {'bounds': [0, 0, 120, 1400], 'origin': [0, 0],
                                  'pitch': 10, 'width': 2, 'spacing': 2, 'via10': via, 'via11': via}}

    def checked(result, current=base, budget=3):
        return handoff(result, result['resolved_hardware'], current, contract, adapter, technology,
                       validate, wire_budget=budget)

    report = []
    for width in (1, 8):
        good = compile_event_graph(graph, hardware, budget=3, width=width, route_target=(base, contract))
        receipt, request, spec = checked(good)
        routed = verify(spec, route(spec, rounds=1, max_expansions=500))
        if (receipt['status'] != 'ready_for_algorithm_2' or routed['nets_checked'] != 135
                or any(not request['users'][f'control.{group}'] for group in groups)):
            raise AssertionError('incomplete product handoff')
        rejected = {}
        for case in ('empty_wiring', 'wrong_target', 'wrong_completion', 'wrong_event', 'wrong_base', 'wrong_plan'):
            attempt = deepcopy(good)
            current = deepcopy(base)
            outputs = attempt['outputs']
            event = outputs['wiring']['users'][link][0]['event_id']
            if case == 'empty_wiring':
                outputs['wiring']['users'].clear()
                outputs['wiring']['members'].clear()
            elif case == 'wrong_target':
                outputs['program']['mother'][event]['targets'] = ['P0']
            elif case == 'wrong_completion':
                for commands in outputs['program']['locals'].values():
                    for command in commands:
                        if command['sequence'] == event:
                            command['required_completion'] = 'source_sent'
            elif case == 'wrong_event':
                outputs['wiring']['users'][link][0]['event_id'] = event + 1
            elif case == 'wrong_plan':
                attempt['plan']['nets'].clear()
            else:
                current['base_id'] = 'replacement-base'
            try:
                checked(attempt, current)
            except ValueError as exc:
                rejected[case] = str(exc)
            else:
                raise AssertionError(f'handoff accepted {case}')
        for case in ('no_control', 'no_done', 'no_ack', 'no_abi', 'missing_pin', 'wrong_owner',
                     'wrong_ack_owner', 'wrong_width', 'false_prewire', 'aliased_ack', 'remote_operand'):
            candidate, current = deepcopy(hardware), deepcopy(base)
            if case == 'no_control':
                del candidate['control_groups']['P1']['control_net']
            elif case == 'no_done':
                candidate['nets']['control.P1']['signals'].pop()
            elif case == 'no_ack':
                candidate['nets'][link]['signals'].pop()
            elif case == 'no_abi':
                del candidate['event_model']['routes']['direct']['transport_abi']
            elif case == 'missing_pin':
                del current['endpoints']['P1.control.cmd']
            elif case == 'wrong_owner':
                candidate['control_groups']['P1']['control_net'] = 'control.P0'
            elif case == 'wrong_ack_owner':
                current['endpoints']['P1.ack']['assembly'] = 'P0'
            elif case == 'wrong_width':
                candidate['nets'][link]['signals'][0]['width'] = 64
            elif case == 'false_prewire':
                candidate['nets'][link]['fixed'] = True
            elif case == 'remote_operand':
                candidate['event_model']['services']['increment']['control_site'] = 'P1'
            else:
                current['endpoints']['P1.ack']['native_net'] = 'P1.ready'
            attempt = compile_event_graph(graph, candidate, budget=3, width=width,
                                          route_target=(current, contract))
            if attempt['status'] == 'planned':
                raise AssertionError(f'product mapping accepted {case}')
            rejected[case] = attempt['status']
        report.append({'width': width, 'nets_routed': routed['nets_checked'],
                       'control_uses': {f'control.{group}': len(request['users'][f'control.{group}'])
                                        for group in groups}, 'negative_controls': rejected})
    fabric = {'schema_version': 'block-event-control-fabric/1', 'mother': 'MC',
              'targets': {}, 'bundles': {}}
    candidate = deepcopy(hardware)
    current = deepcopy(base)
    for number, group in enumerate(groups):
        name = f'control.{group}'
        del candidate['control_groups'][group]['control_net']
        bundle = candidate['nets'].pop(name)
        local = f'{group}.LC'
        fabric['targets'][group] = {'target_id': number, 'controller': local, 'bundles': [name]}
        command, done = bundle['signals']
        for signal, source, target in ((command, f'MC/cmd.{group}', f'{local}/cmd'),
                                       (done, f'{local}/done', f'MC/done.{group}')):
            current['endpoints'][source] = current['endpoints'].pop(signal['driver'])
            current['endpoints'][target] = current['endpoints'].pop(signal['sinks'][0])
            signal.update(driver=source, sinks=[target], role=signal['name'])
        fabric['bundles'][name] = bundle
        bundle['requires'] = ['control.shared']
    fabric['bundles']['control.shared'] = {'cost': 1, 'signals': [
        {'name': 'enable', 'width': 1, 'driver': 'MC/enable', 'sinks': ['distributor/enable']},
    ]}
    for pin, role, x in [('MC/enable', 'driver', 20), ('distributor/enable', 'sink', 100)]:
        current['endpoints'][pin] = {'odb_term': pin, 'native_net': pin, 'role': role,
            'assembly': pin.split('/')[0], 'm10_shapes': [
                {'layer': 'M10', 'object': pin, 'rect_dbu': [x - 2, 1368, x + 2, 1372]},
            ]}
    del candidate['control_groups']
    candidate['event_model']['routes']['direct']['transport_owners'] = ['P0.S', 'P1.S']
    for pin, endpoint in current['endpoints'].items():
        if '/' not in pin:
            endpoint['assembly'] += '.S'
    for width in (1, 8):
        mapped = compile_event_graph(graph, candidate, budget=4, width=width,
                                     route_target=(current, contract), control_fabric=fabric)
        receipt, request, spec = checked(mapped, current, budget=4)
        routed = verify(spec, route(spec, rounds=1, max_expansions=500))
        connectivity = mapped['outputs']['control_connectivity']
        if (receipt['status'] != 'ready_for_algorithm_2' or routed['nets_checked'] != 136
                or connectivity['controllers'] != {'P0': 'P0.LC', 'P1': 'P1.LC'}
                or request['dependencies'] != [['control.P0', 'control.shared'], ['control.P1', 'control.shared']]):
            raise AssertionError('declared control fabric did not reach Algorithm 2')
        corrupted = deepcopy(mapped)
        corrupted['outputs']['control_connectivity']['targets']['P1'] = 2
        try:
            checked(corrupted, current, budget=4)
        except ValueError as exc:
            if str(exc) != 'control connectivity differs from verified event plan':
                raise
        else:
            raise AssertionError('accepted a mutated control target ID')
        absent = deepcopy(current)
        del absent['endpoints']['P1.LC/cmd']
        blocked = compile_event_graph(graph, candidate, budget=4, width=width,
                                      route_target=(absent, contract), control_fabric=fabric)
        if blocked['status'] == 'planned':
            raise AssertionError('accepted a missing local controller endpoint')
        feedback = {'source': mapped['outputs']['wiring']['source'], 'trial_exclude': ['control.P0']}
        replacement = {**current, 'base_id': 'replacement-base'}
        for target in (None, (replacement, contract)):
            try:
                retry_event_graph(graph, candidate, mapped, feedback, width=width, route_target=target)
            except ValueError as exc:
                if 'previous physical base' not in str(exc):
                    raise
            else:
                raise AssertionError('applied feedback outside the previously qualified base')
        alternative_base = compile_event_graph(graph, candidate, budget=4, width=width,
                                               route_target=(replacement, contract), control_fabric=fabric)
        try:
            retry_event_graph(graph, candidate, alternative_base, feedback, width=width,
                              route_target=(replacement, contract))
        except ValueError as exc:
            if 'selected plan and bottom topology' not in str(exc):
                raise
        else:
            raise AssertionError('replayed feedback from a different base with the same logical topology')
        retried = retry_event_graph(graph, candidate, mapped, feedback, width=width,
                                    route_target=(current, contract))
        if retried['status'] == 'planned':
            raise AssertionError('accepted a plan without a required controller')
        report.append({'width': width, 'fabric': 'declared', 'nets_routed': routed['nets_checked'],
                       'controllers': connectivity['controllers'], 'missing_endpoint': blocked['status']})
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('base', 'stack', 'contract', 'adapter', 'output'):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    contract = load_module('handoff_route_contract', args.contract)
    module_path = sys.path[:]
    try:
        adapter = load_module('handoff_router_adapter', args.adapter)
    finally:
        sys.path[:] = module_path
    validate = load_module('handoff_router_geometry', args.adapter.with_name('geometry.py')).validate
    sys.path.append(str(args.adapter.resolve().parent))
    route = load_module('handoff_router_search', args.adapter.with_name('search.py')).route
    verify = load_module('handoff_router_check', args.adapter.with_name('check.py')).verify
    base = contract.read_base(args.base)
    technology = rules(base, json.loads(args.stack.read_text(encoding='utf-8')))
    graph, hardware = fixture()
    args.output.mkdir()
    write(args.output / 'graph.json', graph)
    write(args.output / 'hardware.json', hardware)
    write(args.output / 'technology.json', technology)
    restricted = deepcopy(base)
    restricted['base_id'] += '-access-negative-control'
    u0, u1 = 'U0/e_direct_a_data[0]', 'U1/e_direct_a_data[0]'
    del restricted['endpoints'][u0]
    wrong_direction = deepcopy(base)
    wrong_direction['endpoints'][u0]['role'] = 'driver'
    conflicting = deepcopy(base)
    conflicting['fixed_native_nets'][conflicting['endpoints'][u0]['native_net']] = {
        'driver': 'injected-other-driver',
    }
    disconnected = deepcopy(restricted)
    del disconnected['endpoints'][u1]
    cases = []
    for width in (1, 8):
        no_plan = compile_event_graph(graph, hardware, budget=1, width=width,
                                      route_target=(disconnected, contract), route_scope='interface')
        if no_plan['status'] == 'planned':
            raise AssertionError('physical admission accepted two disconnected alternatives')
        for current, group, case in ((base, 'U0', 'baseline'), (restricted, 'U1', 'missing-pin'),
                                     (wrong_direction, 'U1', 'wrong-direction'),
                                     (conflicting, 'U1', 'multiple-drivers')):
            result = compile_event_graph(graph, hardware, budget=1, width=width,
                                         route_target=(current, contract), route_scope='interface')
            outputs = result['outputs']
            receipt, request, router_input = handoff(result, result['resolved_hardware'],
                                                     current, contract, adapter, technology, validate, wire_budget=1)
            if (receipt['status'] != 'interface_ready_for_algorithm_2' or len(request['members']) != 130
                    or len(router_input['nets']) != 130 or len(request['users'][group + '.N_to_E']) != 36
                    or set(outputs['program']['locals']) != {group}
                    or set(result['plan']['nets']) != {group + '.N_to_E'}):
                raise ValueError('wrong selected handoff or missing endpoint connectivity')
            corrupt = deepcopy(outputs)
            corrupt['wiring']['users'][group + '.N_to_E'][0]['event_id'] = 1
            try:
                handoff({**result, 'outputs': corrupt}, result['resolved_hardware'],
                        current, contract, adapter, technology, validate, wire_budget=1)
            except ValueError as exc:
                if str(exc) != 'connection demands differ from verified event plan':
                    raise
            else:
                raise ValueError('router handoff accepted a demand linked to the wrong dispatch')
            directory = args.output / f'{group}-width-{width}-{case}'
            directory.mkdir()
            for name, data in (*outputs.items(), ('requirements', request), ('handoff', receipt),
                               ('algorithm2-input', router_input)):
                write(directory / (name + '.json'), data)
            cases.append({'group': group, 'width': width, 'case': case, 'dispatches': len(result['plan']['tasks']),
                          'bit_nets': len(router_input['nets']), 'status': receipt['status'],
                          'source': receipt['source'], 'request_sha256': receipt['request_sha256'],
                          'base_sha256': receipt['base_sha256']})
    write(args.output / 'report.json', {'passed': True, 'cases': cases, 'base_state': base['state'],
          'scope': 'real intragroup endpoint regression and synthetic product handoff',
          'product_cases': product_cases(contract, adapter, validate, route, verify)})
    print(json.dumps(cases))


if __name__ == '__main__':
    main()
