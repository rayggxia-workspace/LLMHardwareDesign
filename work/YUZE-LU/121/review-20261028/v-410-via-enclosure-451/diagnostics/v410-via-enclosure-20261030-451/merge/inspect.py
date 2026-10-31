from pathlib import Path
import collections,hashlib,json,re,subprocess,sys
sys.path.insert(0,str(Path('..')/'helpers'))
from native_escape import parse,signature,records
from native_escape_audit import readback,geometry,connectivity
case=json.loads(Path('plan.json').read_bytes());net=case['net'];case['final_paths']=[dict(p,points=[tuple(v)for v in p['points']])for p in case['final_paths']]
def sha(p):
 h=hashlib.sha256()
 with p.open('rb')as f:
  for c in iter(lambda:f.read(8388608),b''):h.update(c)
 return h.hexdigest()
# Retain actual after.def; normalize exactly one new declaration only in a
# separately named structural-audit file. Standard readback remains unchanged.
removed=[];in_vias=False;entry=[];kept=[];count=None
with Path('after.def').open('rb')as inp,Path('after-via-declaration-audit.def').open('wb')as out:
 for line in inp:
  m=re.fullmatch(rb'VIAS (\d+) ;\n',line)
  if m:
   assert not in_vias;in_vias=True;count=int(m[1]);out.write(b'VIAS '+str(count-1).encode()+b' ;\n');continue
  if in_vias and line.startswith(b'END VIAS'):
   assert not entry;out.writelines(kept);out.write(line);in_vias=False;continue
  if in_vias:
   entry.append(line)
   if b';'in line:
    raw=b''.join(entry);entry=[]
    if raw.lstrip().split()[1].decode()==case['via']:removed.append(raw)
    else:kept.append(raw)
  else:out.write(line)
assert len(removed)==1 and count is not None
rects={layer.decode():[int(a),int(b),int(c),int(d)]for layer,a,b,c,d in re.findall(rb'\+ RECT (\w+) \( (-?\d+) (-?\d+) \) \( (-?\d+) (-?\d+) \)',removed[0])}
assert rects==case['via_rectangles'],(rects,case['via_rectangles'])
audit=readback(Path('before.def'),Path('after-via-declaration-audit.def'),{net:case});assert audit['passed']
assert sha(Path('before.v'))==sha(Path('after.v'))
bg=geometry(Path('before-geometry.tsv'));ag=geometry(Path('after-geometry.tsv'));assert set(bg)==set(ag)
for n,rows in bg.items():
 if n!=net:assert collections.Counter(rows)==collections.Counter(ag[n]),n
bc=connectivity(bg[net]);ac=connectivity(ag[net]);assert bc['passed']and ac['passed']
def merged(intervals):
 out=[]
 for a,b in sorted(intervals):
  if out and a<=out[-1][1]:out[-1]=(out[-1][0],max(b,out[-1][1]))
  else:out.append((a,b))
 return out
layers=set(r[0]for r in bg[net])|set(r[0]for r in ag[net]);union={}
for layer in layers:
 before=[b for l,k,b in bg[net]if l==layer];after=[b for l,k,b in ag[net]if l==layer];xs=sorted({v for b in before+after for v in (b[0],b[2])})
 for a,b in zip(xs,xs[1:]):
  assert merged((y,Y)for x,y,X,Y in before if x<=a and X>=b)==merged((y,Y)for x,y,X,Y in after if x<=a and X>=b),(layer,a,b)
 union[layer]=dict(passed=True,x_bands=len(xs)-1,before_rectangles=len(before),after_rectangles=len(after))
exact=collections.Counter(bg[net])==collections.Counter(ag[net])
if case['control']:assert exact
with Path('def-diff.txt').open('w')as f:r=subprocess.run(['diff','-u','before.def','after.def'],stdout=f);assert r.returncode in (0,1)
assert Path('def-diff.txt').stat().st_size<30000
native=Path('native-whole-drc.rpt');types=dict(collections.Counter(s.splitlines()[0]for s in native.read_text().split('violation type: ')[1:]))
files={p.name:dict(bytes=p.stat().st_size,sha256=sha(p))for p in Path('.').iterdir()if p.name in ('before.def','after.def','before.v','after.v','probe.odb','before-geometry.tsv','after-geometry.tsv','native-whole-drc.rpt','after-via-declaration-audit.def')}
Path('probe-result.json').write_text(json.dumps(dict(passed=True,diagnostic_only=True,structural_audit_after_exact_decl_removal=audit,actual_new_via_definition=rects,netlist_unchanged=True,before_connectivity=bc,after_connectivity=ac,exact_rectangle_multiset=exact,actual_selected_net_all_layer_rectangle_union_equal=union,other_exported_net_rectangles_unchanged=True,files=files,native_types=types,native_violations=sum(types.values()),physical_qualified=False,scope='Actual self-contained afterDEF/ODB with one explicit block via. Whole native DRC unmodified. Structural audit explicitly permits only the one declared new via; target mask-union equivalence is exact on all metal/cut layers and all other routes/cells/pins/PG/old declarations unchanged. Full GDS XOR/deck/RC/STA remain separate. Clone result must match original196 before interpreting merge.'),indent=2)+'\n')
