"""Independent fixed-two-P capacity/port/context audit; no timing predictor.

Derives tile budgets, A transactions, native streaming work and both local-S
port workloads from the input trace. No accepted source is modified/imported.
"""
from collections import Counter
from copy import deepcopy
import hashlib
from pathlib import Path


KEYS = ('logical_read', 'logical_write', 'bus_read', 'bus_write', 'descriptors')
FLOWS = ('other', 'A', 'weight', 'dynamic_B', 'dot_output', 'U_read', 'U_write', 'KV_write')


def need(value, message):
    if not value:
        raise AssertionError(message)


def ceildiv(n, d):
    return (n+d-1)//d


def align(n):
    return ceildiv(n, 64)*64


def known_payload_thresholds():
    """Independent concrete payload proof for the 43KiB single-row question."""
    a = 11008*4
    psum, workspace = 8*12, 1024
    values = {bits: a+2*(256*8*(bits//8))+psum+workspace for bits in (8, 16)}
    need(values == {8: 49248, 16: 53344}, 'K256 payload threshold')
    need(all(49152 < cost <= 65536 for cost in values.values()), '48/64KiB threshold')
    return dict(A_bytes=a, K256_W8_bytes=values[8], K256_W16_bytes=values[16],
                additional_write_combine_bytes=512,
                K_at_48KiB={'W8': 248, 'W8_combine': 216, 'W16': 120, 'W16_combine': 104})


def trace_info(path):
    lines = Path(path).read_text(encoding='utf-8').splitlines()
    nt, no, tokens = map(int, lines[0].split())
    tensors = [tuple(map(int, line.split())) for line in lines[1:nt+1]]
    need(len(tensors) == nt, 'tensor count')
    need([t[0] for t in tensors] == list(range(nt)), 'tensor numbering')
    ops = []
    for line in lines[nt+1:]:
        x = line.split()
        ops.append(dict(out=int(x[0]), kind=x[1], r=int(x[3]), n=int(x[4]), k=int(x[5]),
                        batches=int(x[6]), layout=int(x[8]), inputs=list(map(int, x[10:]))))
    need(len(ops) == no, 'operator count')
    return tensors, ops, tokens


def blank_flow():
    return dict.fromkeys(KEYS, 0)


def transfer(flow, address, size, count=1):
    if not size or not count:
        return
    flow['logical_read'] += size*count
    flow['bus_read'] += ceildiv(address % 64 + size, 64)*64*count
    flow['descriptors'] += count


def derive(trace, capacity, contexts, switch, reuse, profile, variant):
    """Derive event counts; tensor bases are 1024-aligned in the frozen format."""
    tensors, ops, tokens = trace_info(trace)
    weight_bits = 8 if profile == 'queued_pipe_w8' else 16
    need(profile in ('queued_pipe_w8', 'queued_pipe_w16'), 'unsupported numeric profile')
    prefix, pair, combine = ('prefix' in variant, 'pair' in variant, 'combine' in variant)
    workspace = 1024 + (512 if combine else 0)
    context_keys = ('enabled_calls', 'groups', 'A_groups', 'A_loaded_bytes', 'A_saved_bytes',
                    'context_switches', 'switch_subcycles', 'psum_register_bytes_peak',
                    'completed_contexts')
    actors = [dict(context=dict.fromkeys(context_keys, 0),
                   flows={name: blank_flow() for name in ('A', 'weight', 'dynamic_B')},
                   input_service_beats=0, input_service_events=0,
                   result_store_beats=0, result_store_events=0,
                   commands=0, m_work=0, adapter_work=0, output_bytes=0,
                   prefix_loaded=0, prefix_saved=0, prefix_peak=0) for _ in range(2)]
    shapes = Counter()
    # Multiplicity is safe for event byte alignment: all tensor bases are multiples
    # of 1024. Deduplicate repeated shapes without sharing any scheduler code.
    plans = Counter()
    for op in ops:
        if op['kind'] != 'Dot':
            continue
        abits = tensors[op['inputs'][0]][2]
        bbits = weight_bits if op['layout'] == 0 else tensors[op['inputs'][1]][2]
        plans[(op['r'], op['n'], op['k'], op['batches'], op['layout'], abits, bbits)] += 1
        shapes[f"{op['r']}x{op['n']}x{op['k']}b{op['batches']}l{op['layout']}"] += 1
    scratch_peak, tile_shapes = 0, []
    for (rows, ncols, total_k, batches, layout, abits, bbits), multiplicity in plans.items():
        ab, bb = abits//8, bbits//8
        need(abits % 8 == bbits % 8 == 0, 'unsupported sub-byte operands')
        target = (contexts > 1 and rows == 1 and layout == 0 and
                  total_k*ab + 2*align(8*8*(weight_bits//8)) + 96 + workspace > capacity)
        for worker, actor in enumerate(actors):
            selected = [col for col in range(0, ncols, 8)
                        if ((col//16) % 2 if pair else (col//8) % 2) == worker]
            c = actor['context']
            if target:
                c['enabled_calls'] += multiplicity  # Empty P still invokes its worker.
            for batch in range(batches):
                for rr in range(0, rows, 8):
                    r = min(8, rows-rr)
                    maximum = (capacity-r*96-workspace)//(2*(r*ab+8*bb))
                    k_limit = min(256, max(8, maximum//8*8))
                    full_a = r*total_k*ab
                    if full_a + r*96 + workspace < capacity:
                        room = (capacity-full_a-r*96-workspace)//(16*bb)
                        if room >= 8:
                            k_limit = min(k_limit, room//8*8)
                    resident = bool(selected) and full_a + 2*align(8*k_limit*bb) + r*96 + workspace <= capacity
                    need(not (target and resident), 'resident/context budget overlap')
                    if rows == 1 and total_k == 11008 and abits == 32 and layout == 0 and selected:
                        known_payload_thresholds()
                        if capacity == 49152:
                            expected_k = {(8, False): 248, (8, True): 216,
                                          (16, False): 120, (16, True): 104}[(bbits, combine)]
                            need(k_limit == expected_k and resident and not target,
                                 '43KiB A residency at 48KiB requires documented K downgrade')
                        if capacity == 65536:
                            need(k_limit == 256 and resident and not target,
                                 '64KiB K256 residency/context exclusion')
                    fixed = 2*(align(r*k_limit*ab)+align(8*k_limit*bb))+align(r*96)+workspace
                    cache_k = (min(total_k, ((capacity-fixed)//(r*ab))//k_limit*k_limit)
                               if prefix and not resident and selected and fixed < capacity else 0)
                    prefix_bytes = r*cache_k*ab
                    groups = ceildiv(len(selected), contexts) if target else len(selected)
                    if selected:
                        tile_shapes.append(dict(rows=rows, N=ncols, K=total_k, r=r, bits=bbits,
                                                worker=worker, K_limit=k_limit, resident=resident,
                                                prefix_bytes=prefix_bytes, context_target=target,
                                                output_groups=groups, calls=multiplicity))
                    if target:
                        chunks = ceildiv(total_k, k_limit)
                        c['groups'] += groups*multiplicity
                        c['A_groups'] += (groups if reuse else len(selected))*chunks*multiplicity
                        c['context_switches'] += len(selected)*chunks*multiplicity
                        c['switch_subcycles'] += len(selected)*chunks*switch*1000*multiplicity
                        c['completed_contexts'] += len(selected)*multiplicity
                        c['psum_register_bytes_peak'] = max(c['psum_register_bytes_peak'], min(contexts, len(selected))*96)
                        loaded = prefix_bytes + (full_a-prefix_bytes)*(groups if reuse else len(selected))
                        c['A_loaded_bytes'] += loaded*multiplicity
                        c['A_saved_bytes'] += ((full_a-prefix_bytes)*(len(selected)-groups)*multiplicity if reuse else 0)
                    # A LOADs follow their actual address alignment, including row/K tails.
                    if resident:
                        transfer(actor['flows']['A'], (batch*rows+rr)*total_k*ab, full_a, multiplicity)
                    elif selected:
                        for row in range(r):
                            base = (batch*rows+rr+row)*total_k*ab
                            transfer(actor['flows']['A'], base, cache_k*ab, multiplicity)
                            repeats = groups if target and reuse else len(selected)
                            for start in range(cache_k, total_k, k_limit):
                                length = min(k_limit, total_k-start)
                                transfer(actor['flows']['A'], base+start*ab, length*ab, repeats*multiplicity)
                        actor['prefix_loaded'] += prefix_bytes*multiplicity
                        actor['prefix_saved'] += prefix_bytes*(len(selected)-1)*multiplicity
                        actor['prefix_peak'] = max(actor['prefix_peak'], prefix_bytes)
                    for col in selected:
                        n = min(8, ncols-col)
                        actor['output_bytes'] += r*n*4*multiplicity
                        actor['result_store_beats'] += ceildiv(r*n*4, 64)*multiplicity
                        actor['result_store_events'] += multiplicity
                        for start in range(0, total_k, k_limit):
                            k = min(k_limit, total_k-start)
                            a_bytes, b_bytes = r*k*ab, n*k*bb
                            footprint = 2*(align(a_bytes)+align(b_bytes))+r*n*12+workspace
                            if resident:
                                footprint = full_a+2*align(b_bytes)+r*n*12+workspace
                            if prefix_bytes:
                                footprint = 2*(align(a_bytes)+align(b_bytes))+align(r*96)+workspace+prefix_bytes
                            need(footprint <= capacity, 'derived P scratch overflow')
                            scratch_peak = max(scratch_peak, footprint)
                            actor['commands'] += multiplicity
                            tail = 4+(14 if start == 0 else 0)+(8+ceildiv(r*n, 4)*2 if start+k == total_k else 0)
                            actor['m_work'] += (r*ceildiv(k, 8)+tail)*multiplicity
                            actor['adapter_work'] += max(ceildiv(a_bytes, 32), ceildiv(b_bytes, 64))*multiplicity
                            actor['input_service_beats'] += ceildiv(a_bytes+b_bytes, 64)*multiplicity
                            actor['input_service_events'] += multiplicity
                            if layout == 0:
                                address = (batch*ncols*total_k+col*total_k+start*n)*bb
                                transfer(actor['flows']['weight'], address, b_bytes, multiplicity)
                            elif layout == 1:
                                for column in range(n):
                                    address = (batch*ncols*total_k+(col+column)*total_k+start)*bb
                                    transfer(actor['flows']['dynamic_B'], address, k*bb, multiplicity)
                            elif layout == 2:
                                for row in range(k):
                                    address = (batch*total_k*ncols+(start+row)*ncols+col)*bb
                                    transfer(actor['flows']['dynamic_B'], address, n*bb, multiplicity)
                            else:
                                raise AssertionError('unsupported Dot layout')
    return dict(tokens=tokens, actors=actors, shapes=dict(shapes), scratch_peak=scratch_peak,
                tile_budgets=tile_shapes)


def check(row, trace, capacity_bytes, dual, quarters, contexts, switch, reuse):
    need(capacity_bytes in (16384, 49152, 65536), 'P capacity choice')
    need(quarters in (4, 5, 6, 8), 'P throughput choice')
    need(contexts in (1, 8) and switch in (0, 1, 3, 8), 'context contract')
    h, d, c, x = (row[k] for k in ('hardware_study', 'detail', 'context_study', 'compare_study'))
    unit = quarters*250
    need(h['P_count'] == x['P_count'] == 2, 'P count changed')
    need(h['P_S_bytes'] == x['P_capacity_bytes'] == d['P_capacity_bytes'] == capacity_bytes, 'P capacity metadata')
    need(h['U_S_bytes'] == x['U_capacity_bytes'] == 16384, 'U capacity changed')
    need(h['total_private_S_bytes'] == 2*capacity_bytes+16384, 'total SRAM accounting')
    need(h['split_P_read_write_ports'] == x['dual_ports'] == bool(dual), 'port configuration')
    need(h['vector_lanes'] == 4 and h['aggregate_bandwidth_B_s'] == 17100000000, 'unadvertised arithmetic/bandwidth')
    need(h['S_port_bytes'] == h['DDR_beat_bytes'] == 64, 'port width changed')
    need(h['S_port_cycles'] == d['P_service_cycles'] == quarters/4, 'P cost metadata')
    need(x['P_port_quarter_cycles'] == quarters and x['P_port_subcycles'] == unit, 'P time scale')
    need(x['U_port_subcycles'] == 1000, 'U timing changed')
    need((c['contexts'], c['switch_cycles'], c['reuse_A']) == (contexts, switch, bool(reuse)), 'context metadata')
    need(row['P_scratch_peak_bytes'] <= capacity_bytes, 'P capacity overflow')
    need(row['U_cache_peak_bytes']+4096 <= 16384, 'U capacity overflow')
    need(row['max_outstanding_beats'] <= 32 and row['max_outstanding_descriptors'] <= 32, 'credit overflow')
    need(len(d['channels']) == len(d['P']) == len(c['P']) == len(h['P_ports']) == 2, 'worker/channel count')
    expected = derive(trace, capacity_bytes, contexts, switch, reuse, row['profile'], d['variant'])
    need(row['tokens'] == expected['tokens'], 'token count')
    need(abs(row['tokens_per_second']*row['seconds']-row['tokens']) < 1e-8, 'time conversion')
    need(d['subcycles_per_core_cycle'] == 1000, 'cycle scale')
    need(abs(row['seconds']*300e9-d['end_subcycles']) < 0.5, 'subcycle conversion')
    need(row['P_scratch_peak_bytes'] == expected['scratch_peak'], 'scratch accounting')
    need(row['M_commands'] == row['M_tiles'] == sum(a['commands'] for a in expected['actors']), 'M command accounting')
    need(row['M_work_ticks'] == sum(a['m_work'] for a in expected['actors']), 'native M work accounting')
    need(row['adapter_work_ticks'] == sum(a['adapter_work'] for a in expected['actors']), 'adapter work accounting')
    total = Counter()
    for worker, (channel, actor) in enumerate(zip(d['channels'], expected['actors'])):
        local = Counter()
        for name in FLOWS:
            local.update(channel['flows'][name])
        need(dict(local) == channel['traffic'], 'channel/flow conservation')
        need(channel['beats']*64 == local['bus_read']+local['bus_write'], 'bus beat conservation')
        need(channel['bus_work_subcycles'] <= d['end_subcycles'], 'DDR utilization')
        total.update(local)
        for name, wanted in actor['flows'].items():
            need(channel['flows'][name] == wanted, 'trace-derived '+name+' traffic P'+str(worker))
        output = channel['flows']['dot_output']
        need(output['logical_write'] == actor['output_bytes'], 'Dot output payload')
        p = d['P'][worker]
        need(sum(p[k] for k in ('consumer_ready_wait_subcycles', 'input_ACK_wait_subcycles',
                               'service_subcycles', 'output_subcycles')) == p['elapsed_subcycles'], 'P phase accounting')
        need(p['tiles'] == actor['commands'] and p['write_buffer_peak_bytes'] <= 512, 'P command/WB capacity')
        need((p['prefix_A_loaded_bytes'], p['prefix_A_saved_bytes'], p['prefix_peak_bytes']) ==
             (actor['prefix_loaded'], actor['prefix_saved'], actor['prefix_peak']), 'prefix attribution')
        ctx = c['P'][worker]
        for name, wanted in actor['context'].items():
            need(ctx[name] == wanted, 'context '+name+' P'+str(worker))
        need(ctx['A_bank_peak'] <= 2 and ctx['B_bank_peak'] <= 2, 'A/B slot limit')
        port, cal = h['P_ports'][worker], d['S_calendars'][worker]
        need(port['worker'] == port['DDR_channel'] == worker, 'P channel mapping')
        input_beats = sum(f['bus_read'] for f in actor['flows'].values())//64
        write_work = (input_beats+actor['result_store_beats'])*unit
        write_events = input_beats+actor['result_store_events']
        # DMA output reads have one local S reservation per actual external beat;
        # finite masked/WB output packing is also checked by the frozen oracle.
        read_work = (actor['input_service_beats']+output['bus_write']//64)*unit
        read_events = actor['input_service_events']+output['bus_write']//64
        want_write, want_wc = (write_work, write_events) if dual else (0, 0)
        want_read, want_rc = (read_work, read_events) if dual else (read_work+write_work, read_events+write_events)
        need(port['write_service_subcycles'] == want_write and port['write_reservations'] == want_wc,
             'P input/M-result S write work missing')
        need(port['read_or_unified_service_subcycles'] == want_read and port['read_or_unified_reservations'] == want_rc,
             'P M-supply/DMA-output S read work missing')
        need(cal['service_subcycles'] == want_read and cal['reservations'] == want_rc, 'S calendar/read conservation')
        need(cal['scheduled_wait_subcycles'] == port['read_or_unified_wait_subcycles'], 'S wait accounting')
        need(want_read <= d['end_subcycles'] and want_write <= d['end_subcycles'], 'S port utilization')
        if not dual:
            need(port['write_wait_subcycles'] == 0, 'unused write port waited')
    for supplied, counted in [('logical_read_bytes', 'logical_read'), ('logical_write_bytes', 'logical_write'),
                              ('read_bus_bytes', 'bus_read'), ('write_bus_bytes', 'bus_write'), ('dma_descriptors', 'descriptors')]:
        need(row[supplied] == total[counted], 'global '+supplied+' conservation')
    need({s['key']: s['calls'] for s in d['matrix_shapes']} == expected['shapes'], 'shape coverage')
    for flow in ('A', 'weight', 'dynamic_B', 'dot_output'):
        for key in KEYS:
            need(sum(s['flows'][flow][key] for s in d['matrix_shapes']) ==
                 sum(ch['flows'][flow][key] for ch in d['channels']), 'shape/flow conservation')
    u = d['S_calendars'][3]
    need(h['U_service_subcycles'] == u['service_subcycles'] and h['U_reservations'] == u['reservations'] and
         h['U_wait_subcycles'] == u['scheduled_wait_subcycles'], 'U calendar accounting')
    need(u['service_subcycles'] % 1000 == 0, 'U service granularity changed')
    need(u['service_subcycles'] <= d['end_subcycles'], 'U service utilization')
    return dict(passed=True, capacity_bytes=capacity_bytes, dual_ports=bool(dual), P_port_subcycles=unit,
                fixed_U_bytes=16384, fixed_U_port_subcycles=1000, independent_actors=expected['actors'],
                tile_budgets=expected['tile_budgets'],
                concrete_payload_thresholds=known_payload_thresholds(),
                scope='trace-derived budgets, A/weight traffic, native work and P local read/write service; no numeric/physical proof')


def assert_regression(row, old, kind='247'):
    clean = deepcopy(row)
    clean.pop('compare_study')
    if str(kind) == '247':
        clean['detail'].pop('P_capacity_bytes')
        clean['detail'].pop('P_service_cycles')
    elif str(kind) == '246':
        clean.pop('context_study')
        clean.pop('hardware_study')
    else:
        raise ValueError('unknown reference kind')
    need(clean == old, 'complete Issue'+str(kind)+' result regression')
    return dict(passed=True, reference_issue=str(kind), complete_fields_equal=True)


def check_U_reference(row, old):
    """Same trace/profile/variant: U capacity, local work and traffic stay fixed.

    U wall/queued-wait time may change with prior DDR row state; it is deliberately
    not compared. Call for every capacity/port experiment, including nondefault
    quarter-cycle costs, using an actual accepted 16KiB result as the reference.
    """
    for key in ('U_cache_peak_bytes', 'cache_hits', 'cache_misses', 'dirty_evictions',
                'dead_lines_discarded', 'vector_work_ticks', 'KV_state_write_bytes'):
        need(row[key] == old[key], 'U work/state changed: '+key)
    current, previous = row['detail']['S_calendars'][3], old['detail']['S_calendars'][3]
    for key in ('service_subcycles', 'reservations'):
        need(current[key] == previous[key], 'U local work changed: '+key)
    for channel, prior in zip(row['detail']['channels'], old['detail']['channels']):
        for flow in ('U_read', 'U_write', 'KV_write'):
            need(channel['flows'][flow] == prior['flows'][flow], 'U flow changed: '+flow)
    return dict(passed=True, U_state_local_work_and_traffic_equal=True,
                excluded='U wall time and scheduled wait may change with shared DDR state')


def reject_checks(row, trace, capacity_bytes, dual, quarters, contexts, switch, reuse):
    changes = [
        ('P_overflow', lambda r: r.__setitem__('P_scratch_peak_bytes', capacity_bytes+1)),
        ('U_expansion', lambda r: r['hardware_study'].__setitem__('U_S_bytes', 32768)),
        ('U_port_change', lambda r: r['compare_study'].__setitem__('U_port_subcycles', 1250)),
        ('missing_write_service', lambda r: r['hardware_study']['P_ports'][0].__setitem__('write_service_subcycles',
             r['hardware_study']['P_ports'][0]['write_service_subcycles']+250)),
        ('wrong_M_commands', lambda r: r.__setitem__('M_commands', r['M_commands']+1)),
        ('wrong_A_loads', lambda r: r['context_study']['P'][0].__setitem__('A_loaded_bytes',
             r['context_study']['P'][0]['A_loaded_bytes']+1)),
        ('wrong_psum_peak', lambda r: r['context_study']['P'][0].__setitem__('psum_register_bytes_peak', contexts*96+1)),
    ]
    rejected = []
    for name, change in changes:
        bad = deepcopy(row)
        change(bad)
        try:
            check(bad, trace, capacity_bytes, dual, quarters, contexts, switch, reuse)
        except AssertionError:
            rejected.append(name)
        else:
            raise AssertionError('accepted mutation '+name)
    return rejected


def verify_source_lock(root, expected):
    need(bool(expected), 'empty source lock')
    for name, wanted in expected.items():
        path = Path(root)/name
        need(hashlib.sha256(path.read_bytes()).hexdigest() == wanted, 'source drift '+name)
    return len(expected)


def source_lock_negative(root, expected):
    verify_source_lock(root, expected)
    bad = dict(expected)
    key = next(iter(bad))
    bad[key] = ('1' if bad[key][0] != '1' else '0')+bad[key][1:]
    try:
        verify_source_lock(root, bad)
    except AssertionError:
        return dict(passed=True, rejected='mismatched expected SHA', source_files_unchanged=True)
    raise AssertionError('accepted source SHA drift')
