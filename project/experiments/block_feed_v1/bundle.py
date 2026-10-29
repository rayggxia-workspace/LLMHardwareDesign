"""Package an accepted native leaf without changing any qualified file.

Large binaries stay on the authorized project storage; the small index can be
committed and used to verify a downloaded archive byte for byte.
"""
import argparse
import json
from pathlib import Path
import tarfile

from deliver import accepted
from io_slots import file_sha as sha


def bundle(delivery, out):
    delivery = delivery.resolve()
    out = out.resolve()
    assert any(p.name.startswith('issue130-') for p in out.parents)
    index = accepted(delivery)
    for key in ('pins', 'image'):
        assert sha(index[key]['path']) == index[key]['sha256']
    out.mkdir(parents=True, exist_ok=False)
    members = {}

    def add(path, name):
        path = Path(path)
        assert path.is_file() and name not in members
        members[name] = dict(path=str(path), sha256=sha(path), bytes=path.stat().st_size)

    for name, row in index['final_files'].items():
        add(row['path'], 'native/' + name)
    for name in ('receipt.json', 'delivery.json', 'pins.json', 'layout.png'):
        add(delivery / name, 'native/' + name)
    for operation, row in index['gate_receipts'].items():
        receipt = Path(row['path'])
        add(receipt, 'evidence/' + operation + '/receipt.json')
        report = Path(row['report_path'])
        add(report, 'evidence/' + operation + '/' + report.name)
        # Preserve human-readable results as well as the digest-bound indexes.
        names = {
            'physical': ('timing-summary.tsv', 'timing.rpt', 'electrical-violations.rpt',
                         'electrical-worst.rpt', 'physical-pins.tsv', 'physical-summary.tsv',
                         'constraints-readback.sdc', 'annotation.rpt'),
            'drc': ('native-whole-drc.rpt', 'full-deck.lyrdb', 'full-deck.log'),
            'function': ('all-ones.log', 'random-130.log', 'random-131.log'),
        }.get(operation, ())
        for name in names:
            add(receipt.parent / name, 'evidence/' + operation + '/' + name)
        if operation == 'function' and index['macro'] == 'S':
            for name in ('memory-observer.json', 'physical-pair.sv', 'physical-test-pair.cpp'):
                assert sha(receipt.parent / name) == json.loads(receipt.read_text())['outputs'][name]
                add(receipt.parent / name, 'evidence/function/' + name)

    archive = out / ('block-feed-' + index['macro'].lower() + '-native.tar.gz')
    with tarfile.open(archive, 'w:gz', compresslevel=3) as stream:
        for name, row in sorted(members.items()):
            path = Path(row['path'])
            assert sha(path) == row['sha256']
            stream.add(path, arcname=name, recursive=False)
            assert sha(path) == row['sha256']
    accepted(delivery)
    result = dict(passed=True, macro=index['macro'], native_leaf_accepted=True,
                  delivery=str(delivery), delivery_receipt_sha256=sha(delivery / 'receipt.json'),
                  archive=dict(path=str(archive), sha256=sha(archive), bytes=archive.stat().st_size),
                  members=members, source_code=sha(Path(__file__)),
                  scope='Byte-preserved qualified native M1-M10 leaf and exact gate evidence; '
                        'not hierarchical Liberty or M11/M12 system qualification.')
    (out / 'bundle.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(dict(passed=True, macro=index['macro'], archive=result['archive'])))


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--delivery', required=True, type=Path)
    p.add_argument('--out', required=True, type=Path)
    a = p.parse_args()
    bundle(a.delivery, a.out)
