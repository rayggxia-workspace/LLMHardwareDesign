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


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('model', type=Path)
    p.add_argument('hardware', type=Path)
    p.add_argument('output', type=Path)
    p.add_argument('--audit-only', action='store_true')
    p.add_argument('--lowered', action='store_true', help='internal tile IR, not a second author-maintained model format')
    p.add_argument('--wire-budget', type=int)
    p.add_argument('--seconds', type=float, default=30)
    p.add_argument('--rounds', type=int, default=4)
    p.add_argument('--cover-limit', type=int, default=8)
    p.add_argument('--workers', type=int, default=1)
    a = p.parse_args()
    a.output.mkdir(exist_ok=False)
    hardware = json.loads(a.hardware.read_text())
    model = import_onnx(a.model) if a.model.suffix == '.onnx' else json.loads(a.model.read_text())
    if a.lowered:
        model['lowered'] = True
    began = time.monotonic()
    write(a.output / 'imported.json', model)
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
    result['input_sha256'] = {str(v): hashlib.sha256(v.read_bytes()).hexdigest() for v in (a.model, a.hardware)}
    result['objective'] = 'minimize elapsed ticks; then external words and static net cost; optional hard wire budget'
    write(a.output / 'result.json', result)
    print(json.dumps({k: v for k, v in result.items() if k not in ('graph', 'plan')}, ensure_ascii=False))


if __name__ == '__main__':
    main()
