"""Integer design check for the new F8 narrow function, not an RTL simulator."""
import argparse
import hashlib
import json
import sys
from pathlib import Path


def reference(value):
    # Independent sign/magnitude rounding, followed by explicit signed clip.
    magnitude, remainder = divmod(abs(value), 8)
    rounded = magnitude + int(remainder > 4 or (remainder == 4 and magnitude % 2))
    if value < 0:
        rounded = -rounded
    return max(-128, min(127, rounded)), rounded < -128 or rounded > 127


def rtl_expression(value):
    # Mathematical interpretation of the source's signed floor + low-bit rule.
    bits = value & 0x1ffff
    increment = int((bits & 7) > 4 or ((bits & 7) == 4 and bool(bits & 8)))
    rounded = (value >> 3) + increment
    return max(-128, min(127, rounded)), rounded < -128 or rounded > 127


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=Path(__file__).with_name('block_w4_f8_top.sv'))
    parser.add_argument('--output', type=Path, default=Path(__file__).with_name('f8-narrow-integer-checks.json'))
    args = parser.parse_args()
    literals = [(-32768, -128, True), (32767, 127, True), (-12, -2, False),
                (-4, 0, False), (4, 0, False), (12, 2, False),
                (1019, 127, False), (1020, 127, True),
                (-1028, -128, False), (-1029, -128, True)]
    for raw, expected, saturated in literals:
        assert reference(raw) == (expected, saturated)
        assert rtl_expression(raw) == (expected, saturated)
    for raw in range(-32768, 32768):
        assert reference(raw) == rtl_expression(raw), raw
    result = {
        'status': 'PASS_INTEGER_DESIGN_CHECK_NOT_RTL_EXECUTION',
        'input_parent': '0101cc7e1e6d5718455fb45b61c7428439efc09a',
        'scope': 'one signed-S16 lane RNE3 then S8 clip; all eight RTL lanes use this expression',
        'exhaustive_S16_values': 65536,
        'literal_boundaries': [{'raw': x, 'S8': y, 'saturated': s} for x, y, s in literals],
        'source': {'name': args.source.name, 'sha256': hashlib.sha256(args.source.read_bytes()).hexdigest()},
        'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'python': sys.version,
        'RTL_or_synthesis_executed': False,
        'limits': ['no proof of HDL elaboration, lane wiring or cycle behavior',
                   'no full-model numeric quality claim']
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes((json.dumps(result, ensure_ascii=False, indent=2) + '\n').encode('utf8'))
    print('PASS integer design: 65536 signed inputs and 10 literal boundaries; no RTL run')


if __name__ == '__main__':
    main()
