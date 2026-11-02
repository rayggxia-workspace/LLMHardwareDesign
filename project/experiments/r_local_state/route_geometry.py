"""Read-only DEF/SPEF analysis; distinguish extracted wire C from Liberty pin C.
DEF centerline totals are checked against the router report before interpretation.
"""
from pathlib import Path
import json,re,hashlib,collections,os,subprocess,concurrent.futures,argparse
from native_cell_gate import group,attribute
canon=lambda n:re.sub(r"\\(.)",r"\1",n)
parser=argparse.ArgumentParser();parser.add_argument('--physical',type=Path,required=True);parser.add_argument('--capacity',type=int,required=True);a=parser.parse_args()
assert a.capacity in [256,1024]
assert json.loads((a.physical/'receipt.json').read_text())['exit']==0
P=Path(__file__).resolve().parent;O=Path.cwd()/'results';O.mkdir(exist_ok=False)
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
 return h.hexdigest()
def analyze(candidate,attempt):
 trial=a.physical/'flow'
 root=trial/'results/nangate45'/('r166_'+candidate)/'base';d=O/candidate;d.mkdir()
 stages=[]
 for s in ['3_3_place_gp','5_1_grt','5_2_route','6_final']:
  odb=root/(s+'.odb')
  if not odb.exists():continue
  before=sha(odb);env=os.environ.copy();env.update(INPUT_ODB=str(odb),OUTPUT_TSV=str(d/(s+'.tsv')))
  with(d/(s+'.log')).open('w')as f:r=subprocess.run(['openroad','-exit',str(P/'route_probe.tcl')],env=env,stdout=f,stderr=subprocess.STDOUT)
  assert sha(odb)==before;stages.append(dict(stage=s,exit=r.returncode,odb=str(odb),sha256=before))
 selected=set();selection={}
 for tsv in d.glob('*.tsv'):
  rows=[line.split('\t')for line in tsv.read_text().splitlines()if line.startswith('SELECT\t')]
  selection[tsv.stem]={'sources':len(rows),'max_endpoint_pins':max((int(r[2])for r in rows),default=0),'max_cone_cells':max((int(r[3])for r in rows),default=0),'max_net_fanout':max((int(r[5])for r in rows),default=0)}
 assert selection and all(r['sources']==2*(a.capacity//128)*8*16*2 and 0<r['max_endpoint_pins']<=32 for r in selection.values())
 for p in d.glob('*.tsv'):
  for line in p.open():
   parts=line.rstrip().split('\t')
   if parts[0]=='NET':selected.add(canon(parts[1]))
 result=dict(candidate=candidate,stages=stages,physical_selection_cones=selection,selected_nets=sorted(selected))
 df=root/'6_final.def';sp=root/'6_final.spef'
 if df.exists():
  before=sha(df);total=collections.Counter();nets={};body=[];inside=False;dbu=None;unsupported=[]
  def consume(lines):
   text=' '.join(lines);name=canon(re.match(r'\s*-\s+(\S+)',text)[1]);layers=collections.Counter()
   chunks=re.split(r'\+\s+(?:ROUTED|FIXED|COVER)\s+|\bNEW\s+',text)[1:]
   for chunk in chunks:
    layer=chunk.split()[0];prev=None
    if 'RECT'in chunk:unsupported.append(name)
    for x,y in re.findall(r'\(\s*(\*|-?\d+)\s+(\*|-?\d+)(?:\s+-?\d+)?\s*\)',chunk):
     if prev is None and'*'in[x,y]:raise ValueError(('undefined DEF star',name))
     point=(prev[0]if x=='*'else int(x),prev[1]if y=='*'else int(y))
     if prev is not None:layers[layer]+=(abs(point[0]-prev[0])+abs(point[1]-prev[1]))/dbu
     prev=point
   total.update(layers)
   if name in selected:nets[name]=dict(layers)
  with df.open()as f:
   for line in f:
    if line.startswith('UNITS DISTANCE MICRONS'):dbu=int(line.split()[3])
    if line.startswith('NETS '):inside=True;continue
    if line.startswith('END NETS'):break
    if not inside:continue
    body.append(line)
    if ';'in line:consume(body);body=[]
  assert sha(df)==before
  log=trial/'logs/nangate45'/('r166_'+candidate)/'base/5_2_route.log'
  expected={k:float(v)for k,v in re.findall(r'Total wire length on LAYER (\w+) = ([\d.]+) um',log.read_text())}if log.exists()else{}
  delta={k:total[k]-v for k,v in expected.items()};matched=bool(expected)and all(abs(v)<2 for v in delta.values())and not unsupported
  result.update(def_path=str(df),def_sha256=before,def_centerline_um_by_layer=dict(total),router_report_um_by_layer=expected,def_minus_router_um_by_layer=delta,centerline_matches_router_within_2um_each_layer=matched,selected_def_centerline_um_by_layer=nets,rect_paths_not_supported=sorted(set(unsupported)))
 if sp.exists():
  before=sha(sp);ids={};caps={};capunit='';pinpolicy=''
  with sp.open()as f:
   for line in f:
    if line.startswith('*C_UNIT'):capunit=line.strip()
    if line.startswith('*DESIGN_FLOW'):pinpolicy=line.strip()
    m=re.match(r'^(\*\d+) (\S+)\s*$',line)
    if m and canon(m[2])in selected:ids[m[1]]=canon(m[2])
    if line.startswith('*D_NET '):
     _,net,c=line.split()[:3]
     if net in ids:caps[ids[net]]=float(c)
  assert sha(sp)==before
  result.update(spef_path=str(sp),spef_sha256=before,spef_capacitance_unit=capunit,spef_pin_cap_policy=pinpolicy,selected_spef_D_NET_capacitance=caps)
 # Sum the whole actual selection tree, including buffers, without hiding
 # pin capacitance behind a per-net maximum or counting shared nets twice.
 final_tsv=d/'6_final.tsv';cone_nets=collections.defaultdict(set);loads=collections.defaultdict(list)
 for line in final_tsv.read_text().splitlines():
  fields=line.split('\t')
  if fields[0]=='SELECT_NET':cone_nets[fields[1]].add(canon(fields[2]))
  if fields[0]=='LOAD':loads[canon(fields[1])].append(fields[2:])
 lib=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib');libtext=lib.read_text();cache={}
 def cellpin(master,pin):
  if(master,pin)not in cache:
   cell=group(libtext,'cell',master);body=group(cell,'pin',pin)
   cache[master,pin]=(float(attribute(body,'capacitance')),float(attribute(cell,'area')))
  return cache[master,pin]
 cscale=re.fullmatch(r'\*C_UNIT\s+([0-9.eE+-]+)\s+(FF|PF|NF)',capunit,re.I);assert cscale,capunit
 wire_ff=float(cscale[1])*{'FF':1,'PF':1000,'NF':1000000}[cscale[2].upper()]
 cone_rows=[]
 for source,nn in cone_nets.items():
  missing=nn-set(caps);cells={};pins=0
  for net in nn:
   for master,pin,x,y,inst in loads[net]:
    cap,area=cellpin(master,pin);pins+=cap;cells[inst]=(master,area)
  cone_rows.append({'source':source,'unique_nets':len(nn),'missing_extracted_nets':sorted(missing),'wire_capacitance_ff':wire_ff*sum(caps[n]for n in nn if n in caps),'liberty_input_pin_capacitance_ff':pins,'route_centerline_um':sum(sum(nets.get(n,{}).values())for n in nn),'combinational_area_um2':sum(area for master,area in cells.values()if not master.startswith('DFF')),'endpoint_storage_cell_area_um2':sum(area for master,area in cells.values()if master.startswith('DFF'))})
 assert len(cone_rows)==2*(a.capacity//128)*8*16*2
 result['physical_selection_tree_loads']={'liberty_sha256':sha(lib),'spef_wire_unit':capunit,'pin_capacitance_unit':'fF, actual Liberty capacitance attributes','rows':cone_rows,'scope':'Each complete registered selection cone stops at sequential endpoint pins. Wire-only SPEF C and separately summed actual Liberty sink-pin C; overlapping cones must not be summed as whole-chip area.'}
 result['all_selection_tree_nets_extracted']=all(not row['missing_extracted_nets']for row in cone_rows)
 (d/'GEOMETRY.json').write_text(json.dumps(result,indent=2)+'\n');return result
rows=[analyze(str(a.capacity),None)]
(O/'GEOMETRY.json').write_text(json.dumps(rows,indent=2)+'\n')
assert all(r.get('centerline_matches_router_within_2um_each_layer') and r.get('selected_spef_D_NET_capacitance') and r['all_selection_tree_nets_extracted'] and all(s['exit']==0 for s in r['stages'])for r in rows)
