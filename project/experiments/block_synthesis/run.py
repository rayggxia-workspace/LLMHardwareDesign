"""Command-line entry point: real ONNX audit or qualified tile compilation."""
import argparse
import hashlib
import json
from pathlib import Path
import time

from cover import propose_covers
from frontend import import_onnx, audit, lower_elementwise
from solver import optimize, Unsupported
from verify import verify
from emit import emit
from memory import attach_virtual_memory
from lowering import lower_registered


def write(path, obj):
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


def compile_model(model, hardware, *, budget=None, seconds=30, rounds=4, cover_limit=8, workers=1):
    """Compile registered services. Return all failures with their exact scope."""
    if hardware.get('native_leaf_profiles') and not model.get('lowered'):
        from leaf_lowering import lower
        graph, hardware = lower(model, hardware)
        variants = [graph]
    else:
        variants = lower_registered(model, hardware)
    best, failures = None, []
    for tiled in variants:
        resolved = attach_virtual_memory(tiled, hardware)
        for graph in propose_covers(tiled, resolved, cover_limit):
            result = optimize(graph, resolved, wire_budget=budget, seconds=seconds, rounds=rounds, workers=workers)
            if 'tasks' not in result:
                failures.append({'tile_elements': tiled.get('tile_elements'), 'cover': graph['cover_trace'],
                                 'status': result['status'], 'scope': 'this candidate cover/tile set only'})
                continue
            check = verify(graph, resolved, result, budget)
            score = (result['makespan'], result['external_words'], result['wire_cost'])
            if best is None or score < best[0]:
                best = (score, graph, result, check, resolved)
    if best is None:
        return {'status': 'no_verified_plan', 'candidate_failures': failures}
    _, graph, result, check, resolved = best
    return {'status': 'planned', 'graph': graph, 'plan': result, 'verification': check,
            'outputs': emit(graph, resolved, result), 'resolved_hardware': resolved,
            'candidate_failures': failures,
            'scope': resolved.get('evaluation_scope', 'algorithm planning under registered services and paths'),
            'acceptance': {'algorithm_plan': True, 'native_control_image_required': False,
                           'native_dma_replay_required': False, 'physical_routing_required': False}}


def compile_event_ir(model, hardware, *, budget=None, width=8, emit_outputs=True, route_target=None,
                     route_scope='product', route_catalog=None, control_fabric=None):
    from cover_frontier import search
    from event_deploy import attach_route_catalog, digest, route_admission
    from verify_cover_frontier import verify as verify_events

    if 'event_model' not in hardware:
        raise ValueError('event IR requires a qualified hardware event model')
    if route_scope not in ('product', 'interface'):
        raise ValueError('unknown event handoff scope')
    declared = hardware.get('control_fabric')
    if control_fabric is not None and declared is not None and control_fabric != declared:
        raise ValueError('conflicting control fabric inputs')
    if control_fabric is None:
        control_fabric = declared
    if control_fabric is not None:
        from event_control_fabric import attach_control_fabric, qualify_endpoint_demands

        hardware = attach_control_fabric(hardware, control_fabric)
    if route_catalog is not None:
        hardware = attach_route_catalog(hardware, route_catalog)
    if control_fabric is not None:
        hardware = qualify_endpoint_demands(hardware)
    if route_target is not None and route_scope == 'product':
        from event_physical_contract import qualify_hardware

        hardware = qualify_hardware(hardware, route_target[0])
    tasks, covers = model['tasks'], model.get('covers', ())
    admit = (route_admission(hardware, *route_target, product=route_scope == 'product')
             if route_target is not None else None)
    plan = search(tasks, hardware, covers, width=width, wire_budget=budget, route_admission=admit)
    result = {'status': plan['status'], 'plan': plan, 'wire_budget': budget,
              'scope': 'qualified event IR and schedule'}
    if control_fabric is not None or route_catalog is not None:
        result['resolved_hardware'] = hardware
    if control_fabric is not None and plan['status'] != 'planned':
        result['logical_control_issues'] = hardware['event_model']['logical_control_issues']
    if route_target is not None:
        result.update(resolved_hardware=hardware, route_scope=route_scope, physical_base_sha256=digest(route_target[0]))
        if plan['status'] != 'planned' and route_scope == 'product':
            result['physical_interface_issues'] = hardware['event_model']['physical_interface_issues']
    if plan['status'] == 'planned':
        result['verification'] = verify_events(tasks, hardware, covers, plan, wire_budget=budget)
        if emit_outputs:
            from event_deploy import emit as emit_events
            result['outputs'] = emit_events(tasks, hardware, covers, plan,
                                            physical_base_sha256=result.get('physical_base_sha256'))
            result['event_ir'] = model
    return result


