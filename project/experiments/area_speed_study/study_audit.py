"""Trace-derived checks for fixed-S context experiments; no timing predictor."""
from copy import deepcopy
import math
from pathlib import Path
import sys

BASE = Path(__file__).resolve().parent.parent / 'p_dma_study'
sys.path.insert(0, str(BASE))
import audit as legacy


def expected_context(path, bits, variant, count, reuse):
    tensors, ops, _ = legacy.trace_info(path)
    expected = [dict(calls=0, groups=0, commands=0, outputs=0, a_bytes=0,
                     a_saved=0, a_groups=0, psum_peak=0) for _ in range(2)]
    if count == 1:
        return expected
    combine = 'combine' in variant
    prefix = 'prefix' in variant
    pair = 'pair' in variant
    for op in ops:
        if op['kind'] != 'Dot' or op['r'] != 1 or op['layout'] != 0:
            continue
        abyte = tensors[op['inputs'][0]][2] // 8
        bbyte = bits // 8
        workspace = 1024 + 512 * combine
        limit = min(256, ((16384 - 96 - workspace) // (2 * (abyte + 8*bbyte))) // 8 * 8)
        full_a = op['k'] * abyte
        if full_a + 96 + workspace < 16384:
            room = (16384 - full_a - 96 - workspace) // (16*bbyte)
            if room >= 8:
                limit = min(limit, room // 8 * 8)
        resident = full_a + 2*math.ceil(8*limit*bbyte/64)*64 + 96 + workspace <= 16384
        if resident:
            continue
        footprint = 2*(math.ceil(limit*abyte/64)*64 + math.ceil(8*limit*bbyte/64)*64) + 128 + workspace
        prefix_k = min(op['k'], max(0, (16384-footprint)//abyte)//limit*limit) if prefix else 0
        for worker, e in enumerate(expected):
            e['calls'] += 1  # The worker is invoked even when this P owns no columns.
            cols = ([c for g in range(worker*16, op['n'], 32)
                     for c in range(g, min(g+16, op['n']), 8)] if pair
                    else list(range(worker*8, op['n'], 16)))
            if not cols:
                continue
            groups = math.ceil(len(cols)/count)
            chunks = math.ceil(op['k']/limit)
            factor = op['batches']
            e['groups'] += groups*factor
            e['commands'] += len(cols)*chunks*factor
            e['outputs'] += len(cols)*factor
            e['a_groups'] += (groups if reuse else len(cols))*chunks*factor
            e['a_bytes'] += (prefix_k*abyte + (op['k']-prefix_k)*abyte*(groups if reuse else len(cols)))*factor
            e['a_saved'] += (op['k']-prefix_k)*abyte*(len(cols)-groups)*factor if reuse else 0
            e['psum_peak'] = max(e['psum_peak'], min(count, len(cols))*96)
    return expected


def check(row, trace, baseline, contexts, switch, reuse):
    result = legacy.check(row, trace)
    c = row['context_study']
    assert (c['contexts'], c['switch_cycles'], bool(c['reuse_A'])) == (contexts, switch, bool(reuse))
    assert len(c['P']) == 2
    for key in ('M_commands', 'M_tiles', 'M_work_ticks', 'vector_work_ticks', 'adapter_work_ticks'):
        assert row[key] == baseline[key], (key, row[key], baseline[key])
    old = legacy.check(baseline, trace)
    for flow in ('weight', 'dynamic_B', 'dot_output', 'U_read', 'U_write', 'KV_write'):
        assert result['flow_totals'][flow] == old['flow_totals'][flow], flow
    expected = expected_context(trace, 8 if 'w8' in row['profile'] else 16,
                                row['detail']['variant'], contexts, reuse)
    mappings = {'enabled_calls':'calls', 'groups':'groups', 'A_groups':'a_groups',
                'A_loaded_bytes':'a_bytes', 'A_saved_bytes':'a_saved',
                'context_switches':'commands', 'completed_contexts':'outputs',
                'psum_register_bytes_peak':'psum_peak'}
    for worker, (actor, e) in enumerate(zip(c['P'], expected)):
        assert actor['worker'] == worker
        for actual, wanted in mappings.items():
            assert actor[actual] == e[wanted], (worker, actual, actor[actual], e[wanted])
        assert actor['switch_subcycles'] == e['commands']*switch*1000
        assert actor['A_bank_peak'] <= 2 and actor['B_bank_peak'] <= 2
        assert actor['psum_register_bytes_peak'] <= contexts*96
    assert old['flow_totals']['A']['logical_read'] - result['flow_totals']['A']['logical_read'] == sum(e['a_saved'] for e in expected)
    if contexts == 1:
        observed = deepcopy(row)
        del observed['context_study']
        assert observed == baseline, 'complete legacy baseline regression'
    result.update(contexts_checked=True, expected_context=expected,
                  extra_psum_payload_bytes_per_P=max(0, contexts-1)*96,
                  metadata_area='not physically measured')
    return result


def reject_checks(row, trace, baseline, contexts, switch, reuse):
    changes = [
        ('A-load', lambda r: r['context_study']['P'][0].__setitem__('A_loaded_bytes', r['context_study']['P'][0]['A_loaded_bytes']+1)),
        ('A-bank-capacity', lambda r: r['context_study']['P'][0].__setitem__('A_bank_peak', 3)),
        ('B-bank-capacity', lambda r: r['context_study']['P'][0].__setitem__('B_bank_peak', 3)),
        ('context-switch-cost', lambda r: r['context_study']['P'][0].__setitem__('switch_subcycles', r['context_study']['P'][0]['switch_subcycles']+1000)),
        ('psum-capacity', lambda r: r['context_study']['P'][0].__setitem__('psum_register_bytes_peak', contexts*96+1)),
        ('work-conservation', lambda r: r.__setitem__('M_commands', r['M_commands']+1)),
    ]
    passed = []
    for name, change in changes:
        bad = deepcopy(row)
        change(bad)
        try:
            check(bad, trace, baseline, contexts, switch, reuse)
        except AssertionError:
            passed.append(name)
        else:
            raise AssertionError('negative accepted: '+name)
    return passed
