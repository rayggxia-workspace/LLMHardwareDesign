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


def compile_event_ir(model, hardware, *, budget=None, width=8, emit_dependencies=False, emit_outputs=None,
                     route_base=None, route_catalog=None, route_scope='product', control_fabric=None):
    from cover_frontier import search
    from event_deploy import attach_route_catalog, digest, route_admission
    from verify_cover_frontier import verify as verify_events

    if 'event_model' not in hardware:
        raise ValueError('event IR requires a qualified hardware event model')
    timing = hardware['event_model'].get('timing', 'calendar')
    if emit_outputs is None:
        # Calendar callers include the native linker. Phase studies may
        # intentionally compare schedules that have no command-level encoding.
        emit_outputs = timing == 'calendar'
    if emit_dependencies and timing not in ('replay', 'snapshot'):
        raise ValueError('phase dependencies require replay or snapshot timing')
    if route_scope not in ('product', 'interface'):
        raise ValueError('unknown event handoff scope')
    if route_base is not None and route_scope == 'product' and route_base.get('state') != 'frozen':
        raise ValueError('product mapping requires a frozen physical base')
    if control_fabric is None:
        control_fabric = hardware.get('control_fabric')
    elif hardware.get('control_fabric', control_fabric) != control_fabric:
        raise ValueError('conflicting control fabric inputs')
    if control_fabric is not None:
        from event_control_fabric import attach_control_fabric, qualify_endpoint_demands

        hardware = attach_control_fabric(hardware, control_fabric)
    if route_catalog is not None:
        hardware = attach_route_catalog(hardware, route_catalog)
    if control_fabric is not None:
        hardware = qualify_endpoint_demands(hardware)
    admit = None
    if route_base is not None:
        import route_contract
        from event_physical_contract import qualify_hardware

        if route_scope == 'product':
            hardware = qualify_hardware(hardware, route_base)
        elif 'native_service_routes' in route_base:
            from event_native_dispatch import qualify_native_dispatch

            hardware = qualify_native_dispatch(hardware, route_base)
        admit = route_admission(hardware, route_base, route_contract, product=route_scope == 'product')
    tasks, covers = model['tasks'], model.get('covers', ())
    plan = search(tasks, hardware, covers, width=width, wire_budget=budget, route_admission=admit)
    result = {'status': plan['status'], 'plan': plan, 'wire_budget': budget,
              'scope': 'qualified event IR and schedule'}
    if route_base is not None:
        result.update(physical_base_sha256=digest(route_base), route_scope=route_scope)
    if plan['status'] != 'planned':
        for field in ('logical_control_issues', 'physical_interface_issues', 'native_dispatch_issues'):
            if field in hardware['event_model']:
                result[field] = hardware['event_model'][field]
    if plan['status'] == 'planned':
        result['verification'] = verify_events(tasks, hardware, covers, plan, wire_budget=budget)
        if emit_dependencies:
            from event_replay_plan import dependency_program
            result['phase_dependencies'] = dependency_program(tasks, hardware, covers, plan)
        if emit_outputs:
            from event_deploy import emit

            result.update(event_ir=model, resolved_hardware=hardware,
                          outputs=emit(tasks, hardware, covers, plan,
                                       physical_base_sha256=result.get('physical_base_sha256')))
    return result


