"""Product K128 runtime-shift oracle; head shares A shift, not W scales."""
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import struct
import sys
from joint_vectors import fp, pack


def main():
    root = Path(sys.argv[1])
    tokens = iter((root / 'records.txt').read_text().split())
    count = int(next(tokens))
    output, records = [str(count)], []
    for _ in range(count):
        head, n, rid = (int(next(tokens)) for _ in range(3))
        for _ in range((18 if head else 17) + 16):
            next(tokens)
        scales = [struct.unpack('<8H', int(next(tokens), 16).to_bytes(16, 'little')) for _ in range(8)]
        dots = [struct.unpack('<8i', int(next(tokens), 16).to_bytes(32, 'little')) for _ in range(8 if head else 1)]
        state, prefixes = [0] * 8, []
        for group, dot in enumerate(dots):
            state = [state[lane] + (round(Fraction(value) * fp(scales[group][lane]) * 256) if lane < n else 0)
                     for lane, value in enumerate(dot)]
            assert all(-(1 << 31) <= value < 1 << 31 for value in state)
            prefixes.append(state[:])
        bias = [lane * 3 - 7 if lane < n else 0 for lane in range(8)]
        final = [x + y for x, y in zip(state, bias)]
        output += [str(rid), pack(bias)] + [pack(value) for value in prefixes] + [pack(final)]
        records.append(dict(record=rid, runtime_A_shift=8, prefixes=prefixes, final=final))
    assert next(tokens, None) is None
    for first, second in [(0, 1), (24, 25)]:
        output.append(pack([x + y for x, y in zip(records[first]['prefixes'][-1], records[second]['final'])]))
    path = root / 'leaf.txt'
    path.write_text('\n'.join(output) + '\n')
    (root / 'leaf-manifest.json').write_text(json.dumps(dict(passed=True, cases=count,
        SHA256=hashlib.sha256(path.read_bytes()).hexdigest(), records=records,
        qualification='actual A16/W8/W-scale fixture with explicitly directed runtime A shift=8; real normalizer metadata/whole-model accuracy remains separate'), indent=2) + '\n')


if __name__ == '__main__':
    main()
