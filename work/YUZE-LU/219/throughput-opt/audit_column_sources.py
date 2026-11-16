"""Check recovered original bytes and the current final producer source lock."""
import hashlib
import json
from pathlib import Path


def main():
    task = Path(__file__).resolve().parent
    root = task.parents[3]
    production = root / 'project/experiments/block_synthesis'
    results = task / 'results'
    originals = {}
    for receipt_file in sorted(results.glob('column-*/receipt.json')):
        receipt = json.loads(receipt_file.read_text())
        for name, record in receipt['recovered'].items():
            path = receipt_file.parent / name
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            if digest != record['sha256']:
                raise ValueError('recovered original changed: ' + str(path))
            originals[str(path.relative_to(root)).replace('\\', '/')] = digest
    source = {}
    # These attempts use the final production modules, unlike intentionally
    # retained earlier static factories and failed SystemC compile snapshots.
    for name in ('column-dynamic-numeric', 'column-systemc-phase', 'column-systemc-separate'):
        receipt = json.loads((results / name / 'receipt.json').read_text())
        for filename, expected in receipt['source_sha256'].items():
            path = production / filename
            if not path.is_file():
                raise ValueError('missing final producer source ' + filename)
            actual = hashlib.sha256(path.read_text(encoding='utf-8').encode('utf-8')).hexdigest()
            if actual != expected:
                raise ValueError('producer source drift: ' + name + '/' + filename)
            source.setdefault(filename, actual)
    output = {'passed': True, 'recovered_originals': originals, 'final_production_normalized_utf8_sha256': source,
              'scope': 'local recovered bytes and normalized final attempt producers; Git blob verification recorded at publication',
              'old_snapshots': 'static factory, earlier dynamic search, and failed SystemC attempt retained at their own hashes'}
    (results / 'column-source-verification.json').write_text(json.dumps(output, indent=2) + '\n', newline='\n')
    print(json.dumps({'passed': True, 'originals': len(originals), 'production_files': len(source)}))


if __name__ == '__main__':
    main()
