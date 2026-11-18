from pathlib import Path
import pya,re,json,hashlib,collections,os
p=Path.cwd();base=Path(os.environ['C_ZERO_BASE']);report=base/'material/receipt.json';receipt=json.loads(report.read_text());assert not receipt['passed']
def sha(q):return hashlib.sha256(q.read_bytes()).hexdigest()
for n in ('before.def','after.def','layers.tsv','vias.tsv'):assert sha(base/n)==receipt['source_sha256'][str(base/n)]
width={n:int(w) for n,w in (x.split('\t') for x in (base/'layers.tsv').read_text().splitlines())};vias={};vlayers={}
for s in (base/'vias.tsv').read_text().splitlines():
 n,l,*b=s.split('\t');vias.setdefault(n,[]).append((l,list(map(int,b))))
 if l.startswith('metal'):vlayers.setdefault(n,set()).add(l)
source=(p/'parser-source.py').read_text();fragment=source[source.index('fmt=lambda'):source.index('rows=[];canonical={}')] ;exec(compile(fragment,'frozen_material_parser','exec'))
text=(base/'before.def').read_text();match=re.search(r'\nNETS\s+\d+\s*;(.*?)\nEND NETS',text,re.S);assert match;section=match[1];pat=re.compile(r'^\s*-\s+(\S+)\s+(.*?);\s*$',re.M|re.S);entries={m[1]:m for m in pat.finditer(section)};targets=sorted({d['net'] for d in receipt['geometry_differences']});changes=[];replacements={}
zero=re.compile(r'\(\s*(?:\*|-?\d+)\s+(?:\*|-?\d+)\s+(0)\s*\)')
def simple_paths(body):
 out=[]
 for m in re.finditer(r'(?:\+ ROUTED|\bNEW)\s+(\S+)\s+(.*?)(?=\bNEW|$)',body,re.S):
  layer,seq=m.groups();pts=list(re.finditer(r'\(\s*(\*|-?\d+)\s+(\*|-?\d+)(?:\s+(-?\d+))?\s*\)',seq))
  if len(pts)!=2 or re.sub(r'\(.*?\)','',seq,flags=re.S).strip():continue
  values=[];prev=None
  for z in pts:
   x,y,e=z.groups();pt=(prev[0] if x=='*' else int(x),prev[1] if y=='*' else int(y));values.append((pt,None if e is None else int(e)));prev=pt
  if values[0][0]==values[1][0]:continue
  axis=0 if values[0][0][1]==values[1][0][1] else 1
  assert values[0][0][1-axis]==values[1][0][1-axis]
  out.append(dict(start=m.start(),end=m.end(),layer=layer,values=values,axis=axis,text=m[0]))
 return out
for net in targets:
 assert net in entries;body=entries[net][2];original,_=parse(body)
 for m in reversed(list(zero.finditer(body))):
  trial=body[:m.start(1)]+body[m.end(1):];a,_=parse(trial)
  if a.keys()==original.keys() and all((a[l]^original[l]).is_empty() for l in a):
   changes.append(dict(net=net,operation='remove_union_redundant_zero',original_point=m[0],body_offset=m.start(1)));body=trial
 while True:
  paths=simple_paths(body);accepted=None
  for i,u in enumerate(paths):
   for v in paths[i+1:]:
    if u['layer']!=v['layer'] or u['axis']!=v['axis']:continue
    axis=u['axis'];layer=u['layer'];fixed=u['values'][0][0][1-axis]
    if v['values'][0][0][1-axis]!=fixed:continue
    values=u['values']+v['values']
    if all(e is None for pt,e in values):continue
    # Derive the exact pair union, never approximate a nonrectangular region.
    pair='+ ROUTED '+u['text'].split(None,2)[2] if u['text'].startswith('+ ROUTED') else '+ ROUTED '+u['text'][4:]
    pair+='\n NEW '+v['text'][4:] if v['text'].startswith('NEW ') else '\n NEW '+v['text'].split(None,2)[2]
    regs,_=parse(pair);merged=regs[layer].merged();polys=list(merged.each())
    if len(polys)!=1 or polys[0].area()!=polys[0].bbox().area():continue
    box=polys[0].bbox();low=min(pt[axis] for pt,e in values);high=max(pt[axis] for pt,e in values);loedge=box.left if axis==0 else box.bottom;hiedge=box.right if axis==0 else box.top;le=low-loedge;he=hiedge-high;half=width[layer]//2
    assert le>=0 and he>=0
    p0=(low,fixed) if axis==0 else (fixed,low);p1=(high,fixed) if axis==0 else (fixed,high)
    line=layer+' '+fmt(p0,None if le==half else le)+' '+fmt(p1,None if he==half else he)
    prefix='+ ROUTED ' if u['text'].startswith('+ ROUTED') else 'NEW '
    trial=body[:u['start']]+prefix+line+'\n      '+body[u['end']:v['start']]+body[v['end']:]
    rr,_=parse(trial)
    if rr.keys()==original.keys() and all((rr[l]^original[l]).is_empty() for l in rr):accepted=(trial,dict(net=net,operation='coalesce_exact_rectangular_collinear_paths',old_paths=[u['text'],v['text']],new_path=line));break
   if accepted:break
  if not accepted:break
  body,record=accepted;changes.append(record)
 a,_=parse(body);assert a.keys()==original.keys() and all((a[l]^original[l]).is_empty() for l in a);replacements[net]=body
assert changes,'No proven geometry-preserving endpoint normalization found; explicit alternative needed'
# Keep all unrelated body text and non-NETS sections byte-for-byte.
newsection=section
for net in sorted(replacements,key=lambda n:entries[n].start(2),reverse=True):
 m=entries[net];newsection=newsection[:m.start(2)]+replacements[net]+newsection[m.end(2):]
newtext=text[:match.start(1)]+newsection+text[match.end(1):];(p/'normalized.def').write_text(newtext)
after={m[1]:m[2] for m in pat.finditer(newsection)};assert set(after)==set(entries)
for n in entries:
 if n not in targets:assert entries[n][2]==after[n]
 else:
  a,_=parse(entries[n][2]);b,_=parse(after[n]);assert a.keys()==b.keys() and all((a[l]^b[l]).is_empty() for l in a)
v=dict(passed=True,accepted=False,scope='Input DEF normalization only, exact net connectivity and material conserved; needs new extraction and all-net before/after fixed-point check before binding SPEF.',target_nets=targets,geometry_preserving_edits=changes,all_other_net_bodies_exact=True,all_non_NETS_text_exact=True,net_count=len(entries),source_sha256={str(q):sha(q) for q in [base/'before.def',base/'after.def',base/'layers.tsv',base/'vias.tsv',report,p/'parser-source.py',Path(__file__),p/'normalized.def']});(p/'edit-receipt.json').write_text(json.dumps(v,indent=2));print(json.dumps(v,indent=2))
