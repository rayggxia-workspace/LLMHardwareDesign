"""Isolated constant-cost phase experiments from registered Dot candidates.

This surveys single services, not a full-model reschedule or algorithm gain.
Full finite loops are evaluated exactly; a bounded derivative is independently
expanded for SystemC event comparison. Arithmetic and new hardware are not run.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace

from phase_program import cached_dot_program, aggregate, simulate
from phase_trace import reference
from transition import evaluate_transition
from verify_primitive_cost import verify as verify_cost


def expanded(body, *, limit=100000):
    rows = []
    def visit(node):
        if 'sequence' in node:
            for child in node['sequence']:visit(child)
        elif 'repeat' in node:
            for _ in range(node['repeat']):visit(node['body'])
        elif node['ticks']:
            if len(rows) >= limit:raise ValueError('bounded SystemC derivative exceeds phase limit')
            rows.append(node)
    visit(body)
    return rows


def survey(ir, output):
    verify_cost(ir)
    h = ir['hardware'];channels = h['virtual_memory']['channels']
    state = SimpleNamespace(resources={r:(0,)*n for r,n in h['resources'].items()},
                            nets=frozenset(),cache={},makespan=0)
    chosen = None
    for task in ir['tasks']:
        choices = [b for b in task['bindings'] if 'parallel_shards' in b and
                   'frontier_partition' not in b and all(
                       child['binding'].get('read_cache',{}).get('stripe',0) > 0
                       for child in b['parallel_shards']['children'])]
        if choices:
            chosen = task,choices;break
    if chosen is None:raise ValueError('no registered prepared-A/S16-B compound candidate')
    task,choices = chosen
    by_count = {}
    for binding in choices:
        count = len(binding['parallel_shards']['children'])
        by_count.setdefault(count,[]).append(binding)
    results = [];last_programs = None
    selected = []
    for count,options in sorted(by_count.items()):
        def spread(b):
            widths = [c['columns'][1]-c['columns'][0] for c in b['parallel_shards']['children']]
            return max(widths)-min(widths)
        seen = set()
        for selection,b in (('first_registered',options[0]),
                            ('minimum_column_width_spread',min(options,key=spread))):
            if b['id'] not in seen:
                selected.append((count,selection,b));seen.add(b['id'])
    for count,selection,binding in selected:
        children = binding['parallel_shards']['children']
        ev = evaluate_transition(state,binding,h,0,retention=('preserve',)*count)
        if not ev['legal']:raise ValueError('registered compound unexpectedly illegal')
        programs = [];small = []
        for child,row in zip(children,ev['details']['services']):
            b = child['binding'];c = b['read_cache']
            meta = {**h['leaf_inventory'][b['macro_binding']['M']],
                    'words':h['sites'][c['site']]['words']}
            program = cached_dot_program(b,row,ir['native_templates'],meta,h['virtual_memory'])
            ticks,events = aggregate(program)
            if ticks != row['end']-row['start'] or events['external-load-until-S-commit'] != row['evaluation']['external_read_words']:
                raise ValueError('phase program does not conserve registered service cost/traffic')
            programs.append(program)
            # Deliberate bounded timing derivative, never a model execution.
            sc = {**c,'rows':min(c['rows'],2),'columns':min(c['columns'],5),
                  'K':min(c['K'],8),'stripe':min(c['stripe'],8)}
            small.append(cached_dot_program({**b,'read_cache':sc},
                {**row,'evaluation':{**row['evaluation'],'reused_prefix':0}},
                ir['native_templates'],meta,h['virtual_memory']))
        timed = simulate(programs,channels)
        expected_counts = Counter()
        for p in programs:expected_counts.update(aggregate(p)[1])
        if Counter(timed['phase_counts']) != expected_counts:
            raise ValueError('full phase loop work lost in timing execution')
        if timed['makespan'] > ev['duration']:
            # FCFS interleaving can in general be slower than service order.
            # Preserve negative results, never force the old plan's time.
            relation = 'FCFS phase execution slower than conservative service order'
        else:relation = 'isolated phase execution no slower than conservative service order'
        results.append({'workers':count,'candidate_selection':selection,'source_task':task['id'],'binding':binding['id'],
            'groups':[c['binding']['macro_binding']['M'] for c in children],
            'columns':[c['columns'] for c in children],
            'whole_service_ticks':ev['duration'],'phase_timing':timed,'relation':relation,
            'traffic_words':ev['traffic'],'programs':programs})
        last_programs = small
    output.mkdir(parents=True,exist_ok=False)
    workers = [expanded(p) for p in last_programs]
    refs = {mode:reference(workers,channels,whole_service=mode == 'whole-service')
            for mode in ('whole-service','descriptor-phases')}
    (output/'reference.json').write_text(json.dumps(refs)+'\n')
    text = f'{len(workers)} {channels}\n'
    for worker in workers:
        text += str(len(worker))+'\n'
        text += ''.join(f"{p['channel']} {p['ticks']}\n" for p in worker)
    (output/'probe.txt').write_text(text)
    result = {'passed':True,'isolated_services':results,
              'systemc_derivative':'same native cost and cache phase recipe, clipped R<=2/N<=5/K<=8; no numerical execution',
              'scope':'exact symbolic constant-cost FCFS timing of isolated compounds; not new DP, full schedule or token/s',
              'pending':'real bank/address/queue/LC arbitration, actual data, full graph and independently calibrated system model',
              'algorithm_gain_claimed':False}
    result['selection_scope'] = 'first registered and minimum column-width spread per worker count; NOT an exhaustive candidate optimum'
    (output/'survey.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps([{'workers':r['workers'],'whole':r['whole_service_ticks'],
        'phases':r['phase_timing']['makespan'],'executed_events':r['phase_timing']['executed_events'],
        'skipped_events':r['phase_timing']['skipped_events']} for r in results]))


def main():
    p = argparse.ArgumentParser();p.add_argument('ir',type=Path);p.add_argument('output',type=Path)
    a = p.parse_args();raw = a.ir.read_bytes();survey(json.loads(raw),a.output)
    (a.output/'source-ir.sha256').write_text(hashlib.sha256(raw).hexdigest()+'\n')
    sources = {p.name:hashlib.sha256(p.read_text(encoding='utf8').encode('utf8')).hexdigest()
               for p in sorted(Path(__file__).parent.glob('*.py'))}
    (a.output/'source-receipt.json').write_text(json.dumps({'python':sys.version,
        'normalization':'UTF8 universal-newline to LF','modules_sha256':sources},indent=2)+'\n')


if __name__ == '__main__':main()
