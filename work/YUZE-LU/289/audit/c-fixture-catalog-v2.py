"""Build a shared frozen master-to-original-full-deck fixture catalog."""
from pathlib import Path
import json,hashlib,sys,xml.etree.ElementTree as ET
R=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117');a=R/'audit'
def h(f):return hashlib.sha256(Path(f).read_bytes()).hexdigest()
out=Path(sys.argv[1]);assert not out.exists()
sources={};mapping={};entries=[]
def bind(f,expected=None):
    value=h(f)
    if expected is not None:assert value==expected,f
    sources[str(f)]=value
    return value
deck=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/drc/FreePDK45.lydrc')
gds=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/gds/NangateOpenCellLibrary.gds')
bind(deck,'4e35cad6786f21c6e233fb606bea59bb44e1a12713008cf7367d65a1a3de2147')
bind(gds,'7fdbd7f4e46283fdd9b9a369e1cae1a7f6f742c8e75cfe943c17f451626fe8e8')
for name,job in [('C-v28-cell-preflight',None),('C-v29-cell-preflight',120149),('C-trace-AOI221X4-fixture',120206),('C-trace-additional-fixture',120212),('C-v38-all-master-fixture',120243),('C-v38-fill-fixture',120264)]:
    f=a/name/'receipt.json';r=json.loads(f.read_text());assert r['passed'] and r['count']==0
    bind(f)
    for path,digest in r['files_sha256'].items():bind(path,digest)
    assert not ET.parse(str(a/name/'full.lyrdb')).findall('.//items/item')
    export=json.loads((a/name/'export-binding.json').read_text())
    for path,digest in export['inputs_sha256'].items():
        source=Path(path)
        if not source.is_absolute():source=a/name/source
        bind(source,digest)
    assert export['recursive_material_readback_exact']
    assert sorted(export['masters'])==sorted(r['masters'])
    entry=dict(receipt=str(f),receipt_sha256=h(f),masters=r['masters'],job=job)
    entries.append(entry)
    for master in r['masters']:mapping.setdefault(master,[]).append(str(f))
# Earlier five-master fixture uses an older receipt schema; validate it explicitly.
p=a/'C-memwr63-static-v1';f=p/'fixture-receipt.json';r=json.loads(f.read_text())
assert r['passed'] and r['count']==0 and not r['markers']
bind(f);bind(p/'fixture-binding.json');bind(p/'fixture.py');bind(p/'fixture-receipt.py');bind(p/'deck-identity.txt')
bind(p/'additional-fixture.gds',r['fixture_sha256']);bind(p/'additional-full.lyrdb',r['report_sha256'])
assert not ET.parse(str(p/'additional-full.lyrdb')).findall('.//items/item')
bind(a/'C-v28-cell-preflight/receipt.json',r['reference_receipt_sha256']);bind(gds,r['source_gds_sha256'])
entries.append(dict(receipt=str(f),receipt_sha256=h(f),masters=r['additional_masters'],job=None,legacy_schema=True))
for master in r['additional_masters']:mapping.setdefault(master,[]).append(str(f))
assert 'OAI221_X4' not in mapping
bind(Path(__file__))
out.write_text(json.dumps(dict(passed=True,scope='Isolated original-library fixtures only; no parent geometry, antenna, timing or function acceptance.',original_deck_sha256=h(deck),original_library_gds_sha256=h(gds),entries=entries,covered_masters=sorted(mapping),master_to_fixture=mapping,all_source_sha256=sources),indent=2)+'\n')
print('FROZEN_CATALOG',out,h(out),'masters',len(mapping))
