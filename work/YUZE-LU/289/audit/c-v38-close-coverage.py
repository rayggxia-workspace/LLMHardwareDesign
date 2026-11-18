"""Close fixture coverage after both strict proofs; never substitutes for a proof."""
from pathlib import Path
import json,hashlib
R=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117');p=R/'audit/C-v38-y640-h75-final-proof'
def h(f):return hashlib.sha256(Path(f).read_bytes()).hexdigest()
binding=json.loads((p/'input-binding.json').read_text())
assert all(h(f)==digest for f,digest in binding.items()),'Changed proof inputs'
proofs=[p/'formal/receipt.json',p/'controls-tag-v3-packed/receipt.json']
assert all(json.loads(f.read_text())['passed'] for f in proofs)
controls=json.loads(proofs[1].read_text());assert controls['state_count']==21095
review=json.loads((p/'actual-master-state-review.json').read_text())
assert review['state_count']==21095 and review['prior_FF_size_changes_exact']
manifest=json.loads((p/'source-manifest.json').read_text())
fixture_paths=manifest['fixture_receipts']+[str(R/'audit/C-v38-all-master-fixture/receipt.json')]
covered=set();fixture_hashes={}
for f in fixture_paths:
    receipt=json.loads(Path(f).read_text());assert receipt['passed'] and receipt['count']==0
    for source,digest in receipt['files_sha256'].items():assert h(source)==digest,source
    covered.update(receipt['masters']);fixture_hashes[f]=h(f)
assert set(review['actual_standard_master_types'])<=covered
assert 'OAI221_X4' not in review['actual_standard_master_types']
supp=dict(passed=True,all_actual_masters_covered=True,actual_master_count=len(review['actual_standard_master_types']),fixtures=fixture_hashes,previous_review_sha256=h(p/'actual-master-state-review.json'),scope='Supplement only: previous failed fixture-coverage gate is closed by 50-master original full-deck fixture 120243. Original proof/source manifest unchanged.')
(p/'coverage-supplement.json').write_text(json.dumps(supp,indent=2)+'\n')
proofs += [p/'actual-master-state-review.json',p/'coverage-supplement.json']
result=dict(passed=True,final_physical_acceptance=False,scope='Actual C-v16 synthesized gold to exact C-v38 y640-h75 legalized gate: full data/state/macro and independent clock/reset/control proofs, 21095 states and admitted FF sizes. Includes complete actual master fixture coverage supplement. Later routed netlist requires fresh-export byte identity or strict reproof.',hashes=binding,receipts={str(f):h(f) for f in proofs},superseded_gate='120242 final coverage assertion only; strict proof receipts both must pass above')
(p/'complete-equivalence-receipt.json').write_text(json.dumps(result,indent=2)+'\n');print('COMPLETE_STRICT_EQUIVALENCE_AND_ALL_MASTER_COVERAGE_PASS')