def compile_event_graph(model, hardware, *, budget=None, width=8, native_loops=None, exclude=(),
                        route_target=None, route_catalog=None, route_scope='product', control_fabric=None):
    from event_deploy import digest

    hardware_sha256 = digest(hardware)
    try:
        if native_loops is None:
            from event_lowering import lower

            if 'event_model' not in hardware:
                raise ValueError('event graph requires a qualified hardware event model')
            lowered, resolved = lower(model, hardware)
        else:
            from event_loop_graph import lower

            lowered, resolved, audit = lower(model, hardware, *native_loops)
    except Unsupported as exc:
        return {'status': 'blocked_lowering', 'reason': str(exc)}
    if exclude:
        spec = resolved['event_model']
        spec['excluded_nets'] = sorted(set(exclude) | set(spec.get('excluded_nets', ())))
    result = compile_event_ir(lowered, resolved, budget=budget, width=width,
                              route_target=route_target, route_scope=route_scope,
                              route_catalog=route_catalog, control_fabric=control_fabric)
    result['scope'] = 'typed graph to verified event plan, control IR and wiring demands'
    if native_loops is not None:
        result['native_loop_verification'] = audit
    result.setdefault('resolved_hardware', resolved)
    result['graph_sha256'] = digest(model)
    result['input_hardware_sha256'] = hardware_sha256
    return result


def retry_event_graph(model, hardware, previous, feedback, *, budget=None, width=8, native_loops=None,
                      route_target=None, route_catalog=None, route_scope='product', control_fabric=None):
    """Try a fresh map excluding selected router demands for this trial."""
    from event_deploy import attach_route_catalog, demand_closure, digest, route_catalog as catalog_from_hardware

    wiring = previous['outputs']['wiring']
    resolved = previous['resolved_hardware']
    if (previous.get('graph_sha256') != digest(model) or feedback['source'] != wiring['source']
            or wiring['source']['plan_sha256'] != digest(previous['plan'])
            or wiring['source']['hardware_sha256'] != digest(resolved)
            or 'input_hardware_sha256' in previous and previous['input_hardware_sha256'] != digest(hardware)):
        raise ValueError('router feedback does not match the selected plan and bottom topology')
    if 'physical_base_sha256' in previous and (
            route_target is None or digest(route_target[0]) != previous['physical_base_sha256']
            or route_scope != previous['route_scope']):
        raise ValueError('router feedback requires the previous physical base and handoff scope')
    exclusions = set(feedback['trial_exclude'])
    nets = resolved['nets']
    if not exclusions or not exclusions <= demand_closure(nets, previous['plan']['nets']):
        raise ValueError('router feedback must identify selected demand IDs')
    if any(nets[name].get('fixed') for name in exclusions):
        raise ValueError('router feedback cannot remove a fixed connection')
    earlier = resolved['event_model'].get('excluded_nets', ())
    previous_fabric = resolved['event_model'].get('control_fabric')
    if control_fabric is not None and control_fabric != previous_fabric:
        raise ValueError('router feedback does not match the control fabric')
    if route_catalog is not None and attach_route_catalog(resolved, route_catalog)['nets'] != nets:
        raise ValueError('router feedback does not match the route catalog')
    if budget is None:
        budget = previous.get('wire_budget')
    result = compile_event_graph(model, hardware, budget=budget, width=width,
                                 native_loops=native_loops, exclude=exclusions | set(earlier),
                                 route_target=route_target, route_catalog=catalog_from_hardware(resolved),
                                 route_scope=route_scope,
                                 control_fabric=previous_fabric)
    result['route_trial'] = {'source': feedback['source'], 'excluded_demands': sorted(exclusions)}
    return result


