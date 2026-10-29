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
    accepted_m = None
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
            if kind == 'm':
                accepted_m = delivery
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
            if kind == 's':
                assert accepted_m is not None, 'S final simulation must bind to the independently accepted M'
                assert reports['function']['peer_source_receipt_sha256'] == accepted_m['source_receipt_sha256']
                peer_inputs = reports['function']['peer_full_final_netlist']['input_sha256']
                assert len(peer_inputs) == 2
                assert set(peer_inputs.values()) == {accepted_m['final_files']['6_final.v']['sha256'], accepted_m['final_files']['6_final.odb']['sha256']}
                observer = json.loads(z.read('evidence/function/memory-observer.json'))
                assert observer == reports['function']['memory_observer']
                assert observer['passed'] and observer['memory_transaction_assertions_retained']
                assert not observer['physical_netlist_modified']
                assert sha(z.read('evidence/function/physical-pair.sv')) == observer['generated_fixture_sha256']
                assert sha(z.read('evidence/function/physical-test-pair.cpp')) == observer['generated_bench_sha256']
                assert reports['function']['compiled_bench_sha256'] == observer['generated_bench_sha256']
                assert reports['function']['bench_sha256'] == observer['original_bench_sha256']
                assert observer['storage_rtl_sha256'] == source['rtl_sha256']['project/rtl/block_feed_v1/block_feed_s16k.sv']
                assert len(observer['exhaustive_legal_boolean_rows']) == 10
                assert len({tuple(row[:4]) for row in observer['exhaustive_legal_boolean_rows']}) == 10
                for reset, valid, take, fire, ready, seen in observer['exhaustive_legal_boolean_rows']:
                    assert reset or not valid or take
                    assert ready == int(not reset and (not valid or take) and not fire)
                    assert seen == fire == int(not reset and (not valid or take) and not ready)
            assert reports['formal']['strict_native_lec']['passed']
            assert all(reports['formal']['strict_native_lec']['checks'].values())
            assert reports['formal']['function_receipt_sha256'] == delivery['gate_receipts']['function']['sha256']
            # Bind physical inputs to the exact already-archived tested RTL;
            # Git's checkout newline normalization is not an evidence rewrite.
            binding = json.loads((base.parent / 'source-binding.json').read_text())
            for name, digest in source['rtl_sha256'].items():
                assert any(r['path'] == name and r['sha256'] == digest for r in binding['source_hashes'])
        if 'geometry' in index:
            geometry = index['geometry']
            archive = base / geometry['archive']
            assert sha(archive.read_bytes()) == geometry['archive_sha256']
            with zipfile.ZipFile(archive) as z:
                assert len(z.namelist()) == len(set(z.namelist()))
                assert set(z.namelist()) == set(geometry['members'])
                for name, digest in geometry['members'].items():
                    assert sha(z.read(name)) == digest
                receipt = json.loads(z.read('receipt.json'))
                assert receipt['passed']
                for name in z.namelist():
                    if name != 'receipt.json':
                        assert sha(z.read(name)) == receipt['outputs'][name]
                report = json.loads(z.read('five-macro-geometry.json'))
                assert report['passed'] and report['macro'] == delivery['macro']
                assert report['original_odb_unchanged'] and report['native_def_rect_complete']
                assert report['provenance']['delivery_receipt_sha256'] == bundle['delivery_receipt_sha256']
                assert report['source_odb_sha256'] == delivery['final_files']['6_final.odb']['sha256']
                assert sha(z.read('candidate.lef')) == report['files']['candidate.lef']['sha256']
                assert all(json.loads(z.read('m10-access.json'))['negative_controls'].values())
        verified.append(kind.upper())
    return verified


if __name__ == '__main__':
    result = verify(Path(__file__).resolve().parents[3])
    print('PASS: stored native acceptance receipts: ' + (', '.join(result) or 'none') + '; EDA not rerun')
