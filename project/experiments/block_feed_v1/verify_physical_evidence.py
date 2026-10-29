"""Verify stored exact acceptance receipts, without claiming an EDA rerun."""
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import zipfile


def sha(data):
    return hashlib.sha256(data).hexdigest()


def verify(root):
    base = root / 'work/YUZE-LU/130/validation/physical'
    verified = []
    for kind in ('m', 's'):
        path = base / ('accepted-' + kind + '-index.json')
        if not path.exists():
            continue
        index = json.loads(path.read_text())
        archive = base / index['receipt_archive']
        assert sha(archive.read_bytes()) == index['receipt_archive_sha256']
        with zipfile.ZipFile(archive) as z:
            assert len(z.namelist()) == len(set(z.namelist()))
            assert set(z.namelist()) == set(index['members'])
            for name, digest in index['members'].items():
                assert sha(z.read(name)) == digest
            delivery = json.loads(z.read('native/delivery.json'))
            bundle = json.loads(z.read('meta/bundle.json'))
            received = json.loads(z.read('meta/received.json'))
            source = json.loads(z.read('meta/final-source.json'))
            source_receipt = json.loads(z.read('meta/source-receipt.json'))
            assert source_receipt['passed'] and source['passed'] and source['pipeline_completed']
            assert sha(z.read('meta/final-source.json')) == source_receipt['outputs']['final-source.json']
            assert sha(z.read('meta/source-receipt.json')) == delivery['source_receipt_sha256']
            assert delivery['passed'] and delivery['native_leaf_accepted'] and delivery['macro'] == kind.upper()
            assert bundle['passed'] and received['passed'] and received['native_leaf_accepted']
            assert bundle['archive'] == index['server_bundle']
            assert received['archive_sha256'] == bundle['archive']['sha256']
            assert sha(z.read('native/receipt.json')) == bundle['delivery_receipt_sha256']
            assert sha(z.read('native/delivery.json')) == json.loads(z.read('native/receipt.json'))['outputs']['delivery.json']
            assert {k: v['sha256'] for k, v in delivery['final_files'].items()} == received['final_files']
            assert set(received['final_files']) == {'6_final.' + s for s in ('v', 'sdc', 'odb', 'def', 'spef', 'gds')}
            for name, row in bundle['members'].items():
                if name in index['members']:
                    assert sha(z.read(name)) == row['sha256']
            reports = {}
            for op, row in delivery['gate_receipts'].items():
                receipt_name = 'evidence/' + op + '/receipt.json'
                report_name = 'evidence/' + op + '/' + Path(row['report_path']).name
                receipt = json.loads(z.read(receipt_name))
                assert receipt['passed'] and sha(z.read(receipt_name)) == row['sha256']
                assert sha(z.read(report_name)) == row['report_sha256'] == receipt['outputs'][Path(report_name).name]
                report = json.loads(z.read(report_name))
                assert report['passed'] and report['source_receipt_sha256'] == delivery['source_receipt_sha256']
                reports[op] = report
            assert set(reports) == {'physical', 'drc', 'function', 'formal'}
            assert all(reports['physical']['checks'].values())
            assert reports['drc']['full_deck']['total_items'] == 0
            assert not z.read('evidence/drc/native-whole-drc.rpt')
            assert not ET.fromstring(z.read('evidence/drc/full-deck.lyrdb')).findall('.//items/item')
            assert len(reports['function']['initial_runs']) == 3
            assert all(v['result']['passed'] for v in reports['function']['initial_runs'].values())
            assert reports['formal']['strict_native_lec']['passed']
            assert all(reports['formal']['strict_native_lec']['checks'].values())
            assert reports['formal']['function_receipt_sha256'] == delivery['gate_receipts']['function']['sha256']
            # Bind physical inputs to the exact already-archived tested RTL;
            # Git's checkout newline normalization is not an evidence rewrite.
            binding = json.loads((base.parent / 'source-binding.json').read_text())
            for name, digest in source['rtl_sha256'].items():
                assert any(r['path'] == name and r['sha256'] == digest for r in binding['source_hashes'])
        verified.append(kind.upper())
    return verified


if __name__ == '__main__':
    result = verify(Path(__file__).resolve().parents[3])
    print('PASS: stored native acceptance receipts: ' + (', '.join(result) or 'none') + '; EDA not rerun')