def load_module(name, path):
    from importlib.util import module_from_spec, spec_from_file_location

    spec = spec_from_file_location(name, path)
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('model', type=Path)
    p.add_argument('hardware', type=Path)
    p.add_argument('output', type=Path)
    p.add_argument('--audit-only', action='store_true')
    p.add_argument('--lowered', action='store_true', help='internal tile IR, not a second author-maintained model format')
    event = p.add_mutually_exclusive_group()
    event.add_argument('--event-ir', action='store_true', help='plan an internal IR with qualified event stages')
    event.add_argument('--event-graph', action='store_true', help='compile a typed operator graph via qualified recipes')
    p.add_argument('--event-control-fabric', type=Path, help='model-independent mother/local control interface JSON')
    p.add_argument('--event-native-program', type=Path, help='typed integer loop program generated from the input model')
    p.add_argument('--event-native-profiles', type=Path, nargs=3, help='native measurement logs for three initial states')
    p.add_argument('--event-native-assembler', type=Path, help='locked native U_64 assembler source')
    p.add_argument('--event-route-base', type=Path, help='route-contract base with verified endpoint views')
    p.add_argument('--event-route-module', type=Path, help='project route_contract.py implementation')
    p.add_argument('--event-route-catalog', type=Path, help='physical templates for logical demand IDs')
    p.add_argument('--event-route-adapter', type=Path, help='Algorithm 2 adapter.py for input admission')
    p.add_argument('--event-route-technology', type=Path, help='Algorithm 2 rules with technology and obstacles')
    p.add_argument('--event-route-scope', choices=('product', 'interface'), default='product',
                   help='qualify all control/transport interfaces, or check only declared interface demands')
    p.add_argument('--event-prior-result', type=Path, help='previous event graph result for a router retry')
    p.add_argument('--event-route-feedback', type=Path, help='matched router demand exclusions for this trial')
    p.add_argument('--event-width', type=int, default=8, help='event search beam width, 1 for greedy')
    p.add_argument('--wire-budget', type=int)
    p.add_argument('--seconds', type=float, default=30)
    p.add_argument('--rounds', type=int, default=4)
    p.add_argument('--cover-limit', type=int, default=8)
    p.add_argument('--workers', type=int, default=1)
    a = p.parse_args()
    if (a.event_ir or a.event_graph) and (a.audit_only or a.lowered):
        p.error('event compilation is incompatible with --audit-only and --lowered')
    if bool(a.event_prior_result) != bool(a.event_route_feedback):
        p.error('event route retry requires both --event-prior-result and --event-route-feedback')
    if a.event_route_feedback and not a.event_graph:
        p.error('event route retry requires --event-graph')
    if bool(a.event_route_base) != bool(a.event_route_module):
        p.error('event physical binding requires both --event-route-base and --event-route-module')
    if a.event_route_catalog and not a.event_route_base:
        p.error('a route catalog requires a physical base')
    if (bool(a.event_route_adapter) != bool(a.event_route_technology)
            or a.event_route_adapter and not a.event_route_base):
        p.error('Algorithm 2 admission requires the adapter, technology and a physical base')
    if (a.event_native_assembler or a.event_route_base or a.event_control_fabric) and not (a.event_ir or a.event_graph):
        p.error('event artifact options require event compilation')
    if a.event_ir and a.model.suffix == '.onnx':
        p.error('--event-ir requires event IR JSON; use --event-graph for ONNX')
    if (bool(a.event_native_program) != bool(a.event_native_profiles)
            or a.event_native_program and not a.event_graph):
        p.error('native loop lowering requires --event-graph, --event-native-program and --event-native-profiles')
    a.output.mkdir(exist_ok=False)
    hardware = json.loads(a.hardware.read_text())
    model = import_onnx(a.model) if a.model.suffix == '.onnx' else json.loads(a.model.read_text())
    if a.lowered:
        model['lowered'] = True
    began = time.monotonic()
    write(a.output / 'imported.json', model)
    native_loops = None
    if a.event_native_program:
        from leaf_catalog import read_profiles

        native_loops = (
            json.loads(a.event_native_program.read_text(encoding='utf-8')),
            read_profiles([path.read_text(encoding='utf-8') for path in a.event_native_profiles]),
        )
    elif a.event_graph and a.model.suffix == '.onnx':
        from canonicalize import canonicalize

        model = canonicalize(model)
    route_target = None
    route_catalog = None
    control_fabric = None
    if a.event_control_fabric:
        control_fabric = json.loads(a.event_control_fabric.read_text(encoding='utf-8'))
    if a.event_route_base:
        backend = load_module('event_route_contract', a.event_route_module)
        base = backend.read_base(a.event_route_base)
        if a.event_route_adapter:
            route_target = (base, backend)
        if a.event_route_catalog:
            route_catalog = json.loads(a.event_route_catalog.read_text(encoding='utf-8'))
    if a.event_ir:
        result = compile_event_ir(model, hardware, budget=a.wire_budget, width=a.event_width,
                                  route_target=route_target, route_scope=a.event_route_scope,
                                  route_catalog=route_catalog, control_fabric=control_fabric)
    elif a.event_graph and a.event_route_feedback:
        previous = json.loads(a.event_prior_result.read_text(encoding='utf-8'))
        feedback = json.loads(a.event_route_feedback.read_text(encoding='utf-8'))
        result = retry_event_graph(model,hardware,previous,feedback,budget=a.wire_budget,
                                   width=a.event_width,native_loops=native_loops,route_target=route_target,
                                   route_catalog=route_catalog, route_scope=a.event_route_scope,
                                   control_fabric=control_fabric)
    elif a.event_graph:
        result = compile_event_graph(model, hardware, budget=a.wire_budget,
                                     width=a.event_width, native_loops=native_loops,route_target=route_target,
                                     route_catalog=route_catalog, route_scope=a.event_route_scope,
                                     control_fabric=control_fabric)
    else:
        coverage = audit(model, hardware)
        write(a.output / 'coverage.json', coverage)
        if a.audit_only:
            result = {'status': coverage['status'], 'scope': 'model import and compiler service coverage audit only'}
        else:
            try:
                result = compile_model(model, hardware, budget=a.wire_budget, seconds=a.seconds,
                    rounds=a.rounds, workers=a.workers, cover_limit=a.cover_limit)
            except Unsupported as exc:
                result = {'status': 'blocked_lowering', 'reason': str(exc)}
    if a.event_native_assembler and result['status'] == 'planned':
        from event_native_u import assemble_u64, compact_assembler_image, load_assembler
        resolved = result.get('resolved_hardware', hardware)
        profile = resolved['event_model'].get('native_control', {})
        try:
            if not profile.get('assembler_sha256'):
                raise Unsupported('no locked native U_64 control profile')
            assembler = load_assembler(a.event_native_assembler, profile['assembler_sha256'])
            binaries = assemble_u64(result['outputs']['program'], resolved, assembler, compact_assembler_image)
        except (Unsupported, ValueError) as exc:
            result['native'] = {'status': 'blocked_native', 'reason': str(exc)}
        else:
            images = {}
            for name, data in binaries.items():
                (a.output / (name + '.bin')).write_bytes(data)
                images[name] = {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
            result['native'] = {'status': 'encoded_native', 'images': images,
                                'source': result['outputs']['program']['source']}
    if a.event_route_base and result['status'] == 'planned':
        from event_deploy import bind_routes, handoff

        resolved = result.get('resolved_hardware', hardware)
        if a.event_route_adapter:
            adapter = load_module('event_router_adapter', a.event_route_adapter)
            geometry = load_module('event_router_geometry', a.event_route_adapter.with_name('geometry.py'))
            rules = json.loads(a.event_route_technology.read_text(encoding='utf-8'))
            receipt, request, router_input = handoff(result, resolved, base, backend, adapter, rules,
                                                      geometry.validate, wire_budget=a.wire_budget)
            write(a.output / 'handoff.json', receipt)
            result['handoff'] = receipt
            if router_input is not None:
                write(a.output / 'algorithm2-input.json', router_input)
        else:
            request = bind_routes(result['outputs']['wiring'], resolved, base,
                                  backend.elaborate, backend.verify_requirements)
        write(a.output / 'requirements.json',request)
        result['router'] = {'status':request['status'], 'sha256':request['sha256'],
                            'unresolved':len(request['unresolved'])}
    if (a.event_ir or a.event_graph) and 'outputs' in result:
        write(a.output / 'program.json',result['outputs']['program'])
        write(a.output / 'wiring.json',result['outputs']['wiring'])
        if 'control_connectivity' in result['outputs']:
            write(a.output / 'control-connectivity.json', result['outputs']['control_connectivity'])
    result['seconds'] = time.monotonic() - began
    inputs = (a.model, a.hardware)
    if a.event_native_program:
        inputs += (a.event_native_program, *a.event_native_profiles)
    if a.event_route_base:
        inputs += (a.event_route_base, a.event_route_module)
    if a.event_route_catalog:
        inputs += (a.event_route_catalog,)
    if a.event_control_fabric:
        inputs += (a.event_control_fabric,)
    if a.event_route_adapter:
        inputs += (a.event_route_adapter, a.event_route_adapter.with_name('geometry.py'), a.event_route_technology)
    result['input_sha256'] = {str(v): hashlib.sha256(v.read_bytes()).hexdigest() for v in inputs}
    result['objective'] = ('minimize elapsed ticks; then external bytes and static net cost; optional hard wire budget'
                           if a.event_ir or a.event_graph else
                           'minimize elapsed ticks; then external words and static net cost; optional hard wire budget')
    result.pop('event_ir', None)
    write(a.output / 'result.json', result)
    print(json.dumps({k: v for k, v in result.items()
                      if k not in ('graph', 'plan', 'outputs', 'resolved_hardware')}, ensure_ascii=False))
    if (a.event_ir or a.event_graph) and result['status'] != 'planned':
        return 2
    if a.event_native_assembler and result.get('native', {}).get('status') != 'encoded_native':
        return 2
    if a.event_route_base and result.get('router', {}).get('status') != 'endpoint_binding_complete':
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
