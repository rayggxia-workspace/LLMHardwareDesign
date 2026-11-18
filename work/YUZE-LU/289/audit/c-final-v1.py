"""Frozen manifest -> actual C synth-to-candidate strict proofs. Run in allocated EDA container."""
import sys,re,json,hashlib,shutil,subprocess,importlib.util
from pathlib import Path
p=Path(sys.argv[1]).resolve()
manifest=json.loads((p/'source-manifest.json').read_text())
R=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117')
dep=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-201-compact-ge/2ba89c0bd/source/project/experiments/block_v1')
lib=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib')
def h(f):
    digest=hashlib.sha256()
    with Path(f).open('rb') as stream:
        for b in iter(lambda:stream.read(1024*1024),b''):digest.update(b)
    return digest.hexdigest()
def dump(name,value):(p/name).write_text(json.dumps(value,indent=2)+'\n')
gold=R/'cu/runs/C-v16-genericadder-cached/flow/results/nangate45/c-overlay-current/base/1_synth_lec.v'
assert h(gold)=='0d42fdd36b5c0ca3f9fc7682a34465dc6ef60732363be81b7eb465a87d7aa0c4'
for key in ['gate','config','odb','provenance']:
    assert manifest[key] in manifest['expected_sha256'],key
for f,expected in manifest['expected_sha256'].items():assert h(f)==expected,f
model=p/'model-run';(model/'flow/results/nangate45/c-overlay-current/base').mkdir(parents=True)
for src,dst in [(gold,p/'gold.v'),(Path(manifest['gate']),p/'gate.v'),(Path(manifest['config']),model/'config.mk')]:shutil.copyfile(str(src),str(dst))
libs=re.search(r'^export ADDITIONAL_LIBS = (.*)$',(model/'config.mk').read_text(),re.M)[1].split()
files=list(map(Path,manifest['expected_sha256']))+[gold,lib,p/'source-manifest.json',p/'gold.v',p/'gate.v',model/'config.mk']
files += [p/n for n in ['c-final-v1.py','c-formal.py','c-control-packed-v3.py','c-liberty-truth.py']]
files += [dep/(n+'.py') for n in ['native_logic_projection','native_tie_projection','structural_view','native_formal','native_cell_gate']]
prior=R/'audit/C-v35-i8h100-pmid200-legalized-proof/controls-tag-v3-packed/receipt.json'
files += list(map(Path,libs))+list(map(Path,manifest['fixture_receipts']))+[prior]
before={str(f):h(f) for f in files};dump('input-binding.json',before)
subprocess.run(['python3',str(p/'c-formal.py'),str(model),str(p),str(p/'gold.v'),str(p/'gate.v')],check=True)
subprocess.run(['python3',str(p/'c-control-packed-v3.py'),str(p)],check=True)
controls=json.loads((p/'controls-tag-v3-packed/receipt.json').read_text())
assert controls['passed'] and controls['state_count']==21095
assert controls['drive_changes']==json.loads(prior.read_text())['drive_changes'],'Unexpected FF resizing'
top='cfj_group_c_memory_legacy'
data=[json.loads((p/'formal'/(side+'-physical.json')).read_text())['modules'][top]['cells'] for side in ['gold','gate']]
macros=set(json.loads((p/'macrotypes.json').read_text()))
actual=sorted(set(c['type'] for c in data[1].values())-macros)
assert 'OAI221_X4' not in actual
covered=set()
for f in manifest['fixture_receipts']:
    receipt=json.loads(Path(f).read_text());assert receipt['passed'] and receipt['count']==0,f
    covered.update(receipt['masters'])
missing=sorted(set(actual)-covered)
sys.path.insert(0,str(dep))
from native_cell_gate import group,attribute
spec=importlib.util.spec_from_file_location('truth',str(p/'c-liberty-truth.py'));truth=importlib.util.module_from_spec(spec);spec.loader.exec_module(truth)
text=lib.read_text();signatures={}
for typ in actual:
    body=group(text,'cell',typ)
    if re.search(r'\b(?:ff|ff_bank|latch|latch_bank|statetable)\s*\(',body):continue
    pins=[]
    for pin in re.findall(r'\bpin\s*\(\s*"?([^"\s)]+)',body):
        q=group(body,'pin',pin);pins.append([pin,attribute(q,'direction'),attribute(q,'function',False),attribute(q,'three_state',False)])
    signatures[typ]=truth.signature(sorted(pins))
review=dict(passed=not missing,state_count=21095,prior_FF_size_changes_exact=True,actual_standard_master_types=actual,uncovered_fixture_types=missing,truth_signatures=signatures,fixture_receipts={f:h(f) for f in manifest['fixture_receipts']},prior_control_receipt={str(prior):h(prior)})
dump('actual-master-state-review.json',review)
assert not missing,('Need original-deck fixtures',missing)
assert before=={str(f):h(f) for f in files},'Input changed during proof'
receipts=[p/'formal/receipt.json',p/'controls-tag-v3-packed/receipt.json',p/'actual-master-state-review.json']
assert all(json.loads(f.read_text())['passed'] for f in receipts)
dump('complete-equivalence-receipt.json',dict(passed=True,final_physical_acceptance=False,scope='Actual original cached parent synth to this exact candidate: all data/state/macro boundaries and independent clock/reset/enable controls. Later routed netlist needs byte identity or another strict proof.',hashes=before,receipts={str(f):h(f) for f in receipts}))