def compile_event_graph(model, hardware, *, budget=None, width=8, emit_dependencies=False,
                        native_loops=None, route_base=None, route_catalog=None,
                        route_scope='product', control_fabric=None):
    from event_deploy import digest
    from event_lowering import MissingImplementations

    provenance = {'graph_sha256': digest(model), 'input_hardware_sha256': digest(hardware)}
    try:
        if native_loops is None:
            from event_lowering import lower

            if 'event_model' not in hardware:
                raise ValueError('event graph requires a qualified hardware event model')
            lowered, resolved = lower(model, hardware)
        else:
            from event_loop_graph import lower

            lowered, resolved, audit = lower(model, hardware, *native_loops)
    except MissingImplementations as error:
        return {'status': 'blocked_lowering', 'reason': str(error), 'lowering_coverage': error.coverage, **provenance}
    except Unsupported as error:
        return {'status': 'blocked_lowering', 'reason': str(error), **provenance}
    result = compile_event_ir(lowered, resolved, budget=budget, width=width,
                              emit_dependencies=emit_dependencies, emit_outputs=True,
                              route_base=route_base, route_catalog=route_catalog,
                              route_scope=route_scope, control_fabric=control_fabric)
    result.update(provenance)
    if native_loops is not None:
        result['native_loop_verification'] = audit
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('model', type=Path)
    p.add_argument('hardware', type=Path)
    p.add_argument('output', type=Path)
    p.add_argument('--audit-only', action='store_true')
    p.add_argument('--lowered', action='store_true', help='internal tile IR, not a second author-maintained model format')
    event_input = p.add_mutually_exclusive_group()
    event_input.add_argument('--event-ir', action='store_true', help='plan an internal IR with qualified event stages')
    event_input.add_argument('--event-graph', action='store_true', help='lower a typed JSON or ONNX graph to event IR')
    p.add_argument('--event-native-program', type=Path, help='typed integer loop program for this input graph')
    p.add_argument('--event-native-profiles', type=Path, nargs=3,
                   help='native qualification logs for three initial states')
    p.add_argument('--event-route-base', type=Path, help='base with verified physical endpoint views')
    p.add_argument('--event-route-catalog', type=Path, help='physical templates for logical demand IDs')
    p.add_argument('--event-route-scope', choices=('product', 'interface'), default='product')
    p.add_argument('--event-control-fabric', type=Path, help='mother/local control interface JSON')
    p.add_argument('--event-dependencies', action='store_true',
                   help='export phase waits from an event replay or snapshot plan')
    p.add_argument('--event-outputs', action='store_true',
                   help='export control and wiring IR from the selected event plan')
    p.add_argument('--event-width', type=int, default=8, help='beam width for --event-ir, 1 for singleton greedy')
    p.add_argument('--wire-budget', type=int)
    p.add_argument('--seconds', type=float, default=30)
    p.add_argument('--rounds', type=int, default=4)
    p.add_argument('--cover-limit', type=int, default=8)
    p.add_argument('--workers', type=int, default=1)
    a = p.parse_args()
    if a.event_ir and (a.audit_only or a.lowered or a.model.suffix == '.onnx'):
        p.error('--event-ir requires event IR JSON and is incompatible with --audit-only and --lowered')
    if a.event_graph and (a.audit_only or a.lowered):
        p.error('--event-graph is incompatible with --audit-only and --lowered')
    if (a.event_dependencies or a.event_outputs) and not (a.event_ir or a.event_graph):
        p.error('event outputs require --event-ir or --event-graph')
    if (bool(a.event_native_program) != bool(a.event_native_profiles)
            or a.event_native_program and not a.event_graph):
        p.error('native loop lowering requires --event-graph, --event-native-program and --event-native-profiles')
    if (a.event_route_base or a.event_route_catalog or a.event_control_fabric) and not (a.event_ir or a.event_graph):
        p.error('physical and control inputs require event compilation')
    if a.event_route_catalog and not a.event_route_base:
        p.error('--event-route-catalog requires --event-route-base')
    hardware = json.loads(a.hardware.read_text())
    if a.event_dependencies and hardware.get('event_model', {}).get('timing') not in ('replay', 'snapshot'):
        p.error('--event-dependencies requires replay or snapshot timing')
    a.output.mkdir(exist_ok=False)
    model = import_onnx(a.model) if a.model.suffix == '.onnx' else json.loads(a.model.read_text())
    if a.lowered:
        model['lowered'] = True
    began = time.monotonic()
    write(a.output / 'imported.json', model)
    event_target = {}
    if a.event_route_base:
        from route_contract import read_base

        event_target.update(route_base=read_base(a.event_route_base), route_scope=a.event_route_scope)
    for field in ('route_catalog', 'control_fabric'):
        path = getattr(a, 'event_' + field)
        if path:
            event_target[field] = json.loads(path.read_text(encoding='utf-8'))
    if a.event_ir:
        result = compile_event_ir(model, hardware, budget=a.wire_budget, width=a.event_width,
                                  emit_dependencies=a.event_dependencies,
                                  emit_outputs=a.event_outputs or bool(a.event_route_base), **event_target)
    elif a.event_graph:
        native_loops = None
        if a.event_native_program:
            from leaf_catalog import read_profiles

            native_loops = (
                json.loads(a.event_native_program.read_text(encoding='utf-8')),
                read_profiles([path.read_text(encoding='utf-8') for path in a.event_native_profiles]),
            )
        elif a.model.suffix == '.onnx':
            from canonicalize import canonicalize

            model = canonicalize(model)
        result = compile_event_graph(model, hardware, budget=a.wire_budget, width=a.event_width,
                                     emit_dependencies=a.event_dependencies, native_loops=native_loops,
                                     **event_target)
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
    result['seconds'] = time.monotonic() - began
    inputs = (a.model, a.hardware)
    if a.event_native_program:
        inputs += (a.event_native_program, *a.event_native_profiles)
    inputs += tuple(path for path in (a.event_route_base, a.event_route_catalog, a.event_control_fabric)
                    if path is not None)
    result['input_sha256'] = {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in inputs}
    result['objective'] = ('minimize elapsed ticks; then external bytes and static net cost; optional hard wire budget'
                           if a.event_ir or a.event_graph else
                           'minimize elapsed ticks; then external words and static net cost; optional hard wire budget')
    write(a.output / 'result.json', result)
    print(json.dumps({k: v for k, v in result.items()
                      if k not in ('graph', 'plan', 'phase_dependencies', 'outputs', 'event_ir', 'resolved_hardware')},
                     ensure_ascii=False))


if __name__ == '__main__':
    main()
