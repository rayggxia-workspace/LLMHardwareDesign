"""Independent legality, U cache/traffic/service and actual event audit."""
from copy import deepcopy
from pathlib import Path

from fusion_contract import ELEMENTWISE, legal_edges, read_trace, require, vector_regions
from u_ledger import Ledger, check as check_U_ledger
from replay import inspect_events


_LEDGERS = {}


def ledger_for(trace, fusion):
    key = trace.sha256, bool(fusion)
    if key not in _LEDGERS:
        edges = legal_edges(trace, True)[0] if fusion else []
        _LEDGERS[key] = Ledger(trace, edges).run()
    return _LEDGERS[key]


def metadata_expected(trace, fusion, fee):
    edges = legal_edges(trace, True)[0]
    enabled = edges if fusion else []
    packets = sum((edge['elements'] + 63) // 64 for edge in enabled)
    forwarded_bytes = sum(edge['write_and_read_bytes'] // 2 for edge in enabled)
    direction_service = sum(edge['S_cycles_saved'] // 2 for edge in enabled) * 1000
    RF_cycles = sum((edge['elements'] + 3) // 4 for edge in enabled)
    regions = vector_regions(trace)
    E_work = node_count = 0
    for begin, stop in regions:
        count = trace.ops[begin].elements
        active = sum(trace.ops[i].kind in ELEMENTWISE for i in range(begin, stop))
        chunks, tail = divmod(count, 64)
        node_count += (chunks + bool(tail)) * active
        E_work += (chunks * 21 + (((tail + 3) // 4 + 5) if tail else 0)) * active * 1000
    return dict(fusion_enabled=bool(fusion), forward_control_cycles=fee,
                forward_capacity_bytes=256, forward_metadata_bytes=32,
                eligible_graph_edges=len(edges), forwarded_packets=packets,
                forwarded_bytes=forwarded_bytes, saved_S_read_bytes=forwarded_bytes,
                saved_S_write_bytes=forwarded_bytes,
                saved_S_read_service_subcycles=direction_service,
                saved_S_write_service_subcycles=direction_service,
                saved_S_read_reservations=packets, saved_S_write_reservations=packets,
                forward_control_subcycles=packets * fee * 1000,
                forward_peak_bytes=max((edge['register_bytes'] for edge in enabled), default=0),
                E_arithmetic_subcycles=E_work, packet_count=node_count, region_count=len(regions),
                register_read_packet_cycles=RF_cycles, register_write_packet_cycles=RF_cycles,
                event_log_enabled=True, event_schema_version=1)


def audit_case(row, old, trace, events, fusion, fee):
    require(fusion in (False, True, 0, 1) and fee in (0, 1, 3), 'unsupported fusion setting')
    # Cheap checks deliberately precede trace/cache/event work. Runner mutations
    # must not rescan a large prefill JSONL just to reject changed M work/metadata.
    for key in ('profile', 'tokens', 'M_work_ticks', 'M_commands', 'M_tiles',
                'vector_work_ticks', 'adapter_work_ticks', 'P_scratch_peak_bytes',
                'KV_state_write_bytes', 'resident_A_saved_bytes'):
        require(row[key] == old[key], 'changed nonfusion arithmetic/P/state: ' + key)
    meta = row['u_fusion_study']
    require(0 <= meta['forward_peak_bytes'] <= 256, 'forward register capacity')
    require(meta['forwarded_bytes'] == meta['saved_S_read_bytes'] == meta['saved_S_write_bytes'],
            'forward data byte conservation')
    require(meta['fusion_enabled'] == bool(fusion) and meta['forward_control_cycles'] == fee,
            'requested fusion mode/fee metadata')
    trace = read_trace(Path(trace))
    expected_meta = metadata_expected(trace, fusion, fee)
    for key, expected in expected_meta.items():
        require(meta[key] == expected, 'independent fusion metadata: ' + key)
    require(bool(meta.get('scope')), 'missing model scope')
    for key in ('compare_study', 'context_study', 'policy_study'):
        require(row[key] == old[key], 'unrelated hardware/policy/context change: ' + key)
    if not fusion:
        clean = deepcopy(row)
        del clean['u_fusion_study']
        require(clean == old, 'default result is not exact prior-run replay')
    baseline = ledger_for(trace, False)
    expected = ledger_for(trace, fusion)
    check_U_ledger(old, baseline)
    check_U_ledger(row, expected)
    h, old_h = row['hardware_study'], old['hardware_study']
    excluded_hardware = {'P_ports', 'U_service_subcycles', 'U_wait_subcycles', 'U_reservations'}
    require({k: v for k, v in h.items() if k not in excluded_hardware} ==
            {k: v for k, v in old_h.items() if k not in excluded_hardware}, 'hardware contract drift')
    require(h['U_S_bytes'] == 16384 and h['vector_lanes'] == 4, 'U hardware budget drift')
    require(h['U_wait_subcycles'] == 0, 'unexpected U contention in sequential source model')
    require(len(h['P_ports']) == len(old_h['P_ports']), 'P port count')
    for port, original in zip(h['P_ports'], old_h['P_ports']):
        require({k: v for k, v in port.items() if 'wait' not in k} ==
                {k: v for k, v in original.items() if 'wait' not in k}, 'P port service/work drift')
    for actor, original in zip(row['detail']['P'], old['detail']['P']):
        for key in ('worker', 'tiles', 'prefix_A_loaded_bytes', 'prefix_A_saved_bytes',
                    'prefix_peak_bytes', 'write_buffer_peak_bytes'):
            require(actor[key] == original[key], 'P actor work/capacity drift')
    for calendar, original in zip(row['detail']['S_calendars'][:3], old['detail']['S_calendars'][:3]):
        for key in ('group', 'service_subcycles', 'reservations'):
            require(calendar[key] == original[key], 'P/unused S work drift')
    Ucal = row['detail']['S_calendars'][3]
    require(Ucal['service_subcycles'] == h['U_service_subcycles'] and
            Ucal['reservations'] == h['U_reservations'], 'U detail/hardware disagreement')
    for field, flow_key in (('read_bus_bytes', 'bus_read'), ('write_bus_bytes', 'bus_write'),
                            ('logical_read_bytes', 'logical_read'),
                            ('logical_write_bytes', 'logical_write'), ('dma_descriptors', 'descriptors')):
        delta = sum(expected['flows'][name][flow_key] - baseline['flows'][name][flow_key]
                    for name in expected['flows'])
        require(row[field] == old[field] + delta, 'global U traffic conservation: ' + field)
    for channel, original in zip(row['detail']['channels'], old['detail']['channels']):
        require(channel['channel'] == original['channel'], 'DDR channel remapping')
        for flow in ('A', 'weight', 'dynamic_B', 'dot_output', 'KV_write', 'other'):
            require(channel['flows'][flow] == original['flows'][flow], 'changed non-U flow: ' + flow)
        for key in channel['traffic']:
            require(channel['traffic'][key] == sum(f[key] for f in channel['flows'].values()),
                    'flow/channel traffic conservation')
        beats = (channel['traffic']['bus_read'] + channel['traffic']['bus_write']) // 64
        require(channel['beats'] == beats, 'channel beat count')
        require(channel['bus_work_subcycles'] * original['beats'] ==
                original['bus_work_subcycles'] * beats, 'DDR byte service changed')
    shapes = {shape['key']: shape for shape in old['detail']['matrix_shapes']}
    require(set(shapes) == {s['key'] for s in row['detail']['matrix_shapes']}, 'matrix shape drift')
    for shape in row['detail']['matrix_shapes']:
        original = shapes[shape['key']]
        for key in ('calls', 'tiles', 'commands'):
            require(shape[key] == original[key], 'matrix work changed')
        for flow in ('A', 'weight', 'dynamic_B', 'dot_output'):
            require(shape['flows'][flow] == original['flows'][flow], 'matrix payload changed')
    observed = inspect_events(events, trace, fusion, fee)
    require(observed['event_facts_sha256'] == expected['event_facts_sha256'],
            'independent per-packet input/output/forward/arithmetic facts differ')
    require(observed['nodes'] == meta['packet_count'] and observed['regions'] == meta['region_count'],
            'event/summary coverage')
    require(observed['forwarded_bytes'] == meta['forwarded_bytes'] and
            observed['forwarded_packets'] == meta['forwarded_packets'], 'event forwarding count')
    require(observed['E_arithmetic_subcycles'] == meta['E_arithmetic_subcycles'] and
            observed['control_subcycles'] == meta['forward_control_subcycles'], 'event fee/work')
    return dict(passed=True, exact_prior_regression=not bool(fusion),
                independent_U_cache_and_flow_replay=True, per_packet_work_and_dependencies_audited=True,
                E_instances=1, U_S_bytes=16384, preserved_per_operator_quantization_required=True,
                unmodelled_existing_control_savings=0, existing_canonical_savings_reclaimed=0,
                trace_sha256=trace.sha256, events=observed,
                scope='actual sequential model conservation plus independent access ledger; '
                      'not RTL/numerical inference or a concurrent DDR simulation')
