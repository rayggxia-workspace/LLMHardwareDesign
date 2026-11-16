"""Register actual U/E and N services from the pinned client RTL replay.

N rows are ordered native command programs. A row service owns the N context
until all statistics/replays retire, so two independent rows cannot corrupt
one another. No FLOAT model is relabeled INT16; the source model must carry
the explicit native numeric profile.
"""
import hashlib
import re

from memory import profile_from_source


def measured_profiles(log):
    measurements, io, mode = {}, {}, 0
    for line in log.splitlines():
        m = re.search(r'PROFILE kind=service lane=(\d+) meta=(\w+) sources=(\d+) store=(\d+) ticks=(\d+)', line)
        if m:
            lane, meta, count, store, ticks = (int(m[1]), int(m[2], 16), int(m[3]), int(m[4]), int(m[5]))
            if lane == 1 and meta & 15 == 0:
                mode = (meta >> 8) & 3
            key = (lane, mode if lane == 1 else 0, meta, count, store)
            measurements.setdefault(key, set()).add(ticks)
        m = re.search(r'PROFILE kind=io direction=(read|write) ticks=(\d+)', line)
        if m:
            io.setdefault(m[1], set()).add(int(m[2]))
    if log.count('PASS U native') != 3 or set(io) != {'read', 'write'}:
        raise ValueError('missing three-initial-state qualification or endpoint IO measurement')
    if any(len(v) != 1 for v in measurements.values()) or any(len(v) != 1 for v in io.values()):
        raise ValueError('input profile is not deterministic for this driver')
    return {k: next(iter(v)) for k, v in measurements.items()}, {k: next(iter(v)) for k, v in io.items()}


def build_catalog(log, memory_source, *, sites, row_lengths=(8, 16)):
    """sites: explicit instance->capacity/group input; never a fixed nine-block layout."""
    profiles, io = measured_profiles(log)
    h = {'external': 'MEM', 'sites': {}, 'resources': {}, 'services': {}, 'routes': {}, 'nets': {},
         'virtual_memory': profile_from_source(memory_source),
         'wire_cost_unit': 'logical channel bundles; not measured bit nets or geometry',
         'evidence': {'compute': 'PR214 real U/N/E/compact-S client replay',
             'log_sha256': hashlib.sha256(log.encode()).hexdigest(),
             'source_commit': 'f5fb8115ece2e125edda6c223f0538ed52c941c6',
             'memory': 'PR182-derived virtual interface; native DMA/MC/LC replay deferred',
             'data_preconnections_required': False, 'numeric_policy': 'explicit native integer source semantics'}}
    for instance, meta in sites.items():
        site = instance + '.S'
        port, client, engine = instance + '.S.port', instance + '.client', instance + '.N'
        h['sites'][site] = {**meta, 'io_resource': port, 'io_read_ticks': io['read'], 'io_write_ticks': io['write']}
        for name in (port, client, engine, instance + '.E'):
            h['resources'][name] = 1
        for macro in ('N', 'E'):
            for direction, src, dst in [('read', site + '.operand_response', instance + '.' + macro + '.operand'),
                                         ('write', instance + '.' + macro + '.result', site + '.write_request')]:
                h['nets'][f'{instance}.{macro}.{direction}'] = {
                    'cost': 1, 'cost_unit': 'logical channel bundle', 'fixed': False,
                    'logical_driver': src, 'logical_sinks': [dst],
                    'binding_scope': 'logical endpoint demand; physical pin binding deferred'}
        for op, code, numeric in [('AddSat', 0, 's16-saturate-no-rescale'), ('MulSat', 3, 's16-multiply-saturate-shift0')]:
            h['services'][instance + '.' + op] = {
                'op': op, 'numeric': numeric, 'site': site,
                'ticks': profiles[0, 0, code, 2, 1], 'qualified': True,
                'elementwise': True, 'tile_elements': 8,
                'input_words': [1, 1], 'output_words': [1],
                'resources': [instance + '.E', port, client],
                'nets': [instance + '.E.read', instance + '.E.write'],
                'native_program': [{'lane': 0, 'meta': code, 'inputs': [0, 1], 'store': True}],
            }
        for length in sorted(set(row_lengths)):
            if length < 8 or length % 8:
                raise ValueError('this measured N profile requires full eight-lane chunks')
            chunks = length // 8
            # Whole-row loops bridge N's row representation and E's eight-lane
            # records without inventing a free scatter/gather or repacker.
            for op, code, numeric in [('AddSat', 0, 's16-saturate-no-rescale'), ('MulSat', 3, 's16-multiply-saturate-shift0')]:
                steps = [{'lane': 0, 'mode': 0, 'meta': code, 'sources': 2, 'store': 1,
                          'chunk': i, 'ticks': profiles[0, 0, code, 2, 1]} for i in range(chunks)]
                h['services'][f'{instance}.{op}.row{length}'] = {
                    'op': op, 'numeric': numeric, 'site': site, 'ticks': sum(v['ticks'] for v in steps),
                    'qualified': True, 'row_replay': True, 'row_elements': length,
                    'input_layouts': ['row', 'row'], 'input_words': [chunks, chunks], 'output_words': [chunks],
                    'resources': [instance + '.E', port, client], 'native_program': steps,
                    'nets': [instance + '.E.read', instance + '.E.write'],
                }
            def program(soft):
                steps = [{'lane': 1, 'mode': 0 if soft else 1, 'meta': 0 if soft else 0x100,
                          'sources': 0 if soft else 1, 'store': 0}]
                steps += [{'lane': 1, 'mode': 0 if soft else 1, 'meta': 0x81, 'sources': 1, 'store': 0,
                           'chunk': i} for i in range(chunks)]
                steps += [{'lane': 1, 'mode': 0 if soft else 1, 'meta': 2, 'sources': 0, 'store': 0}]
                steps += [{'lane': 1, 'mode': 0 if soft else 1, 'meta': 0x83 if soft else 0x85,
                           'sources': 1 if soft else 2, 'store': 1, 'chunk': i} for i in range(chunks)]
                if soft:
                    steps += [{'lane': 1, 'mode': 0, 'meta': 4, 'sources': 0, 'store': 0}]
                    steps += [{'lane': 1, 'mode': 0, 'meta': 0x86, 'sources': 1, 'store': 1,
                               'chunk': i} for i in range(chunks)]
                for step in steps:
                    step['ticks'] = profiles[step['lane'], step['mode'], step['meta'], step['sources'], step['store']]
                return steps
            for soft, op, numeric in [(True, 'Softmax', 'n-softmax-q6.10-to-q1.14'),
                                       (False, 'RMSNorm', 'n-rms-q6.10-gamma-q6.10')]:
                steps = program(soft)
                h['services'][f'{instance}.{op}.{length}'] = {
                    'op': op, 'numeric': numeric, 'site': site, 'ticks': sum(s['ticks'] for s in steps),
                    'qualified': True, 'row_replay': True, 'row_elements': length,
                    'input_layouts': ['row'] if soft else ['row', 'shared-row', 'scalar-word'],
                    'input_words': [chunks] if soft else [chunks, chunks, 1], 'output_words': [chunks],
                    'scratch_words': chunks if soft else 0,
                    'resources': [engine, port, client], 'native_program': steps,
                    'nets': [instance + '.N.read', instance + '.N.write'],
                    'context_lease': 'whole row; never migrate/interleave N statistics across instances',
                    'qualification_scope': 'primitive command timings composed in exact native order; row numerical replay separate',
                }
    return h
