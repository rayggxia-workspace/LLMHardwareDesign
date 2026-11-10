"""Independent traffic/work/capacity checks for the conditional shared A pool."""
from copy import deepcopy
from decimal import Decimal
from functools import lru_cache
import hashlib
import importlib.util
import math
from pathlib import Path

SCOPE = ('conditional shared read-only A pool -> finite per-P FIFO -> existing A feeder; '
         'two 16KiB P and one 16KiB U retained; measured R4 NExp profile retained; '
         '300MHz and shared-pool timing are architectural assumptions, not physical qualification')
RUN23_SHA = '52c5faaad4d67a30577a5b4bc6d564866627105d492ea37aabc31d5b5b5372ff'
R4_AUDIT_SHA = '8b5a414b0646c6ad36a4a21d794612401461522c888b79d4669948da4c96d1b8'
R4_GENERATOR_SHA = 'e16a2cffcf076b1d51fdd8cca5051561a16dc2fe549f8eb5b34829763faa9901'
FROZEN_INPUTS = {
    'run15-result.json': '31213ac812866f463c8bd6e32a97d41e74e570b5310b6689f15e1e8fc6727cbc',
    'r1-calibration-result.json': '78c57febe43f2a114a8a21ca9b5992b465d7b7589f05c83eb68e5f97923d4ef7',
    'r2-calibration-result.json': 'fb0b4d0d1251140655feea5bd671c196e5ae13b1fd47066dc22d6e1e1a2eac78',
    'run19-result.json': 'b16ff9a0209add1227177d1899bbf9928ae7e83d724a0c113469e7c860c97098',
    'calibration-result.json': '5abb31227f0c7b2c7ac9ff7eb8f80687569fab0b64bf74eb1a9ea6ccb54b518d',
    'run23-result.json': RUN23_SHA,
}
TRAFFIC_FIELDS = ('logical_read', 'logical_write', 'bus_read', 'bus_write', 'descriptors')
TRAFFIC_TOP = dict(logical_read='logical_read_bytes', logical_write='logical_write_bytes',
                   bus_read='read_bus_bytes', bus_write='write_bus_bytes', descriptors='dma_descriptors')


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


