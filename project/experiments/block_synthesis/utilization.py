"""Attribute a verified loop plan to measured core, SRAM and memory costs.

Reservation time is deliberately separate from useful command time. The current
backend reserves resources for an entire serial kernel, including memory waits.
The hoisting estimate is an opportunity bound, NOT an executable new plan.
"""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path

from memory import descriptor_ticks
from streaming_ir import counts
from verify_loop_dp import verify
from verify_primitive_cost import verify as verify_cost
from column_shards import expand_selected


def charge(work, binding, hardware):
    result = Counter()
    for macro, group in binding['macro_binding'].items():
        meta = hardware['leaf_inventory'][group]
        reads, writes = work[macro+':read'], work[macro+':write']
        result['core'] += work[macro+':core']
        result['local_io'] += reads*meta['io_read_ticks'] + writes*meta['io_write_ticks']
        result['external_load'] += reads*descriptor_ticks(hardware['virtual_memory'], 1, 'load', meta['io_write_ticks'])
        result['external_store'] += writes*descriptor_ticks(hardware['virtual_memory'], 1, 'store', meta['io_read_ticks'])
    if work['IO:read'] or work['IO:write']:
        meta = hardware['sites'][binding['site']]
        result['external_load'] += work['IO:read']*descriptor_ticks(hardware['virtual_memory'], 1, 'load', meta['io_write_ticks'])
        result['external_store'] += work['IO:write']*descriptor_ticks(hardware['virtual_memory'], 1, 'store', meta['io_read_ticks'])
    return result


