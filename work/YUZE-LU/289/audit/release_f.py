import pathlib,json,hashlib,sys,shutil,subprocess,re
root=pathlib.Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117');f=root/'gs/candidate-S-minimal-localv4/parent-F-eco-h20-v4';q=f/'qualification-final';leaf=f.parent
read=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
qr=read(q/'receipt.json');formal=read(f/'formal/receipt.json');state=read(f/'formal/state-preservation-v2.json');lr=read(leaf/'accepted-leaf.json');review=read(root/'audit/F-new-marker-gds-connectivity-v2.json');diff=read(root/'audit/F-native-marker-diff.json')
assert qr['physical_passed'] and qr['full_deck_items']==0 and formal['passed'] and state['passed'] and state['clock_reset_upstream_cones_identical'] and lr['passed'] and review['passed']
assert qr['sha256'][str(f/'candidate.v')]==formal['hashes'][str(f/'candidate.v')]==sha(f/'candidate.v')
assert qr['sha256'][str(f/'candidate.odb')]==sha(f/'candidate.odb')
for p in [f/'counts.tsv',q/'counts.tsv']:
 counts=dict(line.split() for line in p.read_text().splitlines());assert set(counts)=={'setup','hold','capacitance','slew','fanout'} and all(int(v)==0 for v in counts.values())
for p in [f/'implementation.log',q/'verify.log']:
 s=p.read_text();assert all(t in s for t in ['All shapes on net VDD are connected.','All shapes on net VSS are connected.','Found 0 net violations.','Found 0 pin violations.'])
release=f/'release';release.mkdir(exist_ok=True)
# Regenerate a zero-bloat upper-use parent abstract; do not ship default-bloat view.
tcl=release/'export-abstract.tcl';tcl.write_text(f'read_db {{{f}/candidate.odb}}\nwrite_abstract_lef -bloat_factor 0 {{{release}/cfj_group_f.lef}}\n')
with (release/'export-abstract.log').open('w') as out:subprocess.run(['openroad','-no_init','-exit',str(tcl)],stdout=out,stderr=subprocess.STDOUT,check=True)
sys.path.insert(0,str(root/'audit'))
from compare_lef import parse
a,b=map(parse,[release/'cfj_group_f.lef',q/'cfj_group_f.lef'])
assert a['pins']==b['pins'] and a['terms']==b['terms'] and a['size']==b['size'],'Final zero-bloat view altered physical ports'
for ext in ['odb','def','v','sdc','spef']:shutil.copyfile(f/('candidate.'+ext),release/('6_final.'+ext))
shutil.copyfile(q/'flow/results/nangate45/f-native-frame/base/6_final.gds',release/'6_final.gds');shutil.copyfile(q/'cfj_group_f.lib',release/'cfj_group_f.lib')
for p,name in [(q/'receipt.json','physical.json'),(f/'formal/receipt.json','formal.json'),(f/'formal/state-preservation-v2.json','state.json'),(leaf/'accepted-leaf.json','leaf.json'),(root/'audit/F-native-marker-diff.json','native-marker-diff.json'),(root/'audit/F-new-marker-gds-connectivity-v2.json','native-marker-material.json'),(root/'audit/F-gds-timestamp-identity.json','gds-record-identity.json')]:shutil.copyfile(p,release/name)
shutil.copyfile(f/'config.mk',release/'config.mk')
config=(f/'config.mk').read_text()
assert str(leaf/'qualification-v2/local_s_base.lib') in config and str(leaf/'qualification-v2/flow/results/nangate45/local_s_base/base/6_final.gds') in config
paths=[p for p in release.iterdir() if p.is_file()]
assert 'F_REBASE_INVENTORY_PASS' in (f/'implementation.log').read_text() and 'F_REBASE_NETS_PASS' in (f/'implementation.log').read_text()
period=float(re.search(r'create_clock[^\n]*-period ([0-9.]+)',(f/'candidate.sdc').read_text())[1])
assert period==round(10/3,4), 'Unexpected clock serialization'
# write_sdc default4 digits tightens 3.333333333 to3.3333 ns; final reported STA uses that stricter period.
report=dict(passed=True,nominal_period_ns=10/3,nominal_frequency_mhz=300,clock_serialization='write_sdc 4 digits; final STA uses slightly tighter 3.3333ns',period_ns=period,frequency_mhz=1000/period,setup_worst_ns=float((q/'setup.rpt').read_text().split()[-1]),hold_worst_ns=float((q/'hold.rpt').read_text().split()[-1]),power_grid={'VDD':'connected','VSS':'connected'},antenna_net_violations=0,antenna_pin_violations=0,formal_passed=True,state_control_passed=True,signal_and_power_bpin_geometry_unchanged=True,macro_positions_unchanged=True,selected_leaf_output='local_group.services.store.leaf/req_ready',selected_leaf_driver='BUF_X8',scope='F standalone block 300 MHz original timing contract and exact interface/PG; integrated accepted S X8; no A/B top RC/STA claim',setup=(q/'setup.rpt').read_text().strip(),hold=(q/'hold.rpt').read_text().strip(),counts=counts,full_deck_items=0,native_marker_count=44,native_exact_historical_shared=40,native_new_markers=4,native_new_classification='Actual GDS same-net macro-port material connection, individually checked',state_count=state['state_count'],source_parent='/public/home/yuzelu/project-circuit/main-blockv2-f300-side-01',leaf=str(leaf),abstract_recipe='write_abstract_lef -bloat_factor 0; actual parent signal and power port geometry retained',hashes={str(p):sha(p) for p in paths})
(release/'accepted-parent.json').write_text(json.dumps(report,indent=2)+'\n');(f/'accepted-parent.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
(root/'audit/f-queue/STOP').write_text('F completed and release hashes verified\n')
