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
    if total != row['end'] - row['start']:
        raise ValueError('descriptor/core/S decomposition does not reproduce service time')
    return {'core_ticks': core, 'local_S_ticks': local, 'descriptor_ticks': sum(channels.values()),
            'channel_descriptor_ticks': channels, 'duration': total}


def account(ir, plan):
    verify_costs(ir)
    verify(ir['tasks'], ir['hardware'], plan)
    expanded_tasks, expanded_plan = expand_selected(ir['tasks'], plan)
    tasks = {t['id']: t for t in expanded_tasks}
    program = {p['id']: p for p in ir['program']}
    nodes = {n['id']: n for n in ir['primitive_program']['instructions']}
    totals = dict(core_ticks=0, local_S_ticks=0, descriptor_ticks=0)
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
            totals[key] += parts[key]
        for channel in {r for r in binding['resources'] if r.startswith('virtual-memory.channel.')}:
            target = channels.setdefault(channel, {'whole_service_reserved_ticks': 0, 'descriptor_demand_ticks': 0})
            target['whole_service_reserved_ticks'] += parts['duration']
            target['descriptor_demand_ticks'] += parts['channel_descriptor_ticks'].get(channel, 0)
    for target in channels.values():
        target['reserved_without_descriptor_ticks'] = target['whole_service_reserved_ticks'] - target['descriptor_demand_ticks']
    demand = sum(c['descriptor_demand_ticks'] for c in channels.values())
    capacity = sum(ir['hardware']['resources'][c] for c in channels)
    return {'passed': True, 'makespan': plan['makespan'], 'serial_components': totals, 'channels': channels,
            'descriptor_pool_demand_lower_bound': (demand + capacity - 1) // capacity,
            'scope': 'exact selected-service cost decomposition; demand bound only, no finer schedule proven',
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