def report(ir, plan):
    hardware = ir['hardware']
    audits = {'native_cost': verify_cost(ir), 'schedule': verify(ir['tasks'], hardware, plan)}
    expanded,leaf_plan=expand_selected(ir['tasks'],plan)
    tasks = {t['id']:t for t in expanded}
    bodies = {p['id']:p for p in ir['program']}
    dots = {}
    for node in ir['primitive_program']['instructions']:
        if node['op']=='Dot': dots.setdefault(node['kernel'], []).append(node)
    total = Counter(); reservations = Counter(); useful = Counter(); by_op = {}; opportunities = [];wait_work=0
    tile_auxiliary=[]
    split_work = counts({'call':'split32'}, ir['native_templates'])
    for row in leaf_plan['tasks']:
        task = tasks[row['id']]
        binding = next(b for b in task['bindings'] if b['id']==row['binding'])
        source=task['source_task'];body=bodies[source]
        work = Counter(body['primitive_counts'])
        if 'columns' in task:
            columns=body['shape'][-1];lo,hi=task['columns']
            if any(v%columns for v in work.values()):raise ValueError('nonuniform column work')
            work=Counter({k:v//columns*(hi-lo) for k,v in work.items()})
        if 'dot_tile' in binding:
            from tile_accounting import charge as tile_charge
            costs=tile_charge(binding,hardware)
            if 'E' in binding['macro_binding']:
                group=binding['macro_binding']['E'];meta=hardware['leaf_inventory'][group]
                services=binding['tile_work']['e_sign_services']
                descriptors=services*(descriptor_ticks(hardware['virtual_memory'],1,'load',meta['io_write_ticks'])+
                    descriptor_ticks(hardware['virtual_memory'],1,'store',meta['io_read_ticks']))
                segment=costs['tile_E_service']+descriptors
                offset=binding.get('materialized_tile',{}).get('resource_offsets',{}).get(group+'.E')
                reserved=offset[1]-offset[0] if offset else row['end']-row['start']
                if not 0<=segment<=reserved:raise ValueError('tile E segment/reservation attribution differs')
                tile_auxiliary.append({'task':row['id'],'resource':group+'.E','reserved_ticks':reserved,
                    'E_service_ticks':costs['tile_E_service'],'E_descriptor_ticks':descriptors,
                    'serial_E_segment_ticks':segment,'reservation_minus_segment_ticks':reserved-segment,
                    'segment_fraction_of_reservation':segment/reserved})
        else:costs = charge(work, binding, hardware)
        duration = row['end']-row['start']
        wait = row.get('evaluation',{}).get('channel_wait_ticks',0)
        wait_work += wait
        # Current cache recipes remove external LOADs only. Reject unexplained
        # reductions rather than silently attributing them to compute savings.
        saving = sum(costs.values())-(duration-wait)
        if not 0 <= saving <= costs['external_load']:
            raise ValueError('unexplained duration decomposition '+row['id'])
        costs['external_load'] -= saving
        total.update(costs)
        op = body['op']; by_op.setdefault(op, Counter()).update(costs)
        if 'channel_wait_ticks' not in row.get('evaluation',{}):
            for resource in binding['resources']:
                offsets=binding.get('materialized_tile',{}).get('resource_offsets',{}).get(resource)
                reservations[resource] += offsets[1]-offsets[0] if offsets else duration
        if 'dot_tile' not in binding:
            for macro, group in binding['macro_binding'].items(): useful[group+'.'+macro] += work[macro+':core']
        if len(dots.get(row['id'], []))==1:
            node = dots[row['id']][0]; ca, cb = ir['native_operand_components'][node['id']]
            columns = node['shape'][-1]; rows = math.prod(node['shape'])//columns; k = node['attributes']['length']
            # A is invariant over output-column iterations. Prepare each row's
            # components once in external scratch; keep B unchanged. This is
            # conservative for batch-broadcast A and does not assume S holds it.
            removed = rows*k*(columns-1) if ca==3 and node['id'] not in ir.get('operand_preparations',{}) else 0
            if removed:
                saved = charge(Counter({x:n*removed for x,n in split_work.items()}), binding, hardware)
                opportunities.append({'task':row['id'], 'rows':rows, 'columns':columns, 'K':k,
                    'removed_split32_calls':removed, 'saved_serial_cost_bound':sum(saved.values()),
                    'saved_components':dict(saved), 'external_prepared_words_required':rows*k*ca,
                    'qualification':'opportunity only; transformed addresses/leases/replay not yet verified'})
    original={t['id']:t for t in ir['tasks']}
    for row in plan['tasks']:
        b=next(b for b in original[row['id']]['bindings'] if b['id']==row['binding'])
        if 'phase_execution' in b:
            for resource in b['resources']:reservations[resource]+=row['end']-row['start']
    if sum(total.values())+wait_work != sum(r['end']-r['start'] for r in leaf_plan['tasks']):
        raise ValueError('work decomposition not conserved')
    return {'audits':audits, 'makespan':plan['makespan'], 'serial_work':sum(total.values()),
        'cost_components':dict(total), 'arbitration_wait_work':wait_work,
        'by_operator':{k:dict(v) for k,v in by_op.items()},
        'tile_auxiliary_reservations':{'services':tile_auxiliary,
            'scope':'whole tile reservation versus serialized E service+descriptors, model ticks only; opportunity requiring explicit program/S/ACK proof, not reclaimable cycles or chip utilization'},
        'resources':{r:{'reserved_ticks':n, 'useful_core_ticks':useful[r],
                       'reserved_fraction_of_makespan':n/(plan['makespan']*hardware['resources'][r]),
                       'useful_core_fraction_of_makespan':useful[r]/(plan['makespan']*hardware['resources'][r])}
                     for r,n in reservations.items()},
        'operand_preparation_hoist':{'saved_serial_cost_bound':sum(x['saved_serial_cost_bound'] for x in opportunities),
                                    'candidates':opportunities},
        'scope':'native core/local IO plus virtual memory; tile P/E/feeder are whole service boundaries, not pure core cycles; not chip utilization; hoist is not validated speedup'}


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('ir', type=Path); parser.add_argument('plan', type=Path)
    parser.add_argument('output', type=Path); args = parser.parse_args()
    result = report(json.loads(args.ir.read_text(encoding='utf-8')), json.loads(args.plan.read_text(encoding='utf-8')))
    result['inputs'] = {str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (args.ir,args.plan)}
    args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:result[k] for k in ('makespan','serial_work','cost_components')}))
    print(json.dumps({'hoist_serial_bound':result['operand_preparation_hoist']['saved_serial_cost_bound'],
                      'candidate_count':len(result['operand_preparation_hoist']['candidates'])}))


if __name__=='__main__': main()
