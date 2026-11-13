"""W-first W8 record v1. Scalar public-checkpoint coordinates are the oracle.

Run actual model/vector extraction on an allocated Slurm node. No Torch or
vectorized unpack routine is shared with the historical quality implementation.
"""
import argparse
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import struct

MODEL_ROOT = Path('/public/home/yuzelu/project-circuit/issue248-public-w8-20261110-01')
MODEL_SHA = '73d70c78b55123ff89d5c3b333f169934703c1fd8138ca1d4942b35b58e2d7d6'


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for part in iter(lambda: stream.read(8 << 20), b''):
            h.update(part)
    return h.hexdigest()


class Checkpoint:
    def __init__(self, path):
        self.file = path.open('rb')
        size = struct.unpack('<Q', self.file.read(8))[0]
        header_bytes = self.file.read(size)
        self.header_sha = hashlib.sha256(header_bytes).hexdigest()
        self.header = json.loads(header_bytes)
        self.base = 8 + size

    def at(self, name, *coordinates, bits=False):
        tensor = self.header[name]
        shape = tensor['shape']
        assert len(shape) == len(coordinates)
        index = 0
        for length, coordinate in zip(shape, coordinates):
            assert 0 <= coordinate < length
            index = index * length + coordinate
        code = {'I32': 'i', 'F16': 'H' if bits else 'e'}[tensor['dtype']]
        width = struct.calcsize('<' + code)
        self.file.seek(self.base + tensor['data_offsets'][0] + index * width)
        return struct.unpack('<' + code, self.file.read(width))[0]

    def q(self, prefix, n, k):
        group = self.at(prefix + '.g_idx', k)
        assert group == k // 128, 'activation reordering not implemented'
        packed = self.at(prefix + '.qweight', k // 4, n)
        packed_zero = self.at(prefix + '.qzeros', group, n // 4)
        value = ((packed >> (8 * (k % 4))) & 255) - (((packed_zero >> (8 * (n % 4))) & 255) + 1)
        assert -128 <= value <= 127
        return value


def valid_scale(bits):
    return bits >> 15 == 0 and ((bits >> 10) & 31) != 31 and bits & 32767 != 0


def encode(weights, scales, active_n):
    assert 1 <= active_n <= 8 and len(weights) == active_n
    assert all(len(row) == 128 for row in weights)
    assert len(scales) in (1, 8) and all(len(row) == active_n for row in scales)
    assert all(valid_scale(value) for row in scales for value in row)
    data = bytearray()
    for tile in range(8):
        for n in range(8):
            for k in range(16):
                value = weights[n][tile * 16 + k] if n < active_n else 0
                assert -128 <= value <= 127
                data.append(value & 255)
    for group in scales:
        for n in range(8):
            data.extend(struct.pack('<H', group[n] if n < active_n else 0))
    if len(scales) == 1:
        data.extend(bytes(48))
    assert len(data) == (1152 if len(scales) == 8 else 1088)
    return bytes(data)


def decode(data, head, active_n):
    assert len(data) == (1152 if head else 1088)
    weights = [[0] * 128 for _ in range(active_n)]
    for offset, value in enumerate(data[:1024]):
        tile, lane_offset = divmod(offset, 128)
        lane, k = divmod(lane_offset, 16)
        if lane < active_n:
            weights[lane][tile * 16 + k] = value if value < 128 else value - 256
        else:
            assert value == 0
    scales = []
    for group in range(8 if head else 1):
        values = list(struct.unpack('<8H', data[1024 + group * 16:1040 + group * 16]))
        assert all(valid_scale(v) for v in values[:active_n])
        scales.append(values[:active_n])
    if not head:
        assert data[1040:] == bytes(48)
    return weights, scales


def f32(value):
    return struct.unpack('<f', struct.pack('<f', value))[0]


def head_tile(checkpoint, first_n, first_k, count):
    weights = [[] for _ in range(count)]
    scales = [[] for _ in range(8)]
    for n in range(count):
        for group in range(8):
            values = [checkpoint.at('model.embed_tokens.weight', first_n + n, first_k + group * 16 + k) for k in range(16)]
            # Matches the declared historical head16 policy: FP32 division,
            # FP16 scale, FP32 division, ties-to-even integer rounding.
            scale = struct.unpack('<e', struct.pack('<e', f32(max(max(abs(v) for v in values), 1e-8) / 127)))[0]
            bits = struct.unpack('<H', struct.pack('<e', scale))[0]
            assert valid_scale(bits)
            scales[group].append(bits)
            weights[n].extend(max(-128, min(127, round(f32(value / scale)))) for value in values)
    return weights, scales


def packed_ints(values, width):
    return sum((value & ((1 << width) - 1)) << (i * width) for i, value in enumerate(values))


def signed(value, width):
    return value - (1 << width) if value & (1 << (width - 1)) else value


def export(source, out, check_model_sha):
    out.mkdir(parents=True, exist_ok=False)
    model = MODEL_ROOT / 'official-model/model.safetensors'
    fetched = json.loads((MODEL_ROOT / 'quality/closure-fetch.json').read_text())
    assert fetched['passed'] and fetched['files']['model.safetensors']['sha256'] == MODEL_SHA
    assert model.stat().st_size == fetched['files']['model.safetensors']['bytes']
    if check_model_sha:
        assert digest(model) == MODEL_SHA
    checkpoint = Checkpoint(model)
    original = source / 'project/experiments/w8a16_m/vectors/closure-m-run38.txt'
    assert digest(original) == 'e2767a3007e4dcd2249171616ec027c17067d9daac5c2af34a19404185663c83'
    lines = original.read_text().splitlines()
    assert len(lines) == 24 * 8
    cases = []
    for group_index in range(24):
        layer = [0, 2, 17, 35][group_index // 6]
        label = ['gate', 'up', 'down'][(group_index % 6) // 2]
        prefix = f'model.layers.{layer}.mlp.{label}_proj'
        full_k = checkpoint.header[prefix + '.g_idx']['shape'][0]
        kk = 0 if group_index % 2 == 0 else full_k - 128
        weights = [[checkpoint.q(prefix, n, kk + k) for k in range(128)] for n in range(8)]
        scales = [[checkpoint.at(prefix + '.scales', kk // 128, n, bits=True) for n in range(8)]]
        activations = []
        for tile, line in enumerate(lines[group_index * 8:group_index * 8 + 8]):
            fields = line.split()
            a_bits, w_bits = int(fields[6], 16), int(fields[7], 16)
            a = [signed((a_bits >> (k * 16)) & 65535, 16) for k in range(16)]
            for n in range(8):
                for k in range(16):
                    assert signed((w_bits >> ((n * 16 + k) * 8)) & 255, 8) == weights[n][tile * 16 + k]
            activations.extend(a)
        cases.append(dict(head=False, n=8, weights=weights, scales=scales, a=activations,
                          source=prefix, first_n=0, first_k=kk, qualification='actual run38 A16; Down uses historical Mid64 input'))
    for first_n, first_k in ((0, 0), (0, 1920), (151928, 0), (151928, 1920)):
        weights, scales = head_tile(checkpoint, first_n, first_k, 8)
        a = [((i * 977 + first_n + first_k) % 32768) - 16384 for i in range(128)]
        cases.append(dict(head=True, n=8, weights=weights, scales=scales, a=a,
                          source='model.embed_tokens.weight', first_n=first_n, first_k=first_k,
                          qualification='declared symmetric head16 derivation; directed A, not a model activation witness'))
    # Real checkpoint-derived N tails, with zero W/scale padding.
    for count in (1, 2, 7):
        case = cases[count].copy()
        case.update(n=count, weights=case['weights'][:count], scales=[case['scales'][0][:count]])
        cases.append(case)
        weights, scales = head_tile(checkpoint, 151928, 1920, count)
        cases.append(dict(head=True, n=count, weights=weights, scales=scales, a=cases[0]['a'],
                          source='model.embed_tokens.weight', first_n=151928, first_k=1920,
                          qualification='actual head weights with N-tail and actual ordinary-group A test vector'))
    manifest = []
    fixture = [str(len(cases))]
    for index, case in enumerate(cases):
        data = encode(case['weights'], case['scales'], case['n'])
        assert decode(data, case['head'], case['n']) == (case['weights'], case['scales'])
        fixture.append(f"{int(case['head'])} {case['n']} {index + 1}")
        fixture.extend(f"{int.from_bytes(data[beat:beat + 64], 'little'):0128x}" for beat in range(0, len(data), 64))
        for tile in range(8):
            fixture.append(f"{packed_ints(case['a'][tile * 16:tile * 16 + 16], 16):064x}")
        for tile in range(8):
            fixture.append(f"{packed_ints([case['weights'][n][tile * 16 + k] if n < case['n'] else 0 for n in range(8) for k in range(16)], 8):0256x}")
        for tile in range(8):
            values = case['scales'][tile if case['head'] else 0] + [0] * (8 - case['n'])
            fixture.append(f"{packed_ints(values, 16):032x}")
        for group in range(8 if case['head'] else 1):
            lo, hi = (group * 16, (group + 1) * 16) if case['head'] else (0, 128)
            dots = [sum(case['a'][k] * case['weights'][n][k] for k in range(lo, hi)) if n < case['n'] else 0 for n in range(8)]
            assert all(-(1 << 31) <= value < 1 << 31 for value in dots)
            fixture.append(f"{packed_ints(dots, 32):064x}")
        manifest.append(dict(index=index, head16=case['head'], n=case['n'], source=case['source'],
                             first_n=case['first_n'], first_k=case['first_k'],
                             payload_bytes=len(data), payload_SHA256=hashlib.sha256(data).hexdigest(),
                             qualification=case['qualification']))
    (out / 'records.txt').write_bytes(('\n'.join(fixture) + '\n').encode())
    report = dict(passed=True, model=fetched['model'], revision=fetched['revision'], model_SHA256=MODEL_SHA,
                  full_model_SHA256_checked=check_model_sha, tensor_header_SHA256=checkpoint.header_sha,
                  source_raw_vector_SHA256=digest(original), records=manifest,
                  cases=len(cases), fixture_SHA256=digest(out / 'records.txt'),
                  layout='W[kk16][n][k16], little endian signedW8; FP16[group][n] little endian; ordinary48B zero pad')
    (out / 'manifest.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--check-model-sha', action='store_true')
    args = parser.parse_args()
    result = export(args.source, args.out, args.check_model_sha)
    print(json.dumps(dict(passed=True, cases=result['cases'], fixture_SHA256=result['fixture_SHA256'])))
