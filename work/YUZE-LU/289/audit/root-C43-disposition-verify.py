"""Verify exact final native/PG disposition evidence after full DRC. No approval."""
from pathlib import Path
import hashlib, json, re, xml.etree.ElementTree as ET

R = Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117')
A = R / 'audit/C-v43-independent-v1/C-v43-margin-plan0'
F = R / 'audit/full-C-v43-margin-plan0'
S = R / 'cu/runs/C-v43-margin-plan0/flow/results/nangate45/c-overlay-current/base'
seen = {}

def sha(p):
    p = Path(p).resolve()
    h = hashlib.sha256()
    with p.open('rb') as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            h.update(chunk)
    digest = h.hexdigest()
    if p in seen:
        assert seen[p] == digest, ('Changed during verification', str(p))
    seen[p] = digest
    return digest

def read(p):
    sha(p)
    return json.loads(Path(p).read_text())

def check_hashes(values, base):
    for name, digest in values.items():
        p = Path(name)
        assert sha(p if p.is_absolute() else base / p) == digest

full = read(F / 'receipt.json')
assert full['full_foundry_deck_passed'] is True and full['full_deck_items'] == 0
assert full['deck_sha256'] == '4e35cad6786f21c6e233fb606bea59bb44e1a12713008cf7367d65a1a3de2147'
assert sha(F / 'full.lyrdb') == full['report_sha256']
assert not ET.parse(F / 'full.lyrdb').findall('.//items/item')
assert (F / 'inputs-before.sha256').read_bytes() == (F / 'inputs-after.sha256').read_bytes()
for row in (F / 'inputs-before.sha256').read_text().splitlines():
    digest, name = row.split(None, 1)
    assert sha(name.lstrip('*')) == digest
assert sha(S / '6_final.gds') == '11ed17a55e077a71217667ae6f7e2bb7dbb07d5af22e52450d159d1de4b0bbe9'

native_path = A / 'native/classification/receipt.json'
native = read(native_path)
check_hashes(native['inputs_sha256'], native_path.parent)
assert native['native_markers_resolved'] is True and native['unresolved_indices'] == []
assert native['count'] == len(native['markers']) == 222
assert len({m['index'] for m in native['markers']}) == 222
for m in native['markers']:
    assert m['kind'] == 'Metal Spacing' and m['layer'] in ('metal2', 'metal3')
    assert m['disposition'] == 'explained_same_net_continuous_material'
    assert m['same_net_route_fully_covers_marker'] is True
    assert m['marker_fully_covered_by_actual_metal'] is True
    assert m['actual_local_check'] == {'space': [], 'notch': []}
    assert m['local_spacing_um'] == 0.07
    match = re.fullmatch(r'net:(\S+)', m['source'])
    assert match and match[1] == m['source_net']
for filename in ('native_origin.json', 'metadata_origin.json'):
    origin = read(A / 'native' / filename)
    check_hashes(origin['files'], A / 'native')
    assert origin['files'][str(S / '6_final.odb')] == sha(S / '6_final.odb')

pg_path = A / 'pg-boundary/receipt.json'
pg = read(pg_path)
check_hashes(pg['hashes'], pg_path.parent)
assert pg['passed'] is True
assert pg['normalized_to_candidate_PG_specialwire_material_exact'] is True
assert pg['normalized_to_candidate_PG_BPins_exact'] is True
assert pg['original_to_candidate_BPins_removed'] == 230
assert pg['original_to_candidate_BPins_added'] == 140
assert pg['uncached_PG'] == [['VDD', '0', '1'], ['VSS', '0', '1']]
assert len(pg['all_final_pin_checks']) == 140
for pin in pg['all_final_pin_checks']:
    assert all(pin[k] is True for k in ('same_named_sbox_covers', 'opposite_rail_disjoint', 'actual_gds_covers'))
prior = read(A / 'pg-boundary/prior-PG-disposition-binding.json')
assert prior['current_receipt_sha256'] == sha(pg_path)
assert prior['current_PG_records_byte_exact_C35'] is True
assert sha(prior['source_pg_disposition']) == prior['source_pg_disposition_sha256']
baseline = read(prior['source_pg_disposition'])
assert baseline['pg_boundary_change_accepted_for_candidate_engineering_baseline'] is True
assert baseline['removed_PG_BPins'] == 230 and baseline['added_PG_BPins'] == 140
check_hashes(baseline['receipt_bindings'], R)

for path, digest in list(seen.items()):
    assert sha(path) == digest
result = {'verification_passed': True, 'approved': False,
          'source_gds_sha256': sha(S / '6_final.gds'),
          'full_report_sha256': sha(F / 'full.lyrdb'),
          'native_receipt_sha256': sha(native_path), 'pg_receipt_sha256': sha(pg_path),
          'native_markers': 222, 'PG_removed': 230, 'PG_added': 140,
          'scope': 'Exact same-source native and PG engineering disposition evidence only; root approval and strict backend release aggregation are separate.',
          'inputs_sha256': {str(p): h for p, h in seen.items()}}
(A / 'root-disposition-verification.json').write_text(json.dumps(result, indent=2))
print(json.dumps({k: v for k, v in result.items() if k != 'inputs_sha256'}, indent=2))
