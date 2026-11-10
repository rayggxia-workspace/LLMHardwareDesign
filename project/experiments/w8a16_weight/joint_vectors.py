"""Exact-Fraction scaled state expectations for the native M unit fixture."""
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import struct
import sys


def fp(bits):
    exponent, mantissa = (bits >> 10) & 31, bits & 1023
    assert not bits >> 15 and exponent != 31 and bits & 32767
    if exponent:
        mantissa += 1024
    shift = exponent - 25 if exponent else -24
    return Fraction(mantissa * (1 << max(shift, 0)), 1 << max(-shift, 0))


def pack(values):
    return ''.join(f'{v & 0xffffffff:08x}' for v in reversed(values))


def main():
    root = Path(sys.argv[1])
    tokens = iter((root / 'records.txt').read_text().split())
    count = int(next(tokens))
    output, records = [str(count)], []
    for index in range(count):
        head, n, rid = (int(next(tokens)) for _ in range(3))
        for _ in range(18 if head else 17):
            next(tokens)
        for _ in range(16):
            next(tokens)  # native A and W are checked separately
        scales = [struct.unpack('<8H', int(next(tokens), 16).to_bytes(16, 'little')) for _ in range(8)]
        dots = [struct.unpack('<8i', int(next(tokens), 16).to_bytes(32, 'little')) for _ in range(8 if head else 1)]
        shifts = [3 + g for g in range(8)] if head else [8] * 8
        terms = [[round(Fraction(value) * fp(scales[g][lane]) * (1 << shifts[g])) if lane < n else 0
                  for lane, value in enumerate(dot)] for g, dot in enumerate(dots)]
        prefixes, state = [], [0] * 8
        for term in terms:
            state = [x + y for x, y in zip(state, term)]
            assert all(-(1 << 31) <= v < 1 << 31 for v in state)
            prefixes.append(state[:])
        bias = [lane * 3 - 7 if lane < n else 0 for lane in range(8)]
        final = [x + y for x, y in zip(state, bias)]
        output += [f'{rid} {sum(shift << (6 * g) for g, shift in enumerate(shifts)):012x}', pack(bias)]
        output += [pack(value) for value in prefixes]
        output += [pack(final)]
        records.append(dict(rid=rid, head16=bool(head), n=n, shifts=shifts, prefix=prefixes, final=final))
    assert next(tokens, None) is None
    for first, second in [(0, 1), (24, 25)]:
        # Explicit unit concatenation of first/last source slices, not an
        # assertion that those two K128 windows are adjacent in the model.
        combined = [x + y for x, y in zip(records[first]['prefix'][-1], records[second]['final'])]
        output.append(pack(combined))
    path = root / 'joint.txt'
    path.write_text('\n'.join(output) + '\n')
    (root / 'joint-manifest.json').write_text(json.dumps(dict(passed=True, cases=count,
        SHA256=hashlib.sha256(path.read_bytes()).hexdigest(), records=records,
        qualification='actual source A16/W8/FP16 scales with directed declared A shifts and bias; cross-record cases concatenate named nonadjacent source K slices; not whole-model numeric qualification'), indent=2) + '\n')


if __name__ == '__main__':
    main()
