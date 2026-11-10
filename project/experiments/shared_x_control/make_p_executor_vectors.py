"""Compute-node-only actual payload oracle for local-contiguous P ranges.

Shared A is deliberately rebuilt. The old fixture's precomputed dots/results
are consumed for parsing only, never reused as the expected numeric answer.
"""
import argparse
import importlib.util
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import struct
import zlib


def fp(h):
    sign = -1 if h & 0x8000 else 1
    exp, mant = (h >> 10) & 31, h & 1023
    assert exp != 31
    return sign * (Fraction(mant, 1 << 24) if exp == 0 else Fraction(1024 + mant, 1024) * Fraction(2) ** (exp - 15))


def packed(values, fmt):
    return struct.pack('<' + fmt * len(values), *values).hex()


def mem(path, values, size):
    path.write_text(''.join(f'{int.from_bytes(value, "little"):0{size * 2}x}\n' for value in values))


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--records', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--mc-assembler', type=Path)
    a = p.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    raw = a.records.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == '5abf48c82a4ad5efa4f4473bf64f5604519f1059546a7067fd39c2a684cd27d1'
    tokens = iter(raw.decode().split())
    assert int(next(tokens)) == 34
    records = []
    for _ in range(34):
        head, n, rid = [int(next(tokens)) for _ in range(3)]
        payload = [int(next(tokens), 16).to_bytes(64, 'little') for _ in range(18 if head else 17)]
        for _ in range(24 + (8 if head else 1)):
            next(tokens)
        records.append((head, n, rid, b''.join(payload)))
    assert next(tokens, None) is None
    scopes, inputs, dd, expected, manifest = [], [], [], [], []
    for head in (0, 1):
        for full_k in (128, 256):
            for groups in (1, 2):
                cid = len(scopes)
                values = [((i * 13 + cid * 7) % 251) - 125 for i in range(full_k)]
                inwords = [struct.pack('<8h', *values[i:i + 8]) for i in range(0, full_k, 8)]
                inputs += inwords + [bytes(16)] * (32 - len(inwords))
                base = 0x100000 + cid * 0x10000
                descriptor = bytearray(128)
                struct.pack_into('<IHHII', descriptor, 0, 0x02505001, 128, 1, 0x02504d02, 25001)
                struct.pack_into('<IIII', descriptor, 16, 1, 9 + cid, 8, 7)
                struct.pack_into('<IIII', descriptor, 32, 1000 + cid * 32, 2000 + cid * 32, 1, 100 + cid * 16)
                struct.pack_into('<QQIIHBBHHHBBHHHHH', descriptor, 48,
                                 base, 0, groups * 8, 0, 8, groups, 0, full_k, 0, full_k, 1, head, 0, 128, 160, 200, 240)
                struct.pack_into('<I', descriptor, 124, zlib.crc32(descriptor[:124]))
                scopes.append(bytes(descriptor))
                payloads, answers = [], []
                for group in range(groups):
                    state = [0] * 8
                    for kk in range(full_k // 128):
                        source = records[(24 if head else 0) + group * 2 + kk]
                        assert source[0] == head and source[1] == 8
                        payload = source[3]
                        payloads.append(payload)
                        dots = [[0] * 8 for _ in range(8 if head else 1)]
                        for tile in range(8):
                            for lane in range(8):
                                for q in range(16):
                                    w = struct.unpack_from('<b', payload, tile * 128 + lane * 16 + q)[0]
                                    dots[tile if head else 0][lane] += values[kk * 128 + tile * 16 + q] * w
                        for gi, dot in enumerate(dots):
                            scales = struct.unpack_from('<8H', payload, 1024 + (gi * 16 if head else 0))
                            state = [x + round(Fraction(d) * fp(s) * 256) for x, d, s in zip(state, dot, scales)]
                            assert all(-(1 << 31) <= x < 1 << 31 for x in state)
                    answers.append(state)
                    expected += [struct.pack('<4i', *state[:4]), struct.pack('<4i', *state[4:])]
                expected += [bytes(16)] * (4 - groups * 2)
                data = b''.join(payloads)
                assert len(data) <= 128 * 64
                data += bytes(128 * 64 - len(data))
                dd += [data[i:i + 64] for i in range(0, len(data), 64)]
                manifest.append(dict(case=cid, head=bool(head), full_k=full_k, groups=groups,
                                     source_records=[records[(24 if head else 0) + g * 2 + k][2] for g in range(groups) for k in range(full_k // 128)],
                                     zero_bias=True, runtime_shift=8, answers=answers))
    mem(a.out / 'scopes.mem', scopes, 128)
    mem(a.out / 'A.mem', inputs, 16)
    mem(a.out / 'DDR.mem', dd, 64)
    mem(a.out / 'expected.mem', expected, 16)
    invalid = []
    for full_k, begin in [(384, 0), (256, 128)]:
        data = bytearray(scopes[2])
        struct.pack_into('<HHH', data, 76, full_k, begin, full_k)
        struct.pack_into('<I', data, 124, zlib.crc32(data[:124]))
        invalid.append(bytes(data))
    mem(a.out / 'invalid-native.mem', invalid, 128)
    program_manifest = {}
    if a.mc_assembler:
        from make_lc_kernel import kernel
        image = kernel()
        mem(a.out / 'kernel.mem', [image[i:i + 16] for i in range(0, len(image), 16)], 16)
        spec = importlib.util.spec_from_file_location('mc_image', a.mc_assembler)
        mc = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mc)
        args = [0x4000, 0, 0x00010080, 0x02510001, 25001, 0x02500002, 0, 0]
        program = [('MOVI', r, 0, 0, v) for r, v in enumerate(args)]
        for ci in range(8):
            program += [('MOVI', 0, 0, 0, 0x4000 + ci * 128), mc.call(0), mc.wait(1)]
        program.append(mc.END)
        mother = bytearray(mc.image(program))
        struct.pack_into('<I', mother, 64, 25001)
        mem(a.out / 'mother.mem', [mother[i:i + 16] for i in range(0, len(mother), 16)], 16)
        program_manifest = dict(kernel_crc=f'{zlib.crc32(image):08x}', mother_bytes=len(mother),
                                mother_words=len(mother) // 16, mother_instructions=len(program))
    (a.out / 'manifest.json').write_text(json.dumps(dict(schema='P-real-serialized-range-numeric/1',
        public_records_sha256=hashlib.sha256(raw).hexdigest(), cases=manifest,
        **program_manifest,
        admission='LOCAL_CONTIG_RANGE preloaded A16, explicit committed shift8; not lazy quantization, dynamic Attention, whole model, energy, performance or physical qualification'), indent=2) + '\n')


if __name__ == '__main__':
    main()
