"""Independent shared-pool probe data and whole-K arithmetic reference.

This module deliberately does not implement the candidate's pool, FIFO, tile
schedule or context file. The probe must use actual candidate consumer events.
"""
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import random

S32_MIN, S32_MAX = -(1 << 31), (1 << 31) - 1


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def rounded(value, shift):
    return min(S32_MAX, max(S32_MIN, round(Fraction(value, 1 << shift))))


def make_case(case_id, rows, k, columns, weight_bits, capacity, fifo, contexts=8):
    rng = random.Random(247000 + case_id)
    low, high = -(1 << (weight_bits - 1)), (1 << (weight_bits - 1)) - 1
    # Mix extrema, cancellation and small terms; every row and column differs.
    a = [[rng.randrange(-1000000, 1000001) for _ in range(k)] for _ in range(rows)]
    b = [[rng.randrange(low, high + 1) for _ in range(k)] for _ in range(columns)]
    for row, values in enumerate(a):
        values[0] = S32_MIN + row
        if k > 1:
            values[-1] = S32_MAX - row
        if k > 2:
            values[k // 2] = 2 * row + 1
    for col, values in enumerate(b):
        values[0] = low if col & 1 else high
        if k > 1:
            values[-1] = high if col & 1 else low
    if k >= 8:
        a[0][:8] = [S32_MIN] * 8
        b[0][:8] = [low] * 8
    shift = weight_bits + 8
    expected = [[rounded(sum(x * y for x, y in zip(row, column)), shift)
                 for column in b] for row in a]
    return dict(id=case_id, rows=rows, k=k, columns=columns,
                weight_bits=weight_bits, capacity_bytes=capacity,
                fifo_beats=fifo, contexts=contexts, shift=shift,
                tile_k=120 if rows == 7 else 256,
                A=a, B=b, expected=expected)


def cases():
    # Exactly-full, partial-prefix and unaligned tail rows; both consumers have
    # unequal output-column ownership. Long-K cases exercise >48-bit partials.
    shapes = [
        (1, 1, 9, 8, 32768, 1),
        (2, 7, 17, 16, 32768, 4),
        (2, 255, 17, 8, 32768, 1),
        (7, 257, 17, 16, 32768, 4),
        (1, 8191, 17, 8, 32768, 4),
        (1, 8192, 17, 16, 32768, 1),
        (1, 8193, 137, 8, 32768, 4),
        (1, 11008, 137, 16, 49152, 4),
        (2, 11008, 17, 8, 32768, 1),
        (2, 11008, 17, 16, 49152, 4),
        (2, 11008, 17, 8, 98304, 4),
        (7, 2049, 17, 8, 32768, 4),
    ]
    return [make_case(i, *shape, contexts=8 if shape[0] == 1 else 1)
            for i, shape in enumerate(shapes)]


def write_input(path, values):
    """Plain integer format consumed by an independently compiled C++ probe."""
    lines = [str(len(values))]
    for item in values:
        fields = ('id', 'rows', 'k', 'columns', 'weight_bits', 'capacity_bytes',
                  'fifo_beats', 'contexts', 'shift', 'tile_k')
        lines.append(' '.join(str(item[field]) for field in fields))
        for name in ('A', 'B'):
            lines.extend(' '.join(map(str, row)) for row in item[name])
    Path(path).write_text('\n'.join(lines) + '\n', encoding='ascii')


def compare(actual, expected):
    """Fail on missing/duplicate cases and on the first differing output."""
    if len(actual) != len(expected):
        raise AssertionError('missing or duplicate numeric probe cases')
    by_id = {row['id']: row for row in actual}
    if len(by_id) != len(actual):
        raise AssertionError('duplicate numeric probe case id')
    outputs = 0
    for item in expected:
        got = by_id.get(item['id'])
        if got is None:
            raise AssertionError('missing numeric case ' + str(item['id']))
        if got['output'] != item['expected']:
            raise AssertionError('actual pool consumer output mismatch in case ' + str(item['id']))
        outputs += item['rows'] * item['columns']
    return outputs


def evidence(values):
    return [dict((key, item[key]) for key in item if key not in ('A', 'B', 'expected'))
            for item in values]
