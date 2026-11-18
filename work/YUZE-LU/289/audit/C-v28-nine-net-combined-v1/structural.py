from pathlib import Path
import re,json,hashlib,collections,xml.etree.ElementTree as E
p=Path.cwd();sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
binding=json.loads((p/'source-binding.json').read_text())
assert all(sha(Path(k))==v for k,v in dict(binding['hashes'],**binding['qualified_inputs']).items())
def split(path):
 text=path.read_text();pre,body=text.split('\nNETS ',1);body,post=body.split('\nEND NETS',1)
 entries={m[1]:m[2] for m in re.finditer(r'^\s*-\s+(\S+)\s+(.*?);\s*$',body,re.M|re.S)}
 return pre,post,entries
a,b,old=split(p/'before.def');c,d,new=split(p/'patched.def');assert a==c and b==d and old.keys()==new.keys()
expected={}
for sub in ('C-v28-R4-jog-v4','C-v28-i8h50-S4-notch','C-v28-upper-patch-v2'):
 _,_,part=split(p.parent/sub/'patched.def')
 changes={k:v for k,v in part.items() if old[k]!=v};assert not expected.keys()&changes.keys();expected.update(changes)
assert len(expected)==9
assert {k:v for k,v in new.items() if old[k]!=v}==expected
assert (p/'before.v').read_bytes()==(p/'patched.v').read_bytes()
def native(path):
 text=path.read_text();rows=re.findall(r'violation type: ([^\n]*)\n\s*srcs: ([^\n]*)\n\s*bbox = ([^\n]*?) on Layer (\S+)',text);assert len(rows)==text.count('violation type:');return collections.Counter(rows)
before=native(p/'native-before.rpt');after=native(p/'native-after.rpt');assert not (after-before)
log=(p/'native-after.log').read_text();assert 'NATIVE_PG_CHECK_COMPLETE' in log and 'All shapes on net VDD are connected.' in log and 'All shapes on net VSS are connected.' in log
items=E.parse(p/'upper.lyrdb').findall('.//items/item');m10=[x for x in items if x.findtext('category')=="'METAL10.2'"];assert not items
assert json.loads((p/'R-material-receipt.json').read_text())['passed'] and json.loads((p/'S-material-receipt.json').read_text())['passed']
files=[p/f for f in ['patched.odb','patched.def','patched.gds','patched.v','source-binding.json','R-material-receipt.json','S-material-receipt.json','native-before.rpt','native-after.rpt','native-after.log','upper.lyrdb','hook.tcl','R-hook.tcl','S-hook.tcl','upper-hook.tcl']]
result=dict(patch_qualified=True,backend_accepted=False,scope='Exact-source nine-net local physical combination only. ANT, timing/electrical and qualified RCX/full deck remain pending.',changed_nets=sorted(expected),native_before=sum(before.values()),native_after=sum(after.values()),native_added=[],native_removed=[dict(marker=list(k),count=v) for k,v in (before-after).items()],upper_m10_count=0,upper_other_count=len(items),hashes={str(f):sha(f) for f in files})
(p/'integration-binding.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
