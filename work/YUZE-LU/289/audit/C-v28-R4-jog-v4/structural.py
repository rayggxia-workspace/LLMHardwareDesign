from pathlib import Path
import re,json,hashlib,collections
p=Path.cwd();binding=json.loads((p/'source-binding.json').read_text());plans=json.loads((p/'plan.json').read_text());sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
assert all(sha(Path(k))==v for k,v in binding['hashes'].items())
old=(p/'before.def').read_text();new=(p/'patched.def').read_text()
def split(text):
 pre,body=text.split('\nNETS ',1);body,post=body.split('\nEND NETS',1)
 entries={m[1]:m[2] for m in re.finditer(r'^\s*-\s+(\S+)\s+(.*?);\s*$',body,re.M|re.S)}
 return pre,post,entries
a,b,aa=split(old);c,d,bb=split(new);assert a==c and b==d and aa.keys()==bb.keys()
targets={x['net'] for x in plans};changed={k for k in aa if aa[k]!=bb[k]};assert changed==targets
def routes(body):return re.findall(r'(?:\+ ROUTED|\bNEW)\s+(\S+)\s+(.*?)(?=\bNEW|$)',body,re.S)
def points(seq):
 prev=None;out=[]
 for m in re.finditer(r'\(\s*(\*|-?\d+)\s+(\*|-?\d+)(?:\s+(-?\d+))?\s*\)|(\S+)',seq):
  x,y,e,v=m.groups()
  if x is not None:prev=(prev[0] if x=='*' else int(x),prev[1] if y=='*' else int(y));out.append(('point',*prev,e))
  else:out.append(('via',v))
 return out
for net in targets:
 assert aa[net].split('+ ROUTED')[0]==bb[net].split('+ ROUTED')[0]
 ra,rb=routes(aa[net]),routes(bb[net])
 old_other=[(l,points(s)) for l,s in ra if l!='metal10']
 new_other=[(l,points(s)) for l,s in rb if l!='metal10']
 assert old_other==new_other,(net,'non-M10 route changed')
 expected=next(x['m10'] for x in plans if x['net']==net)
 assert [points(s) for l,s in rb if l=='metal10']==[points(s) for s in expected],net
assert (p/'before.v').read_bytes()==(p/'patched.v').read_bytes()
def native(path):
 text=path.read_text();items=re.findall(r'violation type: ([^\n]*)\n\s*srcs: ([^\n]*)\n\s*bbox = ([^\n]*?) on Layer (\S+)',text)
 assert len(items)==text.count('violation type:');return collections.Counter(items)
before=native(p/'native-before.rpt');after=native(p/'native-after.rpt');added=after-before;removed=before-after
assert not added,dict(added)
log=(p/'native-after.log').read_text();assert 'NATIVE_PG_CHECK_COMPLETE' in log
assert 'ERROR' not in log and len(re.findall('connected',log,re.I))>=2
files=[p/f for f in ['source-binding.json','before.def','patched.def','patched.odb','before.v','patched.v','native-before.rpt','native-after.rpt','native-after.log','hook.tcl','plan.json']]
result=dict(passed=True,scope='Four exact parent M10 reroutes only; other net routes/non-NETS/logic exact, no new fresh native markers, PG completed. Actual GDS geometry proof and complete final deck remain separate.',changed_nets=sorted(changed),native_before=sum(before.values()),native_after=sum(after.values()),removed_native=[dict(marker=list(k),multiplicity=v) for k,v in removed.items()],new_native=[],hashes={str(f):sha(f) for f in files})
(p/'structural-receipt.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
