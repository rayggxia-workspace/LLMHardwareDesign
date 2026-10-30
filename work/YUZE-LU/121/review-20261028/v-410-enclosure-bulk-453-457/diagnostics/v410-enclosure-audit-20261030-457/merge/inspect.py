from pathlib import Path
import collections,hashlib,json,re,subprocess,sys
sys.path.insert(0,str(Path('..')/'helpers'))
from native_escape import parse,signature,records
from native_escape_audit import readback,geometry,connectivity
case=json.loads(Path('plan.json').read_bytes());nets=case['nets']
for row in nets.values():row['final_paths']=[dict(p,points=[tuple(v)for v in p['points']])for p in row['final_paths']]
def sha(p):
 h=hashlib.sha256()
 with p.open('rb')as f:
  for c in iter(lambda:f.read(8388608),b''):h.update(c)
 return h.hexdigest()
# Retain actual after.def; normalize exactly the proposed new declarations only in a
# separately named structural-audit file. Standard readback remains unchanged.
removed=[];in_vias=False;entry=[];kept=[];count=None
with Path('after.def').open('rb')as inp,Path('after-via-declaration-audit.def').open('wb')as out:
 for line in inp:
  m=re.fullmatch(rb'VIAS (\d+) ;\n',line)
  if m:
   assert not in_vias;in_vias=True;count=int(m[1]);out.write(b'VIAS '+str(count-len(case['definitions'])).encode()+b' ;\n');continue
  if in_vias and line.startswith(b'END VIAS'):
   assert not entry;out.writelines(kept);out.write(line);in_vias=False;continue
  if in_vias:
   entry.append(line)
   if b';'in line:
    raw=b''.join(entry);entry=[]
    if raw.lstrip().split()[1].decode()in case['definitions']:removed.append(raw)
    else:kept.append(raw)
  else:out.write(line)
assert len(removed)==len(case['definitions']) and count is not None
definitions={}
for raw in removed:
 name=raw.lstrip().split()[1].decode();rects={layer.decode():[int(a),int(b),int(c),int(d)]for layer,a,b,c,d in re.findall(rb'\+ RECT (\w+) \( (-?\d+) (-?\d+) \) \( (-?\d+) (-?\d+) \)',raw)};assert rects==case['definitions'][name];definitions[name]=rects
assert definitions==case['definitions']
audit=readback(Path('before.def'),Path('after-via-declaration-audit.def'),nets);assert audit['passed']
assert sha(Path('before.v'))==sha(Path('after.v'))
bg=geometry(Path('before-geometry.tsv'));ag=geometry(Path('after-geometry.tsv'));assert set(bg)==set(ag) and set(nets)<=set(bg)
for n in set(bg)-set(nets):assert collections.Counter(bg[n])==collections.Counter(ag[n]),n
def merged(intervals):
 out=[]
 for a,b in sorted(intervals):
  if out and a<=out[-1][1]:out[-1]=(out[-1][0],max(b,out[-1][1]))
  else:out.append((a,b))
 return out
union={};connect={};exact={}
for net in sorted(nets):
 bc=connectivity(bg[net]);ac=connectivity(ag[net]);assert bc['passed']and ac['passed'];connect[net]=dict(before=bc,after=ac)
 exact[net]=collections.Counter(bg[net])==collections.Counter(ag[net])
 if case['control']:assert exact[net],net
 layers=set(r[0]for r in bg[net])|set(r[0]for r in ag[net]);union[net]={}
 for layer in layers:
  before=[b for l,k,b in bg[net]if l==layer];after=[b for l,k,b in ag[net]if l==layer];xs=sorted({v for b in before+after for v in (b[0],b[2])})
  for a,b in zip(xs,xs[1:]):assert merged((y,Y)for x,y,X,Y in before if x<=a and X>=b)==merged((y,Y)for x,y,X,Y in after if x<=a and X>=b),(net,layer,a,b)
  union[net][layer]=dict(passed=True,x_bands=len(xs)-1,before_rectangles=len(before),after_rectangles=len(after))
with Path('def-diff.txt').open('w')as f:r=subprocess.run(['diff','-u','before.def','after.def'],stdout=f);assert r.returncode in (0,1)
# Full exact readback above validates declarations and every net. Diff size is descriptive only.
diff_bytes=Path('def-diff.txt').stat().st_size
native=Path('native-whole-drc.rpt');types=dict(collections.Counter(s.splitlines()[0]for s in native.read_text().split('violation type: ')[1:]))
files={p.name:dict(bytes=p.stat().st_size,sha256=sha(p))for p in Path('.').iterdir()if p.name in ('before.def','after.def','before.v','after.v','probe.odb','before-geometry.tsv','after-geometry.tsv','native-whole-drc.rpt','after-via-declaration-audit.def')}
Path('probe-result.json').write_text(json.dumps(dict(passed=True,diagnostic_only=True,structural_audit_after_exact_decl_removal=audit,actual_new_via_definitions=definitions,netlist_unchanged=True,connectivity=connect,exact_rectangle_multiset=exact,actual_selected_net_all_layer_rectangle_union_equal=union,files=files,native_types=types,native_violations=sum(types.values()),physical_qualified=False,diagnostic_diff_bytes=diff_bytes,scope='Read-only postcheck of453 actual blockvia DEF/ODB: explicitly permits only194 declared new vias, fullDEF otherwise unchanged, all191 nets metal/cut union equal and connected. No RC/STA/production qualification.'),indent=2)+'\n')
