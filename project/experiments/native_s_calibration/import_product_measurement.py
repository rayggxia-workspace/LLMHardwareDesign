"""Read-only extraction of the neighboring agent's SHA-bound102172 receipt."""
import argparse
import csv
import hashlib
import json
from pathlib import Path


def extract(source):
    collection = json.loads((source / 'collection.json').read_text())
    assert collection['job'] in (102172, 102202, 102228)
    assert hashlib.sha256((source / 'receipts.tar.gz').read_bytes()).hexdigest() == collection['SHA256']
    audit = json.loads((source / 'audit.json').read_text())
    sources = {102172: 'e1e823b11a53853ca201fb3d3538c66b7f159738', 102202: '31846aad1ce538065427fcaab13c7f8f55c7f395',
               102228: '637c517873f6a3198b984b6b032b6587f250374a'}
    assert audit['passed'] and audit['source_commit'] == sources[collection['job']]
    records = []
    for path in sorted((source / 'receipts').glob('leaf-seed-*/timing-*.csv')):
        raw = path.read_bytes()
        rows = list(csv.reader(raw.decode().splitlines()))
        wanted = {'5000', '5001', '5010', '5011', '5020', '5021'}
        tickets = {row[3] for row in rows if row[0] == 'RESPONSE' and row[4] in wanted and row[2] in {'3', '4'}}
        selected = [row for row in rows if (row[0] in {'CORE_EXEC', 'CORE_INPUT', 'CORE_RF', 'S_REQ', 'TERMINAL'} and row[2] in tickets)
                    or (row[0] == 'RESPONSE' and row[3] in tickets)
                    or (row[0] == 'A' and row[2] in wanted)]
        records.append(dict(path=path.relative_to(source / 'receipts').as_posix(),
                            SHA256=hashlib.sha256(raw).hexdigest(), events=selected))
    assert len(records) == 18
    return dict(job=collection['job'], source_commit=audit['source_commit'],
                original_receipt_SHA256=collection['SHA256'],
                boundary='Product M+original guard; ideal host S provider RTT2, not actual local_s_base banks',
                records=records, audit_costs=[r['isolated_product_costs'] for r in audit['runs']])


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    result = extract(args.source)
    args.out.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(dict(passed=True, job=result['job'], traces=len(result['records']))))
