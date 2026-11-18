from pathlib import Path
import re,json,hashlib,collections
p=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-m10-notch-v1')
def markers(f):return collections.Counter(re.sub(r'\s+',' ',x).strip() for x in f.read_text().split('violation type:')[1:])
a=markers(p/'native-before.rpt');b=markers(p/'native-full.rpt');removed=list((a-b).elements());added=list((b-a).elements())
assert removed and not added,(removed,added)
assert all('dma_s_rsp_data\\[52\\]' in x and 'Layer metal10' in x for x in removed),removed
r=dict(local_patch_passed=True,full_native_clear=False,scope='Same standalone drt::check_drc default full-design invocation on original and patched ODB. This checker reports additional pre-existing markers versus detailed-router iteration reports; all retained explicitly.',before_count=sum(a.values()),after_count=sum(b.values()),removed=removed,added=added,before_categories=dict(collections.Counter(x.split('srcs:')[0].strip() for x in a.elements())),after_categories=dict(collections.Counter(x.split('srcs:')[0].strip() for x in b.elements())),hashes={str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in [p/'native-before.rpt',p/'native-full.rpt',p/'native-before.tcl',p/'native-check.tcl',p/'patched.odb']})
(p/'native-difference-receipt.json').write_text(json.dumps(r,indent=2));print(json.dumps(r,indent=2))
