from pathlib import Path
r=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117');old=r/'audit/C-rcx-zero-normalization-v1';p=r/'audit/C-v27-rcx-normalization-v2';p.mkdir(exist_ok=False);(p/'parser-source.py').write_bytes((old/'parser-source.py').read_bytes())
s=(old/'normalize.py').read_text();a=s.index('for net in targets:');b=s.index("assert changes,",a)
new='''def simple_paths(body):
 out=[]
 for m in re.finditer(r'(?:\\+ ROUTED|\\bNEW)\\s+(\\S+)\\s+(.*?)(?=\\bNEW|$)',body,re.S):
  layer,seq=m.groups();pts=list(re.finditer(r'\\(\\s*(\\*|-?\\d+)\\s+(\\*|-?\\d+)(?:\\s+(-?\\d+))?\\s*\\)',seq))
  if len(pts)!=2 or re.sub(r'\\(.*?\\)','',seq,flags=re.S).strip():continue
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
    pair+='\\n NEW '+v['text'][4:] if v['text'].startswith('NEW ') else '\\n NEW '+v['text'].split(None,2)[2]
    regs,_=parse(pair);merged=regs[layer].merged();polys=list(merged.each())
    if len(polys)!=1 or polys[0].area()!=polys[0].bbox().area():continue
    box=polys[0].bbox();low=min(pt[axis] for pt,e in values);high=max(pt[axis] for pt,e in values);loedge=box.left if axis==0 else box.bottom;hiedge=box.right if axis==0 else box.top;le=low-loedge;he=hiedge-high;half=width[layer]//2
    assert le>=0 and he>=0
    p0=(low,fixed) if axis==0 else (fixed,low);p1=(high,fixed) if axis==0 else (fixed,high)
    line=layer+' '+fmt(p0,None if le==half else le)+' '+fmt(p1,None if he==half else he)
    prefix='+ ROUTED ' if u['text'].startswith('+ ROUTED') else 'NEW '
    trial=body[:u['start']]+prefix+line+'\\n      '+body[u['end']:v['start']]+body[v['end']:]
    rr,_=parse(trial)
    if rr.keys()==original.keys() and all((rr[l]^original[l]).is_empty() for l in rr):accepted=(trial,dict(net=net,operation='coalesce_exact_rectangular_collinear_paths',old_paths=[u['text'],v['text']],new_path=line));break
   if accepted:break
  if not accepted:break
  body,record=accepted;changes.append(record)
 a,_=parse(body);assert a.keys()==original.keys() and all((a[l]^original[l]).is_empty() for l in a);replacements[net]=body
'''
s=s[:a]+new+s[b:];s=s.replace('zero_extension_edits=changes','geometry_preserving_edits=changes').replace('No proven redundant endpoint-zero edit found','No proven geometry-preserving endpoint normalization found');(p/'normalize.py').write_text(s)
s=(old/'run.sbatch').read_text().replace('C-rcx-zero-normalization-v1','C-v27-rcx-normalization-v2').replace('audit/C-main-clock4-physical-v1/rcx-material-119977','audit/C-v27-physical/rcx-material-120031');(p/'run.sbatch').write_text(s)
