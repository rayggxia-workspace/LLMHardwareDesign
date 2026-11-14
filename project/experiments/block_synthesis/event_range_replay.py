"""Replay native range dispatches against the integer primitive semantics."""
from math import prod

import numpy as np

from full_integer import Q
from wide_program import execute


def replay_ranges(program, dispatched, initial, ids, oracle):
    nodes = {node['id']: node for node in program['instructions']}
    kernels = {}
    for node in nodes.values():
        kernels.setdefault(node['kernel'], []).append(node)
    values = {**initial, 'input_ids': np.asarray(ids, dtype=np.int64)}
    committed = {}

    def result(node, args, shape):
        names = [str(i) for i in range(len(args))]
        single = {**node, 'inputs': names, 'shape': list(shape)}
        return execute({'instructions': [single], 'predicates': program['predicates'],
                        'outputs': {'result': single['id']}},
                       dict(zip(names, args)), ids, oracle)['result']

    def raw(value):
        return value.raw if isinstance(value, Q) else np.asarray(value)

    def transform(value, fn):
        if not isinstance(value, Q):
            return fn(raw(value))
        mask = None if value.mask is None else fn(np.broadcast_to(value.mask, value.raw.shape))
        return Q(fn(value.raw), value.exponent, mask)

    def read(name, span=None):
        node = nodes.get(name)
        if node is not None and node['op'] == 'Mask':
            # Mask is an address alias, with a separate predicate address.
            q = read(node['inputs'][0], span)
            mask = program['predicates'][node['attributes']['predicate']]['raw']
            mask = np.broadcast_to(np.asarray(mask, dtype=bool), node['shape'])
            if span is not None:
                mask = mask.reshape(-1)[slice(*span)]
            return Q(q.raw, q.exponent, mask)
        if name not in values and node is not None and node['op'] in ('Constant', 'View'):
            values[name] = result(node, [read(x) for x in node['inputs']], node['shape'])
        if name not in values:
            raise ValueError(f'native dispatch reads {name} before commit')
        if name in committed:
            limit = span or (0, prod(node['shape']))
            if not committed[name][slice(*limit)].all():
                raise ValueError(f'native dispatch reads an uncommitted range of {name}')
        value = values[name]
        return value if span is None else transform(value, lambda x: x.reshape(-1)[slice(*span)])

    def pointwise_operand(name, shape, lo, hi):
        source = nodes.get(name)
        outer = tuple(shape[:-1])
        if source and tuple(source['shape'][:-1]) == outer and source['shape']:
            stride = source['shape'][-1]
            part = read(name, (lo * stride, hi * stride))
            return transform(part, lambda x: x.reshape(hi - lo, stride))
        return transform(read(name), lambda x: np.broadcast_to(x, shape).reshape(-1, shape[-1])[lo:hi])

    def write_range(node, q, span):
        name, shape = node['id'], node['shape']
        elements = prod(shape)
        if name not in values:
            mask = None if q.mask is None else np.zeros(shape, dtype=bool)
            values[name] = Q(np.empty(shape, dtype=np.int64), q.exponent, mask)
            committed[name] = np.zeros(elements, dtype=bool)
        old = values[name]
        indexes = slice(*span)
        if committed[name][indexes].any() or (old.mask is None) != (q.mask is None):
            raise ValueError(f'duplicate or inconsistent native range output {name}')
        old.raw.reshape(-1)[indexes] = q.raw.reshape(-1)
        if old.mask is not None:
            old.mask.reshape(-1)[indexes] = np.broadcast_to(q.mask, q.raw.shape).reshape(-1)
        committed[name][indexes] = True

    for task, descriptor in dispatched:
        if descriptor is None:
            for node in kernels[task]:
                if node['op'] not in ('Constant', 'View', 'Mask'):
                    values[node['id']] = result(node, [read(name) for name in node['inputs']], node['shape'])
            continue
        lo, hi = descriptor['rows']
        nrows = hi - lo
        for node in kernels[descriptor['kernel']]:
            if node['id'] not in descriptor['output_indices']:
                continue
            op, shape, names = node['op'], node['shape'], node['inputs']
            out_shape = (nrows, shape[-1])
            if op in ('Sum', 'SquareSum', 'Max', 'NFactor'):
                length = node['attributes']['length']
                args = [transform(read(names[0], (lo * length, hi * length)),
                                  lambda x: x.reshape(nrows, length))]
            elif op == 'Dot':
                length = node['attributes']['length']
                a_node = nodes.get(names[0])
                a_shape = a_node['shape'] if a_node is not None else raw(read(names[0])).shape
                inner_rows = shape[-2]
                if tuple(a_shape[:-1]) == tuple(shape[:-1]):
                    a = transform(read(names[0], (lo * length, hi * length)),
                                  lambda x: x.reshape(nrows, 1, length))
                else:
                    a = transform(read(names[0]), lambda x: np.broadcast_to(
                        x, (*shape[:-2], inner_rows, length)).reshape(-1, 1, length)[lo:hi])
                # All K for every output. RHS is whole-value synchronized.
                def rhs(x):
                    if x.ndim == 2:
                        return x
                    batches = np.broadcast_to(x, (*shape[:-2], length, shape[-1]))
                    return batches.reshape(-1, length, shape[-1])[np.arange(lo, hi) // inner_rows]
                args = [a, transform(read(names[1]), rhs)]
                out_shape = (nrows, 1, shape[-1])
            else:
                args = [pointwise_operand(name, shape, lo, hi) for name in names]
            q = result(node, args, out_shape)
            write_range(node, q, descriptor['output_indices'][node['id']])
    if any(not mask.all() for mask in committed.values()):
        raise ValueError('native range program left uncommitted scalar records')
    return {name: read(value) for name, value in program['outputs'].items()}
