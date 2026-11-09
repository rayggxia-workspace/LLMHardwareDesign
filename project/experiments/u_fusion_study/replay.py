"""Finite-resource conditional replay of measured sequential U packet phases.

DDR/cache phase durations are FROZEN observations, not recomputed concurrent
memory transactions. One shared input/output controller and one E are modelled;
regions remain serial and all other measured full-model time is held fixed.
"""
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path

from fusion_contract import ELEMENTWISE, read_trace, require, vector_regions


COLUMNS = ['id', 'region', 'op_index', 'offset', 'n', 'forward_input_tensor',
           'forward_output_tensor', 'input_wall', 'compute_wall', 'output_wall',
           'input_S_read', 'input_S_write', 'output_S_read', 'output_S_write',
           'input_DDR_read_bus', 'input_DDR_write_bus', 'output_DDR_read_bus',
           'output_DDR_write_bus', 'arith_subcycles', 'control_subcycles']
FACT_COLUMNS = [0, 1, 2, 3, 4, 5, 6, 10, 11, 12, 13, 14, 15, 16, 17, 18]


def event_header(path):
    with Path(path).open(encoding='utf-8') as source:
        header = json.loads(source.readline())
    require(header['schema_version'] == 1 and header['columns'] == COLUMNS,
            'unsupported event schema')
    require(header['subcycles_per_core_cycle'] == 1000 and
            header['core_clock_Hz'] == 300000000, 'changed time contract')
    require(header['forward_capacity_bytes'] == 256 and header['input_slot_bytes'] == 768
            and header['output_slot_bytes'] == 256, 'changed finite data budget')
    require(header['forward_register_read_bytes_per_cycle'] == 16 and
            header['forward_register_write_bytes_per_cycle'] == 16, 'forward RF bandwidth')
    return header


def iter_regions(path):
    """At most one region of packet arrays is held, never a full large trace."""
    with Path(path).open(encoding='utf-8') as source:
        source.readline()
        region, nodes = None, []
        for line in source:
            obj = json.loads(line)
            if isinstance(obj, dict):
                require(obj.get('type') == 'region', 'unknown event record')
                if region is not None:
                    yield region, nodes
                region, nodes = obj, []
            else:
                require(region is not None and isinstance(obj, list) and len(obj) == 20,
                        'node outside region/schema')
                require(all(type(value) is int for value in obj), 'noninteger event field')
                nodes.append(obj)
        if region is not None:
            yield region, nodes


