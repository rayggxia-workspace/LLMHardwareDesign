"""Receipt/byte audit only; does not run or replace RTL simulation."""
import argparse
import hashlib
import json
from pathlib import Path
import struct


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--run', type=Path, required=True)
    a = p.parse_args()
    root = a.run / 'receipts'
    files = json.loads((root / 'receipts-manifest.json').read_text())
    for name, expected in files.items():
        assert sha(root / name) == expected, name
    metadata = json.loads((root / 'vectors/manifest.json').read_text())
    assert metadata['passed'] and metadata['full_model_SHA256_checked']
    assert metadata['model_SHA256'] == '73d70c78b55123ff89d5c3b333f169934703c1fd8138ca1d4942b35b58e2d7d6'
    assert sha(root / 'vectors/records.txt') == metadata['fixture_SHA256']
    tokens = iter((root / 'vectors/records.txt').read_text().split())
    count = int(next(tokens))
    assert count == 34
    native = raw_results = payload_bytes = 0
    for entry in metadata['records']:
        head, n, rid = (int(next(tokens)) for _ in range(3))
        assert bool(head) == entry['head16'] and n == entry['n'] and rid == entry['index'] + 1
        payload = b''.join(int(next(tokens), 16).to_bytes(64, 'little') for _ in range(18 if head else 17))
        assert hashlib.sha256(payload).hexdigest() == entry['payload_SHA256']
        payload_bytes += len(payload)
        activations = [struct.unpack('<16h', int(next(tokens), 16).to_bytes(32, 'little')) for _ in range(8)]
        for tile in range(8):
            assert int(next(tokens), 16).to_bytes(128, 'little') == payload[tile * 128:(tile + 1) * 128]
        for tile in range(8):
            actual = struct.unpack('<8H', int(next(tokens), 16).to_bytes(16, 'little'))
            expected = struct.unpack_from('<8H', payload, 1024 + (tile * 16 if head else 0))
            assert actual == tuple(expected[i] if i < n else 0 for i in range(8))
        for group in range(8 if head else 1):
            actual = struct.unpack('<8i', int(next(tokens), 16).to_bytes(32, 'little'))
            tiles = [group] if head else range(8)
            expected = []
            for lane in range(8):
                total = 0
                for tile in tiles:
                    weights = struct.unpack_from('<16b', payload, tile * 128 + lane * 16)
                    total += sum(x * y for x, y in zip(activations[tile], weights))
                expected.append(total)
            assert actual == tuple(expected)
            raw_results += 1
        native += 8
    assert next(tokens, None) is None
    receipts = []
    for seed in range(25011, 25017):
        result = json.loads((root / f'seed-{seed}/result.json').read_text())
        assert result['passed'] and result['seed'] == seed
        assert result['fixture_SHA256'] == metadata['fixture_SHA256']
        lint = (root / f'seed-{seed}/production-lint.log').read_text()
        assert '%Warning' not in lint and '%Error' not in lint
        for initial in (0, 1, 2):
            receipt = (root / f'seed-{seed}/initial-{initial}.log').read_text().strip()
            assert result['runs'][initial]['initial'] == initial
            assert result['runs'][initial]['receipt'] == receipt and receipt.startswith('PASS weights ')
            receipts.append(receipt)
    source = root / 'source'
    for line in (root / 'source.sha256').read_text().splitlines():
        expected, name = line.split('  ', 1)
        assert sha(source / name) == expected
    summary = dict(passed=True, source_commit=(source / 'source-commit.txt').read_text().strip(),
                   files_checked=len(files), fixture_cases=count, payload_bytes=payload_bytes,
                   independent_native_operands=native, independent_raw_results=raw_results,
                   RTL_runs=len(receipts), initial_states=[0, 1, 2], seeds=list(range(25011, 25017)),
                   fixture_SHA256=metadata['fixture_SHA256'],
                   scope='weight records, source coordinates, byte order, bounded protocol and actual raw M; no whole-model/P&R claim')
    (a.run / 'audit.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(summary))


if __name__ == '__main__':
    main()
