from pathlib import Path
import re,json,hashlib
r=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117');p=r/'audit/C-v28-upper-patch-v2';src=r/'cu/runs/C-v28-actual-i8-h50/flow/results/nangate45/c-overlay-current/base'
def parse(f):
 s=f.read_text();pre,t=s.split('\nNETS ',1);mid,post=t.split('\nEND NETS',1);return (pre,post),{x.split()[0]:x for x in re.split(r'(?m)^\s*-(?= )',mid)[1:]}
x,a=parse(p/'before.def');y,b=parse(p/'patched.def');assert x==y and set(a)==set(b)
plan=json.loads((p/'plan.json').read_text())['replacements'];changed={n for n in a if a[n]!=b[n]};assert changed==set(plan)
norm=lambda s:' '.join(s.split())
for n,replacements in plan.items():
 expected=a[n]
 for old,new in replacements:assert expected.count(old)==1;expected=expected.replace(old,new)
 assert norm(expected)==norm(b[n]),n
assert (p/'before.v').read_bytes()==(p/'patched.v').read_bytes();assert (p/'before.def').read_bytes()==(src/'6_final.def').read_bytes()
net=r'services.engine\[0\].element.arithmetic.out_data\[62\]'
for branch in ['NEW metal8 ( 2748990 1820940 ) via8_0','NEW metal9 ( 2748990 1820940 ) via9_0','NEW metal8 ( 2748990 1824140 ) via8_0','NEW metal9 ( 2748990 1824340 ) via9_0','NEW metal9 ( 2748990 1824140 ) ( * 1824340 )','NEW metal10 ( 2748990 1820940 ) ( * 1824340 )']:assert branch in b[net],branch
files=[src/'6_final.odb',src/'6_final.def',p/'before.def',p/'patched.def',p/'before.v',p/'patched.v',p/'patched.odb',p/'hook.tcl',p/'plan.json',Path(__file__)]
receipt=dict(passed=True,changed_nets=sorted(changed),only_declared_edits=True,all_other_nets_exact=True,non_NETS_sections_exact=True,macro_pin_die_unchanged=True,verilog_byte_identical=True,via_bridge='Original upper M8 via8 center retained; explicit M9 0.1um stub to moved upper via9; M10 bridge endpoint moved identically. Lower M8/via8/via9 unchanged. Exact shared centerline junctions, no reliance solely on overlapping pads.',parasitics_changed=True,requires_fresh_rcx=True,hashes={str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in files})
(p/'structural-receipt.json').write_text(json.dumps(receipt,indent=2));print('STRUCTURE_PASS')
