import pya,json,re,os,hashlib,collections
from pathlib import Path
out=Path.cwd();run=Path(os.environ['C_OBS_RUN']);config=run/'config.mk'
def setting(name):return re.findall(r'^export '+name+r'\s*=\s*(.*)$',config.read_text(),re.M)[-1].split()
gds_paths=list(map(Path,setting('ADDITIONAL_GDS')));lef_paths=list(map(Path,setting('ADDITIONAL_LEFS')))
instances=collections.defaultdict(list)
for l in (out/'macro-instances.tsv').read_text().splitlines():
 name,master,*placement=l.split('\t');instances[master].append(dict(instance=name,placement=placement))
masters={}
for name in instances:
 rows=[s.split('\t') for s in (out/(name+'.tsv')).read_text().splitlines()];units=int(next(a[1] for a in rows if a[0]=='UNITS'));shape=next(a[2:] for a in rows if a[0]=='MASTER');origin=next(a[1] for a in rows if a[0]=='ORIGIN')
 # In all supplied zero-origin macros DB master coordinates and GDS cell coordinates coincide.
 assert origin in ('0 0','UNKNOWN'),(name,'nonzero db origin',origin)
 obs=collections.defaultdict(list)
 for a in rows:
  if a[0]=='OBS':obs[a[1]].append(list(map(int,a[2:])))
 masters[name]=dict(units=units,obs=obs,size=list(map(int,shape)),db_origin=origin)
results=[];unmatched=set(masters);sources={str(config),str(out/'macro-instances.tsv'),str(Path(__file__))}
for gp in gds_paths:
 lay=pya.Layout();lay.read(str(gp));sources.add(str(gp))
 for name in sorted(set(masters)&{c.name for c in lay.each_cell()}):
  assert name in unmatched,('master present in more than one source GDS',name)
  unmatched.remove(name);m=masters[name];cell=lay.cell(name);origin_records=[]
  for lp in lef_paths:
   text=lp.read_text();match=re.search(r'(?m)^MACRO\s+'+re.escape(name)+r'\s*$(.*?)^END\s+'+re.escape(name)+r'\s*$',text,re.S|re.M)
   if match:
    origin=re.search(r'\bORIGIN\s+([-+\d.]+)\s+([-+\d.]+)\s*;',match[1]);xy=[float(origin[1]),float(origin[2])] if origin else [0.,0.];assert xy==[0.,0.],(name,lp,xy);origin_records.append(dict(path=str(lp),origin=xy));sources.add(str(lp))
  assert origin_records,(name,'no exact source LEF macro')
  for vn,gn in (('via6',22),('via7',24),('via8',26),('via9',28)):
   actual=pya.Region(cell.begin_shapes_rec(lay.layer(gn,0)));mask=pya.Region()
   for box in m['obs'].get(vn,[]):
    v=[x/m['units']/lay.dbu for x in box];assert all(abs(x-round(x))<1e-5 for x in v),(name,vn,v);mask.insert(pya.Box(*map(round,v)))
   gap=actual-mask;total=actual.area()*lay.dbu**2;missing=gap.area()*lay.dbu**2
   row=dict(master=name,instances=instances[name],gds=str(gp),gds_cell=name,lef_sources=origin_records,layer=vn,actual_source_area_um2=total,installed_obs_rectangles=len(m['obs'].get(vn,[])),uncovered_area_um2=missing,fully_covered=gap.is_empty(),uncovered_component_count=gap.count(),uncovered_bbox_um=None if gap.is_empty() else str(gap.bbox().to_dtype(lay.dbu)),uncovered_examples_um=[str(p.bbox().to_dtype(lay.dbu)) for i,p in enumerate(gap.each()) if i<12]);results.append(row)
   print(json.dumps({k:row[k] for k in ('master','layer','installed_obs_rectangles','actual_source_area_um2','uncovered_area_um2','fully_covered')}),flush=True)
  sources.add(str(out/(name+'.tsv')))
assert not unmatched,('Missing actual GDS master',sorted(unmatched))
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
r=dict(completed=True,all_source_upper_cuts_covered=all(x['fully_covered'] for x in results),scope='Read-only actual leaf GDS VIA6–9 material minus currently installed dbMaster cut OBS in identical zero-origin master coordinates. Uncovered source cut material is an abstract coverage omission, NOT proof of an actual parent DRC violation. No geometry edits or trial routes.',run=str(run),rows=results,source_sha256={p:sha(p) for p in sorted(sources)})
(out/'coverage.json').write_text(json.dumps(r,indent=2))
