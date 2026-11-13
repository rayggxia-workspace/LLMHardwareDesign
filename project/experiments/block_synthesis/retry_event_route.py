"""Try another Algo1 mapping using one source-bound Algo2 routing result."""
import argparse
import json
from pathlib import Path

from event_deploy import emit, route_catalog
from route_contract import digest, elaborate, read_base, require, verify_feedback
from run import compile_event_ir
from verify_cover_frontier import verify


def retry(previous, base, request, router_input, routing, *, nets=(), width=8):
    """Search the previous candidate pool with trial-local demand exclusions."""
    require(previous.get('status') == 'planned', 'route feedback requires a planned event graph')
    model, hardware, plan = (previous[key] for key in ('event_ir', 'resolved_hardware', 'plan'))
    scope, budget = previous['route_scope'], previous['wire_budget']
    require(previous['physical_base_sha256'] == digest(base), 'route feedback uses a different base')
    tasks, covers = model['tasks'], model.get('covers', ())
    verify(tasks, hardware, covers, plan, wire_budget=budget)
    expected = emit(tasks, hardware, covers, plan, physical_base_sha256=previous['physical_base_sha256'])
    require(previous['outputs'] == expected, 'previous program or wiring differs from its plan')
    source = {name + '_sha256': digest(record)
              for name, record in (('ir', model), ('hardware', hardware), ('plan', plan))}
    users = dict(expected['wiring']['users'])
    for name, net in hardware['nets'].items():
        if net.get('fixed'):
            users.setdefault(name, [])
    require(request == elaborate(users, route_catalog(hardware), base, source),
            'router requirements differ from the prior plan')
    require(request['status'] == 'endpoint_binding_complete', 'previous routing request is unresolved')
    context = router_input['context']
    require(context['request_sha256'] == request['sha256']
            and context['base_sha256'] == request['base_sha256'], 'router input differs from the request')
    feedback = routing['feedback']
    verify_feedback(feedback, request)
    physical = routing.get('physical_routes', routing)
    effective_input = routing.get('physical_spec', router_input)
    require(physical['context'] == effective_input['context'] == context
            and physical['spec_sha256'] == digest(effective_input), 'routing result uses different router input')
    if 'admission' in routing:
        require(routing['admission']['base_sha256'] == request['base_sha256']
                and routing['admission']['scope'] == scope, 'Algo2 admission differs from the prior handoff')
    failed = routing['failed']
    observed = {}
    for row in feedback['observations']:
        require(row['category'] == 'search_not_found' and row['spec_sha256'] == physical['spec_sha256'],
                'expected Algo2 search feedback for this input')
        for name in row.get('net_ids', ()):
            require(name not in observed, 'duplicate Algo2 net observation')
            observed[name] = row['code']
    require(observed == failed, 'Algo2 failures and observations differ')
    selected = set(nets)
    require(selected and selected <= observed.keys(),
            'choose failed Algo2 net IDs for an explicit alternate mapping trial')
    members = {member['id']: member['demand_id'] for member in request['members']}
    physical_nets = {row['id']: row for row in request['nets']}
    require(selected <= physical_nets.keys(), 'feedback net has no prior logical demand')
    impacted = {members[member] for name in selected for member in physical_nets[name]['members']}
    spec = hardware['event_model']
    fixed = sorted(name for name in impacted if hardware['nets'][name].get('fixed'))
    excluded = impacted - set(fixed)
    require(excluded, 'selected failures only affect fixed demands')
    retry_hardware = {**hardware, 'event_model': {
        **spec, 'excluded_nets': sorted(excluded | set(spec.get('excluded_nets', ())))}}
    result = compile_event_ir(model, retry_hardware, budget=budget, width=width,
                              emit_dependencies='phase_dependencies' in previous, emit_outputs=True,
                              route_base=base, route_scope=scope,
                              control_fabric=spec.get('control_fabric'))
    for name in ('graph_sha256', 'input_hardware_sha256', 'native_loop_verification'):
        if name in previous:
            result[name] = previous[name]
    result['route_trial'] = {
        'prior': source, 'request_sha256': request['sha256'], 'feedback_sha256': feedback['sha256'],
        'failed_nets': sorted(selected), 'excluded_demands': sorted(excluded), 'fixed_demands': fixed,
        'observed_failure_codes': {name: observed[name] for name in sorted(selected)},
        'hard_constraint': False,
    }
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('result', 'base', 'handoff', 'routing', 'output'):
        parser.add_argument(name, type=Path)
    parser.add_argument('--net', action='append', required=True,
                        help='trial an alternate mapping around this failed physical net ID')
    parser.add_argument('--width', type=int, default=8)
    args = parser.parse_args()

    def read(path):
        return json.loads(path.read_bytes())

    result = retry(read(args.result), read_base(args.base), read(args.handoff / 'requirements.json'),
                   read(args.handoff / 'algorithm2-input.json'), read(args.routing),
                   nets=args.net, width=args.width)
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2, ensure_ascii=False)
        stream.write('\n')
    print(json.dumps({'status': result['status'], 'route_trial': result['route_trial']}, ensure_ascii=False))


if __name__ == '__main__':
    main()
