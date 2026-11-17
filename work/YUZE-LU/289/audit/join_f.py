import pathlib,json,hashlib,sys
f=pathlib.Path(sys.argv[1]).resolve();leaf=f.parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
q=json.loads((f/'qualification/receipt.json').read_text());formal=json.loads((f/'formal/receipt.json').read_text());state=json.loads((f/'formal/state-preservation-v2.json').read_text());accepted=json.loads((leaf/'accepted-leaf.json').read_text())
assert q['physical_passed'] and q['full_deck_items']==0 and formal['passed'] and state['passed'] and state['clock_reset_upstream_cones_identical'] and accepted['passed']
assert q['sha256'][str(f/'candidate.v')]==formal['hashes'][str(f/'candidate.v')]==sha(f/'candidate.v')
assert q['sha256'][str(f/'candidate.odb')]==sha(f/'candidate.odb')
assert accepted['sha256'][str(leaf/'candidate.v')]==sha(leaf/'candidate.v')
for report in [f/'counts.tsv',f/'qualification/counts.tsv']:
 counts=dict(line.split() for line in report.read_text().splitlines());assert set(counts)=={'setup','hold','capacitance','slew','fanout'} and all(int(v)==0 for v in counts.values())
for log in [f/'implementation.log',f/'qualification/verify.log']:
 s=log.read_text();assert all(t in s for t in ['All shapes on net VDD are connected.','All shapes on net VSS are connected.','Found 0 net violations.','Found 0 pin violations.'])
assert (f/'native-drc.rpt').stat().st_size==0 and (f/'qualification/native-drc.rpt').stat().st_size==0
paths=[f/('candidate.'+x) for x in ['odb','def','v','sdc','spef']]+[f/'qualification/flow/results/nangate45/f-native-frame/base/6_final.gds',f/'qualification/receipt.json',f/'formal/receipt.json',f/'formal/state-preservation-v2.json',leaf/'accepted-leaf.json',leaf/'parent-abstract-v3/receipt.json',f/'config.mk']
r=dict(passed=True,scope='F block standalone 300MHz original interface constraints, new accepted S X8 leaf; no A/B top RC/STA claim',source_parent='/public/home/yuzelu/project-circuit/main-blockv2-f300-side-01',counts=counts,full_deck_items=0,state_count=state['state_count'],leaf=str(leaf),hashes={str(p):sha(p) for p in paths})
(f/'accepted-parent.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
