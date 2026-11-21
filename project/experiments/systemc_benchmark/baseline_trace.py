"""Freeze old220 binding choices; independently re-evaluate costs before SystemC.

This is a coarse, conservative KERNEL baseline, not calibrated system timing.
The SystemC input contains no planned start/end times. Resource issue-order
edges model the old compiler's append-only per-resource calendars explicitly.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(ir, plan, evaluate_transition, frequency_hz):
    hardware = ir['hardware']
    if any(n != 1 for n in hardware['resources'].values()):
        raise ValueError('foundation SystemC resource model is capacity-one only')
    if frequency_hz <= 0:
        raise ValueError('positive assumed frequency required')
    tasks = {t['id']: t for t in ir['tasks']}
    if len(tasks) != len(ir['tasks']):
        raise ValueError('duplicate task')
    if len(plan['tasks']) != len(tasks):
        raise ValueError('incomplete plan')
    state = SimpleNamespace(cache={}, nets=frozenset(), makespan=0,
                            resources={r: (0,) for r in hardware['resources']})
    fixed = frozenset(n for n, m in hardware['nets'].items() if m.get('fixed'))
    done, last_owner, seen = {}, {}, set()
    lines, audit = [], []
    traffic = 0
    for row in plan['tasks']:
        name = row['id']
        if name in seen:
            raise ValueError('task scheduled twice')
        seen.add(name)
        task = tasks[name]
        b, = [b for b in task['bindings'] if b['id'] == row['binding']]
        ev = evaluate_transition(state, b, hardware,
                                 max([done[p] for p in task.get('after', [])] or [0]),
                                 retention=row.get('evaluation', {}).get('retention', 'legacy'),
                                 fixed=fixed)
        if not ev['legal'] or (ev['start'], ev['end']) != (row['start'], row['end']):
            raise ValueError('old plan differs from independently recomputed transition: ' + name)
        deps = set(task.get('after', []))
        deps.update(last_owner[r] for r in b['resources'] if r in last_owner)
        # Round each service duration UP to integer ps, never floor execution.
        ps = (ev['duration'] * 10**12 + frequency_hz - 1) // frequency_hz
        if any(any(c in s for c in '\t\r\n,') for s in [name] + sorted(deps) + b['resources']):
            raise ValueError('unsupported TSV identifier')
        lines.append('\t'.join([name, str(ps), ','.join(sorted(deps)) or '-',
                                ','.join(b['resources']), '?']))
        audit.append({'id': name, 'binding': b['id'], 'core_ticks': ev['duration'],
                      'external_words': ev['traffic'], 'cache_hit': ev['cache_hit'],
                      'resource_issue_predecessors': sorted(deps - set(task.get('after', [])))})
        for r in b['resources']:
            last_owner[r] = name
        state.cache, state.nets = ev['cache'], ev['nets']
        state.resources, state.makespan = ev['resources'], ev['makespan']
        traffic += ev['traffic']
        done[name] = ev['end']
    if state.makespan != plan['makespan'] or traffic != plan['external_words']:
        raise ValueError('aggregate old plan mismatch')
    return lines, {
        'scope': 'old220 kernel-lock conservative cost model; NOT calibrated system timing',
        'input_program_scope': ir['program_scope'], 'input_timing_scope': ir['timing_scope'],
        'assumed_frequency_hz': frequency_hz, 'kernel_count': len(lines),
        'recomputed_core_ticks': state.makespan, 'external_128bit_words': traffic,
        'expected_makespan_ps_lower': state.makespan * 10**12 // frequency_hz,
        'rounding_error_ps_upper_exclusive': len(lines) + 1,
        'energy_complete': False, 'decode_qualified': False,
        'capacity_qualified': ir['capacity_qualified'], 'rows': audit}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('ir', type=Path)
    p.add_argument('plan', type=Path)
    p.add_argument('old_transition', type=Path)
    p.add_argument('output', type=Path)
    p.add_argument('--assumed-frequency-hz', type=int, default=300000000)
    a = p.parse_args()
    spec = importlib.util.spec_from_file_location('frozen_old_transition', a.old_transition)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    lines, report = build(json.loads(a.ir.read_text()), json.loads(a.plan.read_text()),
                          module.evaluate_transition, a.assumed_frequency_hz)
    a.output.mkdir(exist_ok=False)
    trace = a.output / 'trace.tsv'
    trace.write_text('\n'.join(lines) + '\n')
    report['inputs'] = {str(f): sha(f) for f in (a.ir, a.plan, a.old_transition)}
    report['trace_sha256'] = sha(trace)
    (a.output / 'audit.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k != 'rows'}))


if __name__ == '__main__':
    main()
