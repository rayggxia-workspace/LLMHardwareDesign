"""Account descriptor occupancy without claiming a finer schedule is executable.

The current planner reserves a memory channel throughout an atomic service.
Here only the original one-word LOAD/STORE descriptor costs count as channel
work. Core commands, S accesses, cache retention and arithmetic are unchanged.
These are demand diagnostics, not a replacement timing model or speedup.
"""
import argparse
import json
from pathlib import Path

from column_shards import expand_selected
from memory import descriptor_ticks
from verify_loop_dp import verify
from verify_primitive_cost import verify as verify_costs


def service_parts(work, binding, row, hardware):
    if 'dot_tile' in binding:
        from tile_accounting import charge
        costs=charge(binding,hardware);w=binding['tile_work'];channels={}
        p_reads=w['external_read_words']-w.get('packed_outputs',0)
        groups=[(binding['macro_binding']['M'],p_reads,w['canonical_outputs']+w.get('packed_outputs',0))]
        if 'E' in binding['macro_binding']:
            groups.append((binding['macro_binding']['E'],w['packed_outputs'],w['flag_outputs']))
        for group,reads,writes in groups:
            meta=hardware['leaf_inventory'][group];m=hardware['virtual_memory']
            channel='virtual-memory.channel.'+str(meta['memory_group']%m['channels'])
            demand=reads*descriptor_ticks(m,1,'load',meta['io_write_ticks'])
            demand+=writes*descriptor_ticks(m,1,'store',meta['io_read_ticks'])
            channels[channel]=channels.get(channel,0)+demand
        service=sum(v for key,v in costs.items() if key.startswith('tile_'))
        total=sum(channels.values())+service
        wait=row.get('evaluation',{}).get('channel_wait_ticks',0)
        if total+wait!=row['end']-row['start']:raise ValueError('tile descriptor/service time does not reproduce service')
        return {'core_ticks':0,'local_S_ticks':0,'tile_service_ticks':service,
                'descriptor_ticks':sum(channels.values()),'channel_descriptor_ticks':channels,
                'duration':total+wait,'channel_wait_ticks':wait}
    inventory = hardware['leaf_inventory']
    groups = binding['macro_binding']
    reads = binding['external_read_words']
    evaluation = row.get('evaluation', {})
    if evaluation.get('cost_model') == 'dot-prefix-state-v2':
        reads = evaluation['external_read_words']
    elif row.get('cache_hit'):
        reads = binding['warm_read_words']
    baseline_reads = sum(work.get(m + ':read', 0) for m in ('M', 'E', 'N', 'IO'))
    saved = baseline_reads - reads
    if saved < 0 or saved and 'read_cache' not in binding:
        raise ValueError('unproved external-read adjustment')
    core = local = 0
    channels = {}
    for macro in ('M', 'E', 'N', 'IO'):
        r, w = work.get(macro + ':read', 0), work.get(macro + ':write', 0)
        if macro != 'IO' and macro not in groups:
            if r or w or work.get(macro + ':core', 0):
                raise ValueError('missing phase macro binding')
            continue
        if macro == 'IO':
            if not r and not w:
                continue
            matches = [g for g, meta in inventory.items() if meta['site'] == binding['site']]
            if len(matches) != 1:
                raise ValueError('ambiguous IO control group')
            group = matches[0]
        else:
            group = groups[macro]
            core += work.get(macro + ':core', 0)
        meta = inventory[group]
        # Caching changes external loads only. Original local operand reads
        # remain, including the zero packet and B staging reads.
        if macro != 'IO':
            local += r * meta['io_read_ticks'] + w * meta['io_write_ticks']
        external_r = r - (saved if macro == 'M' else 0)
        if external_r < 0:
            raise ValueError('cache saving exceeds M source reads')
        dma = external_r * descriptor_ticks(hardware['virtual_memory'], 1, 'load', meta['io_write_ticks'])
        dma += w * descriptor_ticks(hardware['virtual_memory'], 1, 'store', meta['io_read_ticks'])
        channel = 'virtual-memory.channel.' + str(meta['memory_group'] % hardware['virtual_memory']['channels'])
        channels[channel] = channels.get(channel, 0) + dma
    total = core + local + sum(channels.values())
    wait = row.get('evaluation',{}).get('channel_wait_ticks',0)
    if total+wait != row['end'] - row['start']:
        raise ValueError('descriptor/core/S decomposition does not reproduce service time')
    return {'core_ticks': core, 'local_S_ticks': local, 'descriptor_ticks': sum(channels.values()),
            'channel_descriptor_ticks': channels, 'duration': total,'channel_wait_ticks':wait}


def account(ir, plan):
    verify_costs(ir)
    verify(ir['tasks'], ir['hardware'], plan)
    expanded_tasks, expanded_plan = expand_selected(ir['tasks'], plan)
    tasks = {t['id']: t for t in expanded_tasks}
    program = {p['id']: p for p in ir['program']}
    nodes = {n['id']: n for n in ir['primitive_program']['instructions']}
    totals = dict(core_ticks=0, local_S_ticks=0, descriptor_ticks=0, tile_service_ticks=0)
    channels = {}
    for row in expanded_plan['tasks']:
        task = tasks[row['id']]
        binding = next(b for b in task['bindings'] if b['id'] == row['binding'])
        original = task['source_task']
        work = dict(program[original]['primitive_counts'])
        if 'columns' in task:
            width = task['columns'][1] - task['columns'][0]
            columns = nodes[original]['shape'][-1]
            if any(v * width % columns for v in work.values()):
                raise ValueError('nonintegral column work')
            work = {k: v * width // columns for k, v in work.items()}
        parts = service_parts(work, binding, row, ir['hardware'])
        for key in totals:
            totals[key] += parts.get(key,0)
        for channel in {r for r in binding['resources'] if r.startswith('virtual-memory.channel.')}:
            target = channels.setdefault(channel, {'whole_service_reserved_ticks': 0, 'descriptor_demand_ticks': 0})
            if 'channel_wait_ticks' not in row.get('evaluation',{}):
                target['whole_service_reserved_ticks'] += parts['duration']
            target['descriptor_demand_ticks'] += parts['channel_descriptor_ticks'].get(channel, 0)
    original={t['id']:t for t in ir['tasks']}
    for row in plan['tasks']:
        b=next(b for b in original[row['id']]['bindings'] if b['id']==row['binding'])
        if 'phase_execution' in b:
            for channel in b['resources']:
                if channel.startswith('virtual-memory.channel.'):
                    channels[channel]['whole_service_reserved_ticks']+=row['end']-row['start']
    for target in channels.values():
        target['reserved_without_descriptor_ticks'] = target['whole_service_reserved_ticks'] - target['descriptor_demand_ticks']
    demand = sum(c['descriptor_demand_ticks'] for c in channels.values())
    capacity = sum(ir['hardware']['resources'][c] for c in channels)
    return {'passed': True, 'makespan': plan['makespan'], 'serial_components': totals, 'channels': channels,
            'descriptor_pool_demand_lower_bound': (demand + capacity - 1) // capacity,
            'scope': 'exact selected-service cost decomposition; tile services include local adaptation/ACK, not pure core; demand bound only, no finer schedule proven',
            'unchanged': 'native arithmetic/order, local S traffic, one-word cold descriptors and final ACKs',
            'pending': 'phase calendars, channel arbitration, control/RTL calibration, physical timing and energy'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('ir', type=Path)
    parser.add_argument('plan', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    result = account(json.loads(args.ir.read_text()), json.loads(args.plan.read_text()))
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
