import collections
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

R = Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117')
p = R / 'audit/C-v35-upper-patch-v2'
def sha(f):
    h = hashlib.sha256()
    with open(str(f), 'rb') as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()
def markers(f):
    return collections.Counter(x.strip() for x in f.read_text().split('violation type:')[1:])
a, b = markers(p/'native-before.rpt'), markers(p/'native-after.rpt')
assert not b-a, list((b-a).elements())
upper = ET.parse(str(p/'upper.lyrdb')).findall('.//item')
assert not upper, len(upper)
log = (p/'native-pg-v2-120235.log').read_text()
for net in ['VDD', 'VSS']:
    assert log.count('All shapes on net '+net+' are connected.') == 2
assert log.count('NATIVE_PG_CHECK_COMPLETE') == 2
for name in ['structural-receipt.json', 'gds-local-receipt.json']:
    assert json.loads((p/name).read_text())['passed']
receipt = dict(passed=True, backend_accepted=False,
    native_before=sum(a.values()), native_after=sum(b.values()),
    native_added=0, native_removed=list((a-b).elements()),
    original_upper_diagnostic_items=0, fresh_pg_before_after=['VDD','VSS'],
    jobs=dict(apply=120233,actual_gds=120234,native_pg=120235,upper=120236),
    hashes={str(p/n):sha(p/n) for n in ['native-before.rpt','native-after.rpt','native-pg-v2-120235.log','upper.lyrdb','upper.sbatch','native-pg-v2.sh','native-before.tcl','native-after.tcl']})
(p/'native-upper-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
source=R/'cu/runs/C-v35-unified-i8-h100-pnone/flow/results/nangate45/c-overlay-current/base/6_final.odb'
binding=dict(patch_qualified=True,backend_accepted=False,source_odb=str(source),source_odb_sha256=sha(source),
    patched_odb_sha256=sha(p/'patched.odb'),patched_gds_sha256=sha(p/'patched.gds'),
    scope='Two parent nets only: aperture_data[26] connected M10 jog shifted 80nm; _136204_ serial three-via zigzag replaced by one via and explicit connected M9 L. Actual GDS exact delta, foreign/OBS/width/space/notch, unchanged other nets/interface/Verilog, fresh native no added markers, upper diagnostic zero, PG VDD/VSS pass. Full original deck, antenna, fresh RCX and timing remain mandatory.',
    replay='Whole-wire hook may only apply when both target source wires match the frozen before.def exactly. Re-extract parasitics after combining; do not blindly overwrite later routed target wires.',
    receipts={str(p/n):sha(p/n) for n in ['structural-receipt.json','gds-local-receipt.json','native-upper-receipt.json']},
    scripts={str(p/n):sha(p/n) for n in ['build.py','hook.tcl','plan.json','structure.py','gds-check.py']},
    rejected_variant=dict(path=str(R/'audit/C-v35-upper-patch-v1'),job=120222,reason='Moved via produced insufficient foreign M9 spacing; excluded, not accepted.'))
(p/'integration-binding.json').write_text(json.dumps(binding,indent=2)+'\n')
print(json.dumps(dict(native_before=sum(a.values()),native_after=sum(b.values()),upper_items=len(upper),binding=binding),indent=2))
