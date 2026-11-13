"""Bounded virtual LOAD/STORE interface, using the pinned PR182 policy.

This is a compiler timing model, not a requirement to instantiate DMA RTL or
to finish physical routing. PR182's finite credits, queue, bank timing and
128-bit requests are retained. Descriptor service is conservatively serialized
per channel; words within a descriptor can overlap up to its finite credit.
S access times are supplied by the actual endpoint profile, not guessed here.
"""
from copy import deepcopy
import math
import re

PIN = '24e20d13a71cf65f721a182451308f1ad01ebaec'


def profile_from_source(text):
    """Read the checked-in test_dma.cpp configuration; fail on source drift."""
    config = re.search(r'struct Config\{(.*?)\};', text, re.S).group(1)
    names = ('channels', 'credits', 'queue', 'period', 'phase', 'latency', 'seed')
    result = {n: int(re.search(r'\b' + n + r'=(\d+)', config).group(1)) for n in names}
    checks = {
        'core_period': r'now%10==0', 'bank_index': r'\(r.address/64\)%4',
        'row_index': r'r.address/1024', 'bank_issue': r'bank.free=command\+2',
        'row_miss': r'bank.row==row\?0:6', 'turnaround': r'm.busfree=mems\+4',
    }
    for name, pattern in checks.items():
        if not re.search(pattern, text):
            raise ValueError('PR182 memory source changed: ' + name)
    result.update(kind='pr182-bounded-v1', source_commit=PIN,
        word_bytes=16, core_period=10, address_bits=40, slots=8,
        bank_count=4, bank_interleave_bytes=64, row_bytes=1024,
        bank_issue_cycles=2, row_miss_cycles=6, turnaround_cycles=4,
        scope='deterministic compiler abstraction; not RTL/VIP or device calibration',
        randomness='disabled explicitly; no reuse of PR182 measured throughput')
    return result


def descriptor_ticks(profile, words, direction, s_access_ticks):
    """Finite-credit, finite-queue word timing, in declared core cycles.

    Cold banks and a direction turnaround are charged on every descriptor.
    This does not predict the concurrent RR/CDC behavior of the RTL. Shared
    channel exclusion below intentionally gives a conservative serial model.
    """
    if direction not in ('load', 'store') or words < 1 or s_access_ticks < 1:
        raise ValueError('invalid modeled descriptor')
    if profile['kind'] != 'pr182-bounded-v1':
        raise ValueError('unknown virtual memory model')
    positive = ('period', 'core_period', 'slots', 'queue', 'bank_count', 'bank_interleave_bytes', 'row_bytes', 'bank_issue_cycles', 'word_bytes')
    if any(profile[k] < 1 for k in positive) or not 1 <= profile['credits'] <= profile['slots']:
        raise ValueError('invalid virtual memory clock/capacity/credit parameters')
    if not 0 <= profile['phase'] < profile['period'] or any(profile[k] < 0 for k in ('latency', 'row_miss_cycles', 'turnaround_cycles')):
        raise ValueError('invalid virtual memory phase/latency')
    credit = min(profile['credits'], profile['queue'], profile['slots'])
    if credit < 1 or profile['channels'] not in (1, 2, 4):
        raise ValueError('invalid PR182 credits/channels')
    # Track retirement in core cycles: a slot remains live until S commit for
    # LOAD or until the external response for STORE.
    live, free, rows = [], [0] * profile['bank_count'], [None] * profile['bank_count']
    issue, s_free, bus_free, end = 0, 0, 0, 0
    for index in range(words):
        live = [t for t in live if t > issue]
        if len(live) >= credit:
            issue = min(live)
            live = [t for t in live if t > issue]
        if direction == 'store':
            issue = max(issue, s_free)
            s_free = issue + s_access_ticks
            accepted = s_free
        else:
            accepted = issue
        address = index * profile['word_bytes']
        bank = (address // profile['bank_interleave_bytes']) % profile['bank_count']
        row = address // profile['row_bytes']
        mem_edge = max(0, (accepted * profile['core_period'] - profile['phase'] + profile['period'] - 1) // profile['period'])
        command = max(mem_edge, free[bank])
        due = command + profile['latency'] + (profile['row_miss_cycles'] if rows[bank] != row else 0)
        free[bank], rows[bank] = command + profile['bank_issue_cycles'], row
        bus_free = max(bus_free, due) + (profile['turnaround_cycles'] if index == 0 and direction == 'store' else 1)
        response = (bus_free * profile['period'] + profile['phase'] + profile['core_period'] - 1) // profile['core_period']
        if direction == 'load':
            s_free = max(s_free, response) + s_access_ticks
            retired = s_free
        else:
            retired = response
        live.append(retired)
        end = max(end, retired)
        issue = accepted + 1  # <= one 128-bit request per core cycle
    return end


def attach_virtual_memory(graph, hardware):
    """Generate size-specific routes from one hardware input, no extra JSON.

    A site declares memory_group and measured io_read_ticks/io_write_ticks.
    Native DMA binaries, preconnected data nets and physical signoff are not
    prerequisites. Logical endpoint demands remain visible for later routing.
    """
    h = deepcopy(hardware)
    profile = h.get('virtual_memory')
    if not profile:
        return h
    extent = sorted({int(v['words']) for v in graph['values'].values()})
    for site, meta in h['sites'].items():
        channel = int(meta['memory_group']) % profile['channels']
        port = meta['io_resource']
        if port not in h['resources']:
            raise ValueError('undeclared S IO resource: ' + site)
        resource = f'virtual-memory.channel.{channel}'
        h['resources'][resource] = 1
        for direction in ('load', 'store'):
            src, dst = (h['external'], site) if direction == 'load' else (site, h['external'])
            endpoint = f'{site}.io.{direction}'
            nets = meta.get('memory_nets', {}).get(direction, [])
            for n in nets:
                if n not in h['nets']:
                    raise ValueError('missing declared endpoint demand ' + n)
            for words in extent:
                if words > meta['words']:
                    continue
                rid = f'virtual:{direction}:{site}:{words}'
                ticks = descriptor_ticks(profile, words, direction,
                    meta['io_write_ticks' if direction == 'load' else 'io_read_ticks'])
                h['routes'][rid] = {
                    'src': src, 'dst': dst, 'min_words': words, 'max_words': words,
                    'qualified': True, 'qualification_scope': 'configured_virtual_interface',
                    'protocol': 'acknowledged_copy', 'nets': list(nets),
                    'phases': [{'name': direction + '-until-commit', 'ticks': ticks,
                                'resources': [resource, port]}],
                    'logical_endpoint': endpoint, 'channel': channel,
                    'source_commit': profile['source_commit'], 'physical_signoff': False,
                }
    h['evaluation_scope'] = 'algorithm under the recorded PR182-derived virtual memory model'
    return h