def inspect_events(path, trace, fusion, fee):
    header = event_header(path)
    require(header['trace_sha256'] == trace.sha256, 'event input SHA mismatch')
    require(header['fusion'] == bool(fusion) and header['fee_cycles'] == fee,
            'event command metadata mismatch')
    expected_regions = vector_regions(trace)
    digest = hashlib.sha256()
    node_id = count_regions = phase_wall = arithmetic = control = 0
    S_service = DDR_read = DDR_write = forward_packets = forward_bytes = 0
    previous_end = 0
    for region, nodes in iter_regions(path):
        require(count_regions < len(expected_regions), 'extra region')
        begin, stop = expected_regions[count_regions]
        count_regions += 1
        count = trace.ops[begin].elements
        require((region['id'], region['begin'], region['end_exclusive'], region['elements']) ==
                (count_regions, begin, stop, count), 'region identity/coverage')
        require(previous_end <= region['start_subcycles'] <= region['end_subcycles'],
                'overlapping/out-of-order source regions')
        previous_end = region['end_subcycles']
        cursor = wall = 0
        for offset in range(0, count, 64):
            n = min(64, count - offset)
            for index in range(begin, stop):
                if trace.ops[index].kind == 'Constant':
                    continue
                require(cursor < len(nodes), 'missing region packet')
                node = nodes[cursor]
                cursor += 1
                node_id += 1
                require(node[:5] == [node_id, count_regions, index, offset, n],
                        'packet source order/extent/identity')
                require(all(value >= 0 for value in node[7:]), 'negative phase/work')
                require(node[18] == ((n + 3) // 4 + 5) * 1000, 'changed single-E arithmetic')
                require(node[19] == (fee * 1000 if node[6] >= 0 else 0), 'forward control fee')
                require(node[8] == node[18] + node[19], 'unpaid compute/control phase')
                require(node[7] >= node[10] + node[11] and
                        node[9] >= node[12] + node[13], 'physical S work exceeds phase')
                require(all(value % 64 == 0 for value in node[14:18]), 'DDR bus beat alignment')
                digest.update((json.dumps([node[i] for i in FACT_COLUMNS],
                                           separators=(',', ':')) + '\n').encode())
                wall += sum(node[7:10])
                arithmetic += node[18]
                control += node[19]
                S_service += sum(node[10:14])
                DDR_read += node[14] + node[16]
                DDR_write += node[15] + node[17]
                if node[6] >= 0:
                    forward_packets += 1
                    forward_bytes += n * 4
        require(cursor == len(nodes), 'extra region packet')
        require(wall == region['end_subcycles'] - region['start_subcycles'],
                'source phase wall conservation')
        phase_wall += wall
    require(count_regions == len(expected_regions), 'missing vector region')
    return dict(passed=True, event_facts_sha256=digest.hexdigest(), nodes=node_id,
                regions=count_regions, source_region_subcycles=phase_wall,
                E_arithmetic_subcycles=arithmetic, control_subcycles=control,
                phase_S_service_subcycles=S_service, phase_DDR_read_bus=DDR_read,
                phase_DDR_write_bus=DDR_write, forwarded_packets=forward_packets,
                forwarded_bytes=forward_bytes)


def dependencies(region, nodes, trace):
    producer_op = {trace.ops[i].out: i for i in range(region['begin'], region['end_exclusive'])
                   if trace.ops[i].kind in ELEMENTWISE}
    prior_nodes = {}
    needs = []
    peak_input = peak_output = 0
    for local, node in enumerate(nodes):
        op = trace.ops[node[2]]
        offset, n = node[3:5]
        dep = set()
        input_bytes = 0
        for tid in op.inputs:
            tensor = trace.tensors[tid]
            start = 0 if tensor.elements == 1 else offset % tensor.elements
            take = min(n, tensor.elements - start)
            input_bytes += take * (tensor.bits // 8)
            if take < n and tensor.elements > 1:
                input_bytes += min(n - take, tensor.elements) * (tensor.bits // 8)
            if tid in producer_op:
                require(tensor.elements == region['elements'], 'nonlocal region dependency')
                producer = prior_nodes[(producer_op[tid], offset)]
                dep.add((producer, 'E' if tid == node[5] else 'output'))
        output_bytes = n * (trace.tensors[op.out].bits // 8)
        require(input_bytes <= 768 and output_bytes <= 256, 'unbudgeted FIFO payload')
        peak_input = max(peak_input, input_bytes)
        peak_output = max(peak_output, output_bytes)
        needs.append(tuple(sorted(dep)))
        prior_nodes[(node[2], offset)] = local
    return needs, peak_input, peak_output


def replay_region(region, nodes, trace, depth):
    """Event scheduler. Input/output share one nonpreemptive controller.

    E and controller can overlap. E issues strictly in original packet order.
    Every slot is owned from input start through output ACK. A forward value
    remains live through its consumer's E completion: its 16B/cycle RF read is
    inside the original E service, not a free input-FIFO copy.
    """
    require(depth in (1, 2, 4, 8), 'unsupported FIFO depth')
    for node in nodes:
        require(node[18] == ((node[4] + 3) // 4 + 5) * 1000 and
                node[8] == node[18] + node[19] and node[19] >= 0,
                'replay lost single-E arithmetic/control service')
        require(node[7] >= node[10] + node[11] >= 0 and
                node[9] >= node[12] + node[13] >= 0, 'replay lost shared S service')
    require(sum(sum(node[7:10]) for node in nodes) ==
            region['end_subcycles'] - region['start_subcycles'], 'source phase total mismatch')
    deps, peak_input, peak_output = dependencies(region, nodes, trace)
    size = len(nodes)
    require(size > 0, 'empty vector region')
    input_done = [-1] * size
    E_done = [-1] * size
    output_done = [-1] * size
    input_start = [-1] * size
    E_start = [-1] * size
    output_start = [-1] * size
    slots = [None] * depth
    controller = E = forward = None
    next_input = next_E = next_output = completed = time = live = peak_live = 0
    peak_forward = 0
    while completed < size:
        progress = False
        if controller is not None and controller[2] == time:
            phase, local, end = controller
            controller = None
            if phase == 'input':
                input_done[local] = end
            else:
                output_done[local] = end
                require(slots[local % depth] == local, 'output ACK wrong buffer owner')
                slots[local % depth] = None
                live -= 1
                completed += 1
            progress = True
        if E is not None and E[1] == time:
            local, end = E
            E = None
            node = nodes[local]
            E_done[local] = end
            if node[5] >= 0:
                require(forward == (node[5], node[3], node[4]), 'forward consumer identity')
                forward = None
            if node[6] >= 0:
                require(forward is None, 'overwrite live forward register')
                forward = (node[6], node[3], node[4])
                peak_forward = max(peak_forward, node[4] * 4)
            progress = True
        if E is None and next_E < size and input_done[next_E] >= 0:
            node = nodes[next_E]
            if node[5] >= 0:
                require(forward == (node[5], node[3], node[4]), 'E consumed unready forward')
            E_start[next_E] = time
            E = next_E, time + node[8]
            next_E += 1
            progress = True
        if controller is None:
            # Drain outputs before another read when both are ready, to avoid
            # retaining a completed packet while all finite input slots fill.
            if next_output < size and E_done[next_output] >= 0:
                output_start[next_output] = time
                controller = 'output', next_output, time + nodes[next_output][9]
                next_output += 1
                progress = True
            elif next_input < size and slots[next_input % depth] is None:
                ready = all((E_done[p] if phase == 'E' else output_done[p]) >= 0
                            for p, phase in deps[next_input])
                if ready:
                    node = nodes[next_input]
                    if node[5] >= 0:
                        require(forward == (node[5], node[3], node[4]), 'input forward not ready')
                    slots[next_input % depth] = next_input
                    input_start[next_input] = time
                    live += 1
                    peak_live = max(peak_live, live)
                    require(live <= depth, 'FIFO over-allocation')
                    controller = 'input', next_input, time + node[7]
                    next_input += 1
                    progress = True
        # Resolve zero-duration completions before advancing either resource.
        pending = ([controller[2]] if controller else []) + ([E[1]] if E else [])
        if any(end == time for end in pending):
            continue
        if completed == size:
            break
        require(bool(pending), 'finite pipeline deadlock')
        time = min(pending)
    require(controller is None and E is None and forward is None and live == 0,
            'unfinished resource/forward/output ACK at region boundary')
    S_ranges, E_ranges = [], []
    for local, node in enumerate(nodes):
        require(input_done[local] <= E_start[local] <= E_done[local] <= output_start[local]
                <= output_done[local], 'packet producer/consumer chronology')
        for producer, phase in deps[local]:
            ready_at = E_done[producer] if phase == 'E' else output_done[producer]
            require(ready_at <= input_start[local], 'read before producer forward/write ACK')
        if local >= depth:
            require(output_done[local - depth] <= input_start[local], 'early slot overwrite')
        if node[7]:
            S_ranges.append((input_start[local], input_done[local]))
        if node[9]:
            S_ranges.append((output_start[local], output_done[local]))
        E_ranges.append((E_start[local], E_done[local]))
    for ranges in (S_ranges, E_ranges):
        ranges.sort()
        require(all(a[1] <= b[0] for a, b in zip(ranges, ranges[1:])),
                'resource duplication/overlap')
    measured = region['end_subcycles'] - region['start_subcycles']
    E_work = sum(node[8] for node in nodes)
    controller_work = sum(node[7] + node[9] for node in nodes)
    require(max(E_work, controller_work) <= time <= measured, 'pipeline work/runtime bounds')
    if depth == 1:
        require(time == measured, 'depth1 did not reproduce full sequential region')
    return dict(source_subcycles=measured, replay_subcycles=time,
                E_service_subcycles=E_work, controller_service_subcycles=controller_work,
                E_controller_overlap_subcycles=E_work + controller_work - time,
                peak_live_slots=peak_live, peak_forward_bytes=peak_forward,
                peak_packet_input_bytes=peak_input, peak_packet_output_bytes=peak_output,
                output_ACKs=size)


def replay_events(events, row, depth, trace=None):
    header = event_header(events)
    trace = read_trace(Path(trace) if trace is not None else Path(header['trace_path']))
    require(header['trace_sha256'] == trace.sha256, 'replay trace SHA mismatch')
    expected_regions = vector_regions(trace)
    source = candidate = E_work = controller_work = count = nodes = 0
    peaks = dict(peak_live_slots=0, peak_forward_bytes=0,
                 peak_packet_input_bytes=0, peak_packet_output_bytes=0)
    for region, packets in iter_regions(events):
        require(count < len(expected_regions) and
                (region['begin'], region['end_exclusive']) == expected_regions[count],
                'replay region source identity')
        receipt = replay_region(region, packets, trace, depth)
        source += receipt['source_subcycles']
        candidate += receipt['replay_subcycles']
        E_work += receipt['E_service_subcycles']
        controller_work += receipt['controller_service_subcycles']
        count += 1
        nodes += receipt['output_ACKs']
        for key in peaks:
            peaks[key] = max(peaks[key], receipt[key])
    require(count == len(expected_regions), 'replay missing region')
    actual = row['detail']['end_subcycles']
    require(source <= actual, 'regions exceed full-model time')
    conditional = actual - source + candidate
    if depth == 1:
        require(conditional == actual, 'depth1 full-model replay mismatch')
    return dict(passed=True, depth=depth, source_region_subcycles=source,
                replay_region_subcycles=candidate, held_other_subcycles=actual - source,
                raw_source_time=actual / 300000000000,
                newcounterfactual_time=conditional / 300000000000,
                frozen_source_seconds=actual / 300000000000,
                counterfactual_seconds=conditional / 300000000000,
                counterfactual_tokens_per_second=row['tokens'] * 300000000000 / conditional,
                conditional_speedup=actual / conditional, E_instances=1,
                input_output_controller_instances=1,
                frozen_E_service_subcycles=E_work,
                frozen_controller_service_subcycles=controller_work,
                pipeline_overlap_subcycles=source - candidate,
                regions=count, packet_output_ACKs=nodes, **peaks,
                FIFO_data_capacity_bytes=depth * (768 + 256),
                independent_forward_capacity_bytes=256,
                forward_metadata_bytes=header['forward_metadata_bytes'],
                total_declared_data_bytes=depth * 1024 + 256,
                FIFO_control_area='not implemented or measured',
                unchanged_physical_U_S_bytes=16384,
                phase_DDR_and_cache_costs='frozen, not recomputed under concurrency',
                scope='conditional finite one-E/one-shared-controller replay with fixed '
                      'per-phase DDR/cache times; not a new full-system simulation or RTL result')
