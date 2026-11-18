from pathlib import Path
import json,hashlib,xml.etree.ElementTree as E
r=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117');p=r/'audit/C-v28-upper-patch-v2';h=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
def native(n):return set(' '.join(x.split()) for x in (p/n).read_text().split('violation type:')[1:])
a,b=native('native-before.rpt'),native('native-after.rpt');assert not b-a,sorted(b-a)
log=(p/'native-pg-v2-120140.log').read_text();assert log.count('All shapes on net VDD are connected.')==2 and log.count('All shapes on net VSS are connected.')==2
def markers(f):return {(i.findtext('category'),i.findtext('cell'),tuple(v.text for v in i.findall('values/value'))) for i in E.parse(f).findall('.//items/item')}
before=r/'audit/C-v28-i8h50-physical/focused/upper.lyrdb';after=p/'upper.lyrdb';x,y=markers(before),markers(after);assert not y-x;assert len(x-y)==6 and all(c in ("'METAL9.2'","'VIA9.2'") for c,_,_ in x-y)
assert {i for i in x if i[0]=="'METAL10.2'"}=={i for i in y if i[0]=="'METAL10.2'"}
files=[before,after,p/'native-before.rpt',p/'native-after.rpt',p/'native-pg-v2-120140.log',p/'patched.odb',p/'hook.tcl',p/'plan.json']
q=dict(passed=True,full_physical_clear=False,native_before=len(a),native_after=len(b),native_added=sorted(b-a),native_removed=sorted(a-b),PG_VDD_VSS=True,upper_before=len(x),upper_after=len(y),removed_upper=[list(i) for i in sorted(x-y)],all_remaining_markers_exact=True,hashes={str(f):h(f) for f in files})
(p/'native-upper-receipt.json').write_text(json.dumps(q,indent=2))
receipts=[p/n for n in ['structural-receipt.json','gds-local-receipt.json','native-upper-receipt.json']]
for f in receipts:
 q=json.loads(f.read_text());assert q['passed']
 for name,sha in q['hashes'].items():assert h(Path(name))==sha,(name,sha)
source=r/'cu/runs/C-v28-actual-i8-h50/flow/results/nangate45/c-overlay-current/base/6_final.odb'
result=dict(patch_qualified=True,backend_accepted=False,source_odb=str(source),source_odb_sha256=h(source),patched_odb_sha256=h(p/'patched.odb'),scope='Three M9 jog changes and one V9 bridge with explicit M9 connecting stub; other nets/instances/macros/pins/die/logic unchanged. Actual GDS exact delta and local original rules pass; six original upper markers removed without new ones; fresh native no new markers and PG pass. Full unchanged DRC and fresh RCX/timing remain mandatory.',receipts={str(f):h(f) for f in receipts},excluded_failed_checks=[dict(job=120139,reason='Region representation equality rejected; superseded by exact symmetric-difference geometric identity in 120145, with same frozen GDS inputs')],excluded_exploratory_variant='v1 lacks explicit M9 stub and is not qualified')
(p/'integration-binding.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
