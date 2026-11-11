"""Policy-only comparison against an actual run04 result of identical hardware.

No frozen audit/generator is changed. Runtime/waits/queue occupancy/DRAM row
events may change; payload, work, capacities, interfaces and local S service may
not. The caller still runs compare_audit.check for independent trace checks.
"""
from copy import deepcopy


def need(condition, message):
    if not condition:
        raise AssertionError(message)


def invariant_view(row):
    top = ('profile', 'tokens', 'read_bus_bytes', 'write_bus_bytes',
           'logical_read_bytes', 'logical_write_bytes', 'dma_descriptors',
           'U_cache_peak_bytes', 'P_scratch_peak_bytes', 'cache_hits',
           'cache_misses', 'dirty_evictions', 'dead_lines_discarded',
           'M_commands', 'M_tiles', 'KV_state_write_bytes', 'resident_A_saved_bytes',
           'M_work_ticks', 'vector_work_ticks', 'adapter_work_ticks')
    d = row['detail']
    channels = []
    for channel in d['channels']:
        channels.append({key: deepcopy(channel[key]) for key in
                         ('channel', 'traffic', 'flows', 'beats', 'bus_work_subcycles')})
    actors = []
    for actor in d['P']:
        actors.append({key: deepcopy(actor[key]) for key in
                       ('worker', 'tiles', 'prefix_A_loaded_bytes', 'prefix_A_saved_bytes',
                        'prefix_peak_bytes', 'write_buffer_peak_bytes')})
    calendars = [{key: cal[key] for key in ('group', 'service_subcycles', 'reservations')}
                 for cal in d['S_calendars']]
    shapes = {}
    for shape in d['matrix_shapes']:
        need(shape['key'] not in shapes, 'duplicate matrix shape')
        shapes[shape['key']] = {key: deepcopy(shape[key]) for key in
                                ('calls', 'tiles', 'commands', 'flows')}
    hardware = deepcopy(row['hardware_study'])
    # Every local port's actual work and number of requests are compared, not
    # merely its declared width/latency. Scheduling waits alone may vary.
    hardware.pop('U_wait_subcycles')
    for port in hardware['P_ports']:
        port.pop('read_or_unified_wait_subcycles')
        port.pop('write_wait_subcycles')
    return dict(top={key: row[key] for key in top},
                detail_metadata={key: d[key] for key in
                                 ('variant', 'subcycles_per_core_cycle',
                                  'P_capacity_bytes', 'P_service_cycles')},
                channels=channels, P_actors=actors, S_calendars=calendars,
                matrix_shapes=shapes, hardware=hardware,
                context=deepcopy(row['context_study']),
                capacity_port=deepcopy(row['compare_study']))


def check_policy(row, run04_same_config, policy_kib):
    need(policy_kib in (0, 16), 'unsupported policy override')
    need('policy_study' not in run04_same_config,
         'reference must be actual run04 output without a policy extension')
    meta = row['policy_study']
    actual = row['compare_study']['P_capacity_bytes']
    need(meta['requested_policy_KiB'] == policy_kib, 'policy request metadata')
    need(meta['actual_P_capacity_bytes'] == actual == row['hardware_study']['P_S_bytes']
         == row['detail']['P_capacity_bytes'], 'actual capacity changed by policy')
    expected = 16384 if policy_kib else actual
    need(meta['effective_policy_bytes'] == expected, 'effective policy threshold')
    need(isinstance(meta['scope'], str) and bool(meta['scope']), 'missing policy scope')
    current = invariant_view(row)
    reference = invariant_view(run04_same_config)
    for section, value in current.items():
        need(value == reference[section], 'policy changed payload/work/hardware: '+section)
    identical_path = policy_kib == 0 or actual == 16384
    if identical_path:
        clean = deepcopy(row)
        del clean['policy_study']
        need(clean == run04_same_config, 'same-path policy complete-result regression')
    return dict(passed=True, requested_policy_KiB=policy_kib,
                effective_policy_bytes=expected, actual_P_capacity_bytes=actual,
                hardware_payload_M_vector_context_and_S_work_equal=True,
                U_actual_state_traffic_and_local_service_equal=True,
                complete_result_equal_required=identical_path,
                allowed_changes='runtime, stage spans, queue occupancy, DDR row/bank/order '
                                'events, consumer/producer waits and local-port waits',
                scope='policy-only resource/work conservation against actual same-hardware run04; '
                      'not a prediction of physical arbitration or real tensor quality')


def reject_checks(row, run04_same_config, policy_kib):
    changes = [
        ('false_policy_metadata', lambda r: r['policy_study'].__setitem__(
            'requested_policy_KiB', 16 if policy_kib == 0 else 0)),
        ('hidden_M_work', lambda r: r.__setitem__('M_work_ticks', r['M_work_ticks']-1)),
        ('hidden_A_traffic', lambda r: r['detail']['channels'][0]['flows']['A'].__setitem__(
            'logical_read', r['detail']['channels'][0]['flows']['A']['logical_read']-1)),
        ('hidden_S_write_service', lambda r: r['hardware_study']['P_ports'][0].__setitem__(
            'write_service_subcycles', r['hardware_study']['P_ports'][0]['write_service_subcycles']+250)),
        ('hidden_U_service', lambda r: r['hardware_study'].__setitem__(
            'U_service_subcycles', r['hardware_study']['U_service_subcycles']+1000)),
        ('hidden_S_reservations', lambda r: r['detail']['S_calendars'][0].__setitem__(
            'reservations', r['detail']['S_calendars'][0]['reservations']+1)),
    ]
    rejected = []
    for name, mutate in changes:
        bad = deepcopy(row)
        mutate(bad)
        try:
            check_policy(bad, run04_same_config, policy_kib)
        except AssertionError:
            rejected.append(name)
        else:
            raise AssertionError('accepted policy mutation '+name)
    return rejected
