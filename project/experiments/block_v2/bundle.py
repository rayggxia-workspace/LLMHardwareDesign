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
    assert any(p.name.startswith('issue143-') for p in out.parents)
    index = accepted(delivery)
    for key in ('pins', 'image'):
        assert sha(index[key]['path']) == index[key]['sha256']
    out.mkdir(parents=True, exist_ok=False)
    members = {}

    def add(path, name):
        path = Path(path)
        assert path.is_file() and name not in members
        members[name] = dict(path=str(path), sha256=sha(path), bytes=path.stat().st_size)

    # A local recipient needs the exact source binding, not only server paths.
    from qualify import ROOT, source
    physical_receipt = Path(index['gate_receipts']['physical']['path'])
    sealed = Path(json.loads(physical_receipt.read_text())['source'])
    _, _, flow, _ = source(sealed)
    assert sha(sealed / 'receipt.json') == index['source_receipt_sha256']
    for name in ('receipt.json', 'final-source.json', 'config.mk', 'pins.json',
                 'pins.tcl', 'input.sdc'):
        add(sealed / name, 'meta/source/' + name)
    if flow.get('completed_final_native_admission'):
        for name in ('admission-diagnostic.json','admission-native-complete-proof.json','original-flow-final.sdc'):
            add(sealed/name,'meta/source/'+name)
    if flow.get('targeted_r_closure'):
        sealed_receipt=json.loads((sealed/'receipt.json').read_text())
        for name,digest in sealed_receipt['outputs'].items():
            if name.startswith(('r-targeted-','issue143-targeted-','r-measured-','r-hold-','r-electrical-','r-input-','issue143-measured-','issue143-input-')):
                assert '/' not in name and sha(sealed/name)==digest
                add(sealed/name,'meta/source/'+name)
    for relative, digest in flow['rtl_sha256'].items():
        assert sha(ROOT / relative) == digest
        add(ROOT / relative, 'meta/rtl/' + relative)

    for name, row in index['final_files'].items():
        add(row['path'], 'native/' + name)
    for name in ('receipt.json', 'delivery.json', 'pins.json', 'layout.png'):
        add(delivery / name, 'native/' + name)
    if 'postroute_repair_proof' in index:
        p=index['postroute_repair_proof'];assert sha(p['path'])==p['sha256']
        add(p['path'],'evidence/physical/route-repair-proof.json')
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
            'function': ('all-ones.log', 'random-143.log', 'random-144.log'),
            'formal': ('kepler.log','formal.log'),
        }.get(operation, ())
        for name in names:
            add(receipt.parent / name, 'evidence/' + operation + '/' + name)
        if operation == 'function' and index['macro'] == 'S':
            for name in ('memory-observer.json', 'physical-pair.sv', 'physical-test-pair.cpp'):
                assert sha(receipt.parent / name) == json.loads(receipt.read_text())['outputs'][name]
                add(receipt.parent / name, 'evidence/function/' + name)
            if (receipt.parent/'build-reuse-receipt.json').exists():
                for name in ('build-reuse-receipt.json','build-reuse-function.json'):
                    assert sha(receipt.parent/name) == json.loads(receipt.read_text())['outputs'][name]
                    add(receipt.parent/name,'evidence/function/'+name)
        if operation == 'formal' and (receipt.parent/'computation-receipt.json').exists():
            for name in ('computation-receipt.json','before-logic-proof.json','after-logic-proof.json'):
                assert sha(receipt.parent/name) == json.loads(receipt.read_text())['outputs'][name]
                add(receipt.parent/name,'evidence/formal/'+name)
            if (receipt.parent/'formal-computation.json').exists():add(receipt.parent/'formal-computation.json','evidence/formal/formal-computation.json')
        if operation=='function' and (receipt.parent/'function-computation-receipt.json').exists():
            for name in ('function-computation-receipt.json','function-computation.json','original-physical-functional-proof.json'):
                assert sha(receipt.parent/name)==json.loads(receipt.read_text())['outputs'][name]
                add(receipt.parent/name,'evidence/function/'+name)
        if operation == 'drc' and (receipt.parent/'drc-computation-receipt.json').exists():
            for name in ('drc-computation-receipt.json','drc-computation.json'):
                assert sha(receipt.parent/name) == json.loads(receipt.read_text())['outputs'][name]
                add(receipt.parent/name,'evidence/drc/'+name)
        if operation=='drc' and (receipt.parent/'native-computation.json').exists():
            for name in ('native-computation.json','gds-computation.json','gds-identity.json',
                         'native-fragmented-drc.rpt','native-complete-proof.json',
                         'native-fragmented.log','native-complete.log','native-fragmented.tcl','native-complete.tcl',
                         'control-fragmented-drc.rpt','control-complete-drc.rpt','control-spacing-negative-drc.rpt',
                         'control-fragmented.log','control-complete.log','control-spacing-negative.log','gds.log'):
                assert sha(receipt.parent/name)==json.loads(receipt.read_text())['outputs'][name]
                add(receipt.parent/name,'evidence/drc/'+name)

    geometry=delivery.parent/('geometry-'+index['macro'].lower())
    geo_receipt=json.loads((geometry/'receipt.json').read_text());assert geo_receipt['passed']
    geo_report=json.loads((geometry/'five-macro-geometry.json').read_text());assert geo_report['passed']
    assert sha(geometry/'five-macro-geometry.json')==geo_receipt['outputs']['five-macro-geometry.json']
    assert geo_report['source_odb_sha256']==index['final_files']['6_final.odb']['sha256']
    for name in ['receipt.json','five-macro-geometry.json','candidate.lef','m10-access.json','native-pins.tsv','occupancy-summary.tsv','native-rect-completion.json']:
        add(geometry/name,'geometry/'+name)
    archive = out / ('block-v2-' + index['macro'].lower() + '-native.tar.gz')
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