@lru_cache(maxsize=4)
def frozen_r4(repo):
    path = Path(repo) / 'project/experiments/iterative_speed/round04/audit.py'
    require(sha(path) == R4_AUDIT_SHA, 'frozen R4 audit source drift')
    generator = path.with_name('generate_round4.py')
    require(sha(generator) == R4_GENERATOR_SHA, 'frozen R4 generator source drift')
    spec = importlib.util.spec_from_file_location('shared_pool_frozen_R4_audit', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def lookup(prior, item):
    keys = ('workload', 'profile', 'variant', 'dual_ports', 'contexts', 'P_KiB',
            'P_port_quarters', 'policy_KiB', 'switch_cycles', 'reuse_A', 'iteration4_enabled')
    found = [c for c in prior['cases'] if all(c[k] == item[k] for k in keys)]
    require(len(found) == 1, 'unique actual run23 R4 case missing')
    return found[0]['result']


def area_budget(pool_kib, fifo_beats):
    require(pool_kib in (0, 32, 48, 96) and fifo_beats in (1, 2, 4, 8), 'invalid area configuration')
    bank_area = Decimal('0.092462050025')
    pool_banks = pool_kib // 4
    total_banks = 12 + pool_banks
    return dict(scope='conditional replication of existing 4KiB 1RW bank macro only',
                bank_KiB=4, bank_macro_proxy_mm2=float(bank_area),
                private_P_count=2, private_P_KiB_each=16, private_U_KiB=16,
                pool_KiB=pool_kib, total_S_KiB=48 + pool_kib,
                private_banks=12, additional_pool_banks=pool_banks, total_banks=total_banks,
                baseline_macro_proxy_mm2=float(12 * bank_area),
                additional_macro_proxy_mm2=float(pool_banks * bank_area),
                total_macro_proxy_mm2=float(total_banks * bank_area),
                two_P48_plus_U16_macro_proxy_mm2=float(28 * bank_area),
                two_P64_plus_U16_macro_proxy_mm2=float(36 * bank_area),
                max_added_periphery_vs_two_P48_mm2=float((28 - total_banks) * bank_area),
                max_added_periphery_vs_two_P64_mm2=float((36 - total_banks) * bank_area),
                FIFO_payload_bits=2 * fifo_beats * 64 * 8 if pool_kib else 0,
                FIFO_tag_bits='not yet synthesized',
                excludes=['pool routing and arbitration', 'FIFO registers and tags',
                          'control and interconnect', 'physical clock qualification',
                          'a real 1R1W macro cost', 'whole chip area'],
                physical_area_qualified=False)


@lru_cache(maxsize=32)
def trace_inventory(trace_path, pool_kib):
    """Count A extents from the input trace, independently of runtime ledgers."""
    parts = Path(trace_path).read_text(encoding='utf8').split()
    it = iter(parts)
    nt, no, tokens = (int(next(it)) for _ in range(3))
    tensors = []
    for expected in range(nt):
        tid, elements, bits, initial = (int(next(it)) for _ in range(4))
        require(tid == expected and elements >= 0 and bits in (8, 16, 32, 64), 'invalid tensor inventory')
        tensors.append((elements, bits, initial))
    eligible = []
    capacity = pool_kib * 1024
    for index in range(no):
        output, kind, elements = int(next(it)), next(it), int(next(it))
        rows, cols, k, batches, shift, layout, ni = (int(next(it)) for _ in range(7))
        inputs = [int(next(it)) for _ in range(ni)]
        require(0 <= output < nt and all(0 <= x < nt for x in inputs), 'tensor reference outside inventory')
        if not (capacity and kind == 'Dot' and layout == 0 and batches == 1
                and 1 <= rows <= 8 and len(inputs) >= 2 and tensors[inputs[0]][1] == 32):
            continue
        require(rows * k <= tensors[inputs[0]][0], 'A source extent exceeds tensor')
        full_stride = ((k * 4 + 63) // 64) * 64
        covered = k if rows * full_stride <= capacity else min(k, (capacity // rows // 4 // 256) * 256)
        if not covered:
            continue
        stride = ((covered * 4 + 63) // 64) * 64
        require(rows * stride <= capacity, 'independent prefix exceeds pool')
        eligible.append(dict(operation=index, tensor=inputs[0], rows=rows, cols=cols, k=k,
                             covered_k=covered, capacity_bytes=rows * stride,
                             payload_bytes=rows * covered * 4,
                             full=covered == k, row_stride_bytes=stride))
    require(next(it, None) is None, 'extra trace tokens')
    return dict(trace_sha256=sha(trace_path), tokens=tokens, pool_KiB=pool_kib,
                eligible_operations=len(eligible), full_operations=sum(x['full'] for x in eligible),
                partial_operations=sum(not x['full'] for x in eligible),
                fill_payload_bytes=sum(x['payload_bytes'] for x in eligible),
                fill_padded_bytes=sum(x['capacity_bytes'] for x in eligible),
                fill_descriptors=sum(x['rows'] * ((x['covered_k'] * 4 + 1023) // 1024) for x in eligible),
                resident_peak_bytes=max((x['capacity_bytes'] for x in eligible), default=0),
                operations=eligible)


def traffic(row):
    channels = row['detail']['channels']
    require(len(channels) == 2 and [c['channel'] for c in channels] == [0, 1], 'DDR channel topology drift')
    flow_totals = {}
    for channel in channels:
        flows = channel['flows']
        for flow, amounts in flows.items():
            require(set(amounts) == set(TRAFFIC_FIELDS), 'DDR flow ledger schema drift')
            for field in TRAFFIC_FIELDS:
                value = amounts[field]
                require(type(value) is int and value >= 0, 'negative/noninteger traffic')
                flow_totals.setdefault(flow, dict.fromkeys(TRAFFIC_FIELDS, 0))[field] += value
        for field in TRAFFIC_FIELDS:
            require(channel['traffic'][field] == sum(f[field] for f in flows.values()),
                    'channel traffic does not equal flow sum ' + field)
        require(channel['beats'] * 64 == channel['traffic']['bus_read'] + channel['traffic']['bus_write'],
                'DDR beats do not conserve bus bytes')
        require(channel['row_misses'] <= channel['beats'] and channel['direction_changes'] <= channel['beats'],
                'DDR timing event exceeds transferred beats')
    for field, top in TRAFFIC_TOP.items():
        require(row[top] == sum(c['traffic'][field] for c in channels), 'top DDR total mismatch ' + top)
    return flow_totals


def base_check(row, baseline, item):
    require(set(row) == set(baseline) | {'shared_pool_study'}, 'shared-pool changed RESULT schema beyond its own metadata')
    require(row['seconds'] > 0 and row['tokens'] > 0 and math.isfinite(row['tokens_per_second']), 'nonfinite timing')
    require(math.isclose(row['tokens_per_second'], row['tokens'] / row['seconds'], rel_tol=2e-10), 'token/s arithmetic mismatch')
    require(math.isclose(row['seconds'], row['detail']['end_subcycles'] / 300000000000,
                         rel_tol=2e-10, abs_tol=1e-12), 'elapsed time does not use unchanged 300MHz')
    require(row['ticks'] == (row['detail']['end_subcycles'] + 999) // 1000, 'core tick rounding mismatch')
    for key in ('profile', 'tokens', 'M_commands', 'M_tiles', 'M_work_ticks', 'vector_work_ticks',
                'adapter_work_ticks', 'KV_state_write_bytes', 'U_cache_peak_bytes',
                'cache_hits', 'cache_misses', 'dirty_evictions', 'dead_lines_discarded',
                'iteration_study', 'iteration4_study'):
        require(row[key] == baseline[key], 'unrelated arithmetic/cache/NExp work changed ' + key)
    for key in ('iteration2_study', 'iteration2_baseline_study'):
        require(row.get(key) == baseline.get(key), 'frozen NExp ledger changed ' + key)
    h, old_h = row['hardware_study'], baseline['hardware_study']
    for key in h:
        if key not in ('P_ports', 'U_wait_subcycles'):
            require(h[key] == old_h[key], 'fixed hardware/service contract changed ' + key)
    require(h['P_count'] == 2 and h['P_S_bytes'] == h['U_S_bytes'] == 16384
            and h['total_private_S_bytes'] == 49152 and h['split_P_read_write_ports'] is item['dual_ports'],
            'private capacities or local port layer drift')
    require(row['P_scratch_peak_bytes'] <= 16384 and row['U_cache_peak_bytes'] <= 16384,
            'private SRAM capacity exceeded')
    for p in row['detail']['P']:
        require(p['elapsed_subcycles'] == sum(p[k] for k in (
            'consumer_ready_wait_subcycles', 'input_ACK_wait_subcycles', 'service_subcycles', 'output_subcycles')),
            'P consumer stages do not conserve elapsed time')
    require(len(row['detail']['matrix_shapes']) == len(baseline['detail']['matrix_shapes']), 'matrix shape count drift')
    for current, old in zip(row['detail']['matrix_shapes'], baseline['detail']['matrix_shapes']):
        for key in ('key', 'calls', 'tiles', 'commands'):
            require(current[key] == old[key], 'matrix shape arithmetic drift ' + key)
    flows, old_flows = traffic(row), traffic(baseline)
    require(set(flows) == set(old_flows), 'new unaccounted DDR flow category')
    for current, old in zip(row['detail']['channels'], baseline['detail']['channels']):
        for name in current['flows']:
            if name != 'A':
                require(current['flows'][name] == old['flows'][name], 'non-A DDR traffic changed ' + name)
    for field in ('logical_write', 'bus_write'):
        require(flows['A'][field] == old_flows['A'][field] == 0, 'read-only A pool wrote A to DDR')
    return flows, old_flows


def check(row, baseline, trace, item):
    flows, old_flows = base_check(row, baseline, item)
    meta = row['shared_pool_study']
    facts = trace_inventory(str(Path(trace).resolve()), item['shared_pool_KiB'])
    if not item['shared_pool_KiB']:
        stripped = deepcopy(row)
        stripped.pop('shared_pool_study')
        require(stripped == baseline, 'pool0 complete RESULT differs from actual run23')
        require(meta['enabled'] is False and meta['capacity_bytes'] == 0 and
                meta['fifo_beats_per_P'] == item['fifo_beats'] and
                meta['read_latency_cycles'] == item['read_latency_cycles'] and
                meta['port_cycles'] == item['pool_port_cycles'], 'pool0 contract mismatch')
        for key in ('calls', 'full_calls', 'partial_calls', 'peak_bytes', 'fill_payload_bytes', 'fill_DDR_bus_bytes',
                    'fill_descriptors', 'fill_peak_descriptors', 'write_beats', 'write_bus_bytes',
                    'read_beats', 'read_bus_bytes', 'fill_subcycles', 'write_wait_subcycles',
                    'port_service_subcycles', 'port_wait_subcycles', 'max_live_workers',
                    'live_workers', 'completed_epochs', 'live_epoch'):
            require(meta[key] == 0, 'pool0 performed shared-pool work ' + key)
        require(meta['bank_service_subcycles'] == [0] * 4 and len(meta['P']) == 2,
                'pool0 shared bank service/topology drift')
        for index, worker in enumerate(meta['P']):
            require(worker['worker'] == index and all(value == 0 for key, value in worker.items() if key != 'worker'),
                    'pool0 performed FIFO work')
        return dict(passed=True, pool0_all_original_fields_exact=True,
                    trace_sha256=facts['trace_sha256'])
    checked = pool_check(meta, facts, item, row, baseline, flows, old_flows)
    return dict(passed=True, pool0_all_original_fields_exact=False,
                all_NExp_and_matrix_arithmetic_exact=True, non_A_DDR_flows_exact=True,
                trace=facts, pool=checked)


def pool_check(meta, facts, item, row, baseline, flows, old_flows):
    constants = dict(schema=1, enabled=True, capacity_bytes=item['shared_pool_KiB'] * 1024,
                     fifo_beats_per_P=item['fifo_beats'], fifo_beat_bytes=64,
                     read_latency_cycles=item['read_latency_cycles'], port_cycles=item['pool_port_cycles'],
                     banks=4, bank_width_bits=128, bank_mode='1RW lockstep lanes', fabric_bytes=64,
                     A_feeder_bytes_per_cycle=32, broadcast=False,
                     fill_descriptor_max_bytes=1024, fill_descriptor_limit=2,
                     scope='conditional SystemC timing; no RTL or physical qualification')
    for key, value in constants.items():
        require(meta[key] == value, 'shared pool contract drift ' + key)
    for key, value in meta.items():
        if type(value) is int:
            require(value >= 0, 'negative pool counter ' + key)
    require(meta['calls'] == facts['eligible_operations'] == meta['completed_epochs'],
            'pool operation generations differ from trace')
    require(meta['full_calls'] == facts['full_operations'] and meta['partial_calls'] == facts['partial_operations'],
            'full/partial pool coverage differs from independent capacity calculation')
    require(meta['peak_bytes'] == facts['resident_peak_bytes'] <= meta['capacity_bytes'],
            'pool peak padded occupancy mismatch')
    require(meta['fill_payload_bytes'] == facts['fill_payload_bytes'], 'pool fill payload missing/duplicated')
    require(meta['fill_descriptors'] == facts['fill_descriptors'], '1024B fill descriptor count mismatch')
    require(0 < meta['fill_peak_descriptors'] <= 2 and meta['fill_peak_descriptors'] <= meta['fill_descriptors'],
            'fill descriptor capacity exceeded')
    require(meta['write_bus_bytes'] == facts['fill_padded_bytes'] == meta['write_beats'] * 64,
            'pool fill bus service does not cover padded rows')
    require(meta['fill_DDR_bus_bytes'] == facts['fill_padded_bytes'], 'shared fill DDR bytes differ from trace extents')
    require(meta['read_bus_bytes'] == meta['read_beats'] * 64, 'pool read service bytes mismatch')
    require(meta['port_service_subcycles'] == (meta['write_beats'] + meta['read_beats']) *
            item['pool_port_cycles'] * 1000, 'pool read/write service was not charged')
    require(meta['bank_service_subcycles'] == [meta['port_service_subcycles']] * 4,
            'four physical-width lanes do not conserve shared 1RW service')
    require(meta['port_service_subcycles'] <= row['detail']['end_subcycles'],
            'single shared pool fabric overlaps its own service')
    require(meta['live_workers'] == meta['live_epoch'] == 0 and 0 < meta['max_live_workers'] <= 2,
            'pool released before all readers drained')
    require(meta['fill_subcycles'] >= meta['write_beats'] * item['pool_port_cycles'] * 1000,
            'pool fills faster than their own required SRAM writes')
    require(len(meta['P']) == 2 and [w['worker'] for w in meta['P']] == [0, 1], 'pool consumer topology changed')
    avoided_payload = avoided_bus = avoided_descriptors = read_payload = read_bus = read_count = 0
    expected_P = []
    for index, w in enumerate(meta['P']):
        for key, value in w.items():
            require(type(value) is int and (value >= 0 or key == 'avoided_A_DDR_descriptors'),
                    'invalid pool worker counter ' + key)
        require(w['active'] == 0 and 0 < w['fifo_peak'] <= item['fifo_beats'], 'FIFO leak/capacity exceeded')
        require(w['read_bytes'] == w['consumed_bytes'] == w['bypassed_local_A_read_bytes'],
                'pool read/FIFO consumed/local bypass bytes not conserved')
        require(w['read_bus_bytes'] == w['reads'] * 64 >= w['read_bytes'], 'pool read beats missing')
        require(w['latency_subcycles'] == w['reads'] * item['read_latency_cycles'] * 1000,
                'shared pool read latency ledger mismatch')
        require(w['feed_subcycles'] >= ((w['consumed_bytes'] + 31) // 32) * 1000,
                'A FIFO consumed faster than its 32B/cycle feeder')
        require(w['avoided_local_write_subcycles'] == w['avoided_A_DDR_bus_bytes'] // 64 * 1000
                and w['avoided_A_DDR_bus_bytes'] % 64 == 0, 'local A input-write bypass fee mismatch')
        # Enumerate full-K arithmetic input coverage independently of runtime
        # counters. The existing 16KiB scratch bound also determines W16's
        # shorter resident-A tile; its unaligned 64B rereads are charged.
        expected_bytes = expected_beats = expected_tiles = expected_local_bytes = expected_read_saved = 0
        pair = 'pair' in item['variant']
        weight_bytes = 1 if item['profile'] == 'queued_pipe_w8' else 2
        workspace = 1536 if 'combine' in item['variant'] else 1024
        for op in facts['operations']:
            require(op['rows'] <= 2, 'independent main-case read inventory needs extension for r>2')
            columns = [col for col in range(0, op['cols'], 8) if ((col // (16 if pair else 8)) % 2) == index]
            ncols = len(columns)
            expected_bytes += op['payload_bytes'] * ncols
            full_a = op['rows'] * op['k'] * 4
            max_k = (16384 - op['rows'] * 96 - workspace) // (2 * (op['rows'] * 4 + 8 * weight_bytes))
            tile_k = min(256, max(8, max_k // 8 * 8))
            if full_a + op['rows'] * 96 + workspace < 16384:
                resident_k = (16384 - full_a - op['rows'] * 96 - workspace) // (16 * weight_bytes)
                if resident_k >= 8:
                    tile_k = min(tile_k, resident_k // 8 * 8)
            for ki in range(0, op['k'], tile_k):
                count = min(tile_k, op['k'] - ki)
                shared_k = max(0, min(count, op['covered_k'] - ki))
                expected_beats += (op['rows'] * ((ki * 4 % 64 + shared_k * 4 + 63) // 64)
                                   if shared_k else 0) * ncols
                expected_local_bytes += op['rows'] * (count - shared_k) * 4 * ncols
                expected_tiles += ncols
                for col in columns:
                    a_bytes = op['rows'] * count * 4
                    b_bytes = min(8, op['cols'] - col) * count * weight_bytes
                    hit = op['rows'] * shared_k * 4
                    expected_read_saved += (((a_bytes + b_bytes + 63) // 64) -
                                            ((a_bytes + b_bytes - hit + 63) // 64)) * 1000
        require(w['read_bytes'] == expected_bytes and w['reads'] == expected_beats,
                'shared A read count differs from independent trace/two-P column inventory')
        require(w['completed_tiles'] == expected_tiles and w['local_A_read_bytes'] == expected_local_bytes,
                'shared feeder tile count/local fallback differs from independent inventory')
        require(w['avoided_local_read_subcycles'] == expected_read_saved,
                'local read bypass fee differs from independent tile byte bounds')
        expected_P.append(dict(worker=index, shared_A_bytes=expected_bytes, shared_read_beats=expected_beats,
                               active_tiles=expected_tiles, local_A_bytes=expected_local_bytes,
                               avoided_local_read_subcycles=expected_read_saved))
        current, old = row['hardware_study']['P_ports'][index], baseline['hardware_study']['P_ports'][index]
        read_delta = old['read_or_unified_service_subcycles'] - current['read_or_unified_service_subcycles']
        write_delta = old['write_service_subcycles'] - current['write_service_subcycles']
        if item['dual_ports']:
            require(read_delta == w['avoided_local_read_subcycles']
                    and write_delta == w['avoided_local_write_subcycles'],
                    'local separate read/write service reduction differs from exact bypass ledger')
        else:
            require(write_delta == 0 and read_delta == w['avoided_local_read_subcycles'] +
                    w['avoided_local_write_subcycles'], 'local 1RW service reduction differs from bypass ledger')
        avoided_payload += w['avoided_A_DDR_bytes']
        avoided_bus += w['avoided_A_DDR_bus_bytes']
        avoided_descriptors += w['avoided_A_DDR_descriptors']
        read_payload += w['read_bytes']
        read_bus += w['read_bus_bytes']
        read_count += w['reads']
    require(read_bus == meta['read_bus_bytes'] and read_count == meta['read_beats'],
            'shared read totals differ from two FIFO consumers')
    require(meta['port_wait_subcycles'] == meta['write_wait_subcycles'] +
            sum(w['port_wait_subcycles'] for w in meta['P']), 'shared 1RW wait work not conserved')
    require(flows['A']['logical_read'] == old_flows['A']['logical_read'] - avoided_payload + meta['fill_payload_bytes'],
            'A DDR payload reduction omitted shared fill or local fallback')
    require(flows['A']['bus_read'] == old_flows['A']['bus_read'] - avoided_bus + meta['fill_DDR_bus_bytes'],
            'A DDR bus reduction omitted shared fill or local fallback')
    require(flows['A']['descriptors'] == old_flows['A']['descriptors'] - avoided_descriptors + meta['fill_descriptors'],
            'A DDR descriptor reduction omitted shared fill or local fallback')
    return dict(independent_P_reads=expected_P, shared_A_read_payload_bytes=read_payload,
                avoided_A_DDR_payload_bytes=avoided_payload,
                added_shared_fill_payload_bytes=meta['fill_payload_bytes'],
                net_A_DDR_payload_saved=old_flows['A']['logical_read'] - flows['A']['logical_read'],
                net_A_DDR_bus_saved=old_flows['A']['bus_read'] - flows['A']['bus_read'],
                no_broadcast=True, no_cross_operation_residency=True,
                pool_1RW_read_write_service_conserved=True, finite_FIFO_capacity_checked=True,
                local_S_service_reduction_exact=True)


def reject_checks(row, baseline, trace, item):
    changes = [('M_work_missing', lambda r: r.__setitem__('M_work_ticks', r['M_work_ticks'] - 1)),
               ('DDR_byte_missing', lambda r: r.__setitem__('read_bus_bytes', r['read_bus_bytes'] - 1)),
               ('R4_identity_changed', lambda r: r['iteration4_study'].__setitem__('new_calibration_result_sha256', '0' * 64)),
               ('area_hidden_in_private', lambda r: r['hardware_study'].__setitem__('P_S_bytes', 65536))]
    if item['shared_pool_KiB']:
        changes += [
            ('pool_write_fee_missing', lambda r: r['shared_pool_study'].__setitem__(
                'port_service_subcycles', r['shared_pool_study']['port_service_subcycles'] - 1000)),
            ('FIFO_capacity_exceeded', lambda r: r['shared_pool_study']['P'][0].__setitem__('fifo_peak', 9)),
            ('pool_payload_lost', lambda r: r['shared_pool_study']['P'][0].__setitem__(
                'consumed_bytes', r['shared_pool_study']['P'][0]['consumed_bytes'] - 1)),
            ('pool_capacity_hidden', lambda r: r['shared_pool_study'].__setitem__('capacity_bytes', 1024)),
            ('pool_not_drained', lambda r: r['shared_pool_study'].__setitem__('live_epoch', 1)),
            ('A_repeated_read_erased', lambda r: r['shared_pool_study']['P'][0].__setitem__(
                'read_bytes', r['shared_pool_study']['P'][0]['read_bytes'] - 64))]
    rejected = []
    for name, change in changes:
        bad = deepcopy(row)
        change(bad)
        try:
            check(bad, baseline, trace, item)
        except (ValueError, KeyError):
            rejected.append(name)
        else:
            raise ValueError('corrupt result accepted ' + name)
    return rejected
