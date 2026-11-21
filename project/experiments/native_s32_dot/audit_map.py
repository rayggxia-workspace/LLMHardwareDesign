"""Audit all six original mapping outcomes and the three narrow S128 variants."""
import argparse
import json
from pathlib import Path
import re

from audit import read_run
from map_native import LIB_SHA, DECK_SHA


def audit(directory):
    stage, files, inventory = read_run(directory)
    original = stage['job'] == '102415'
    assert stage['job'] in ('102415', '102446')
    rows = []
    for name, data in sorted(files.items()):
        if not name.endswith('/result.json'):
            continue
        folder = name.rsplit('/', 1)[0]
        record = json.loads(data)
        assert record['job'] == stage['job'] and record['source_commit'] == stage['source_commit']
        assert len(record['affinity']) == 10 and record['added_SRAM_B'] == 0 and not record['physical_qualified']
        assert record['liberty_sha256'] == LIB_SHA and record['original_full_deck_sha256'] == DECK_SHA
        assert len(record['rtl_proof_receipts']) == 6
        for proof in ('abc-liberty-conversion.json', 'abc-mapping.json'):
            assert json.loads(files[f'{folder}/{proof}'])['passed']
        old_metadata_failure = original and record['top'] == 'dot_s32_s128'
        assert record['passed'] != old_metadata_failure
        script = files[f'{folder}/map.ys'].decode()
        assert ('flatten -noscopeinfo' in script) != original
        log = files.get(f'{folder}/map.log', files.get(f'{folder}/map.log.tail', b'')).decode()
        match = re.search(r'Chip area for module .*?:\s*([\d.]+)', log)
        assert match
        area = float(match[1])
        if record['passed']:
            assert abs(record['mapped_area_um2'] - area) < 1e-5
            assert record['cell_count'] == sum(record['cells'].values()) and not any(t.startswith('$') for t in record['cells'])
            assert record['logical_multiplier_lanes'] == 4*record['rows']
            assert record['port_bits'] == sum(p['bits'] for p in record['ports'].values())
            for artifact, digest in record['artifacts'].items():
                if artifact == 'mapped.v':
                    continue  # large remote-only mapped.v, exact hash in original receipt
                assert inventory[f'{folder}/{artifact}'] == digest
        rows.append(dict(top=record['top'], rows=record['rows'], real_signed32_lanes=4*record['rows'],
                         mapped_area_um2=area, mapping_verifier_passed=record['passed'],
                         signal_pins=record.get('port_bits'), flop_count=record.get('flop_count'),
                         flop_area_um2=record.get('flop_area_um2'), physical_qualified=False,
                         note='Retained verifier negative: portless Yosys scope metadata was rejected.' if old_metadata_failure else 'Original Nangate45 mapping only.'))
    assert len(rows) == (6 if original else 3)
    assert {r['rows'] for r in rows if r['top']=='dot_s32_s128'} == {1,2,4}
    return dict(job=stage['job'], source_commit=stage['source_commit'], original_Liberty_SHA256=LIB_SHA,
                original_DRC_SHA256=DECK_SHA, rows=rows, DRC_passed=False, original_300MHz_passed=False,
                source_archive_sha256=stage['source_archive_sha256'], receipts_archive_sha256=stage['receipts_archive_sha256'])


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--run', required=True, type=Path)
    args = p.parse_args()
    result = audit(args.run)
    (args.run / 'audit.json').write_text(json.dumps(result, indent=2) + '\n', newline='\n')
    print(json.dumps(result))
