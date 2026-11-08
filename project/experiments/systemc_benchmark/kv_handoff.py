"""Strict integer KV handoff between emitted programs, with no HF replacement.

Requires a fixed state format across the trace. A scale change needs an
explicitly lowered Convert service, not a reinterpretation here. Array copying
is host ownership only, never charged or advertised as a device DMA operation.
"""
import hashlib

import numpy as np


def handoff(outputs, program, layers):
    from full_integer import Q
    if type(layers) is not int or layers < 1:
        raise ValueError('positive layer count required')
    expected = {'past_%d_%s' % (i, k) for i in range(layers) for k in ('k', 'v')}
    formats = program.get('runtime_formats', {})
    if set(formats) != expected:
        raise ValueError('incomplete or extra live KV input contracts')
    states, audit = {}, []
    for name in sorted(expected):
        source = name.replace('past_', 'next_', 1)
        q, meta = outputs.get(source), formats[name]
        if not isinstance(q, Q):
            raise ValueError('missing integer-generated KV: ' + source)
        if q.mask is not None:
            raise ValueError('KV cannot inherit an attention validity predicate')
        declared = program.get('initial_formats', {}).get(name, {})
        if not declared.get('runtime') or any(declared.get(k) != meta.get(k)
                                              for k in ('shape', 'bits', 'exponent')):
            raise ValueError('KV is not a consistent runtime program input')
        if meta['bits'] != 32 or q.exponent != meta['exponent']:
            raise ValueError('KV format change requires an explicit Convert service')
        data = np.asarray(q.raw)
        if data.shape != tuple(meta['shape']) or data.dtype.kind != 'i':
            raise ValueError('KV length/layout/type changed at handoff')
        if data.ndim != 4 or data.shape[0] != 1 or min(data.shape) < 1:
            raise ValueError('first sequence backend requires nonempty B1 KV')
        if int(data.min()) < -(1 << 31) or int(data.max()) >= (1 << 31):
            raise ValueError('KV escaped its signed S32 program format')
        # Canonical hashing is independent of the host oracle's int64 storage.
        owned = data.astype('<i4', copy=True)
        states[name] = Q(owned, q.exponent)
        audit.append({'source': source, 'input': name, 'shape': list(data.shape),
                      'exponent': q.exponent, 'logical_elements': int(data.size),
                      'canonical_s32_sha256': hashlib.sha256(owned.tobytes()).hexdigest()})
    lengths = {s.raw.shape[2] for s in states.values()}
    if len(lengths) != 1:
        raise ValueError('layers disagree on KV length')
    return states, {'origin': 'previous emitted integer program outputs',
                    'prefix_tokens': lengths.pop(), 'state_count': len(states),
                    'state': audit, 'physical_movement_inferred': False}
