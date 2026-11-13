"""Publish one verified Algo1 schedule for routing and native linking."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

from route_contract import digest, elaborate, read_base, require, verify_requirements
from event_deploy import attach_route_catalog, bind_routes, emit
from verify_cover_frontier import verify


SCHEMA = 'algo1-handoff/1'


def source_identity(model, hardware, plan):
    return {'ir_sha256': digest(model), 'hardware_sha256': digest(hardware),
            'plan_sha256': digest(plan)}


def program_images(manifest, source, hardware, artifact_root):
    """Bind binary bytes from a target encoder to its exact schedule and ABI."""
    require(manifest.get('schema_version') == 'algo1-control-images/1', 'unknown control-image manifest')
    require(manifest.get('source') == source, 'control images belong to a different schedule or hardware')
    target = hardware.get('program_target', {})
    controllers = target.get('controllers', {})
    topology = target.get('topology_id')
    require(bool(topology) and manifest.get('topology_id') == topology, 'control topology identity differs')
    require(sum(row.get('level') == 'mother' for row in controllers.values()) == 1
            and any(row.get('level') == 'local' for row in controllers.values()),
            'product requires a mother and local control target')
    images = {}
    used_paths = set()
    root = artifact_root.resolve()
    for image in manifest['images']:
        identity = image['controller']
        require(identity in controllers and identity not in images, 'duplicate or unknown control image target')
        target_controller = controllers[identity]
        require(image['level'] == target_controller['level'] in {'mother', 'local'}
                and image['abi'] == target_controller['abi'], 'control image ABI differs')
        file_name = Path(image['path'])
        path = (root / file_name).resolve()
        require(not file_name.is_absolute() and '..' not in file_name.parts and path.is_relative_to(root)
                and path.is_file() and path not in used_paths, 'invalid or reused image path')
        payload = path.read_bytes()
        require(payload and len(payload) == image['bytes']
                and hashlib.sha256(payload).hexdigest() == image['sha256'],
                'control image bytes differ')
        capacity = target_controller.get('capacity_bytes')
        require(capacity is None or len(payload) <= capacity, 'control image exceeds target capacity')
        used_paths.add(path)
        images[identity] = dict(image, payload_hex=payload.hex())
    require(images.keys() == controllers.keys(), 'incomplete target controller images')
    return [images[identity] for identity in sorted(images)]


def build(model, hardware, plan, catalog, base, rules, bind_request, *,
          route_scope='interface', manifest=None, artifact_root=None, wire_budget=None,
          source_outputs=None):
    require(route_scope in {'interface', 'product'}, 'unknown handoff scope')
    require(plan.get('status') == 'planned', 'handoff requires a planned event schedule')
    source = source_identity(model, hardware, plan)
    tasks, covers = model['tasks'], model.get('covers', ())
    verify(tasks, hardware, covers, plan, wire_budget=wire_budget)
    resolved = attach_route_catalog(hardware, catalog)
    command_source = source_outputs['program']['source'] if source_outputs else {}
    physical_base = command_source.get('physical_base_sha256')
    require(physical_base is None or physical_base == digest(base), 'schedule used a different physical base')
    if route_scope == 'interface' and 'native_service_routes' in base:
        from event_native_dispatch import qualify_native_dispatch

        require(physical_base is not None and qualify_native_dispatch(hardware, base) == hardware,
                'schedule lacks native dispatch qualification for this base')
    if route_scope == 'product' and source_outputs is not None:
        from event_physical_contract import qualify_hardware

        require(physical_base is not None and 'physical_interface_issues' in hardware['event_model']
                and qualify_hardware(hardware, base) == hardware,
                'product schedule lacks physical interface qualification')
    generated = emit(tasks, resolved, covers, plan, physical_base_sha256=physical_base)
    if source_outputs is not None:
        require(resolved == hardware and source_outputs == generated,
                'command and wiring outputs differ from the verified schedule')
    users = dict(generated['wiring']['users'])
    for name, net in resolved['nets'].items():
        if net.get('fixed'):
            users.setdefault(name, [])
    request = elaborate(users, catalog, base, source)
    verify_requirements(request, users, catalog, base, source)
    require(not request['unresolved'], 'unbound physical demands: ' + str(request['unresolved']))
    product = route_scope == 'product'
    if product:
        require(base['state'] == 'frozen', 'product requires frozen native views')
        require({'odb', 'def', 'gds', 'netlist', 'spef'} <= base['views'].keys(),
                'product requires all native physical views')
        require(manifest is not None and artifact_root is not None, 'product requires source-bound control images')
        images = program_images(manifest, source, hardware, artifact_root)
    else:
        require(manifest is None, 'interface handoff consumes event IR only')
        images = []
    spec = bind_request(request, base, rules['technology'], rules.get('obstacles', []))
    program = {'schema_version': SCHEMA, 'source': source,
               'kind': 'target_control_images' if product else 'scheduled_event_ir',
               'decisions': plan['tasks'], 'control_ir': generated['program'],
               'topology_id': hardware.get('program_target', {}).get('topology_id'),
               'images': images, 'native_execution_qualified': False}
    wiring = {'schema_version': SCHEMA, 'source': source, 'members': request['members'],
              'users': request['users'], 'unresolved': []}
    receipt = {'schema_version': SCHEMA, 'route_scope': route_scope,
               'status': 'ready_for_algorithm_2' if product else 'interface_ready_for_algorithm_2',
               'unresolved': [], 'source': source, 'base_sha256': request['base_sha256'],
               'program_sha256': digest(program), 'wiring_sha256': digest(wiring),
               'request_sha256': request['sha256'], 'router_input_sha256': digest(spec),
               'coverage': {'new_signal_nets': sum(bool(net['sinks']) for net in spec['nets']),
                            'static_bit_members': len(request['members']), 'control_images': len(images)},
               'physical_qualified': False}
    files = {'handoff': receipt, 'program': program, 'wiring': wiring,
             'requirements': request, 'algorithm2-input': spec}
    if physical_base is not None:
        native_request = bind_routes(generated['wiring'], resolved, base, elaborate,
                                     verify_requirements, catalog=catalog)
        require(native_request['status'] == 'endpoint_binding_complete',
                'unbound native endpoint demands')
        routing_users = request['users']
        require(all(routing_users.get(name) == uses for name, uses in native_request['users'].items()),
                'native command demands differ from the routing handoff')
        receipt['native_route_request_sha256'] = native_request['sha256']
        files['native-route-requirements'] = native_request
    return files


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('result', 'catalog', 'base', 'rules', 'output'):
        parser.add_argument(name, type=Path)
    parser.add_argument('legacy_args', nargs='*', type=Path, help=argparse.SUPPRESS)
    parser.add_argument('--scope', choices=('interface', 'product'), default='interface')
    parser.add_argument('--control-images', type=Path)
    parser.add_argument('--wire-budget', type=int, help='override the budget recorded in the compiler result')
    parser.add_argument('--upper-router', type=Path,
                        default=Path(__file__).resolve().parents[1] / 'upper_router',
                        help='directory containing the Algorithm 2 adapter.py')
    args = parser.parse_args()
    event_ir = source_hardware = None
    if args.legacy_args:
        if len(args.legacy_args) != 2:
            parser.error('provide RESULT CATALOG BASE RULES OUTPUT, or prefix them with EVENT_IR HARDWARE')
        event_ir, source_hardware = args.result, args.catalog
        args.result, args.catalog, args.base, args.rules, args.output = (
            args.base, args.rules, args.output, *args.legacy_args)
    if not (args.upper_router / 'adapter.py').is_file():
        parser.error('Algorithm 2 adapter.py is missing; pass --upper-router from the router checkout')
    sys.path.insert(0, str(args.upper_router.resolve()))
    from adapter import bind_request

    def load(path):
        return json.loads(path.read_text(encoding='utf-8'))

    try:
        result = load(args.result)
        model = load(event_ir) if event_ir is not None else result.get('event_ir')
        hardware = result.get('resolved_hardware')
        if hardware is None and source_hardware is not None:
            hardware = load(source_hardware)
        require(result.get('status') == 'planned', 'handoff requires a planned event schedule')
        require(model is not None and hardware is not None,
                'result must contain event IR and resolved hardware, or supply EVENT_IR HARDWARE')
        base = read_base(args.base)
        manifest = load(args.control_images) if args.control_images else None
        if 'event_ir' in result:
            require(model == result['event_ir'], 'provided event IR differs from compiler output')
        budget = args.wire_budget if args.wire_budget is not None else result.get('wire_budget')
        files = build(model, hardware, result['plan'], load(args.catalog), base, load(args.rules), bind_request,
                      route_scope=args.scope, manifest=manifest,
                      artifact_root=args.control_images.parent if manifest is not None else None,
                      wire_budget=budget, source_outputs=result.get('outputs'))
        args.output.mkdir(exist_ok=False)
        for name, data in files.items():
            (args.output / (name + '.json')).write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n',
                                                         encoding='utf-8')
    except (OSError, KeyError, ValueError) as error:
        parser.exit(2, str(error) + '\n')


if __name__ == '__main__':
    main()
