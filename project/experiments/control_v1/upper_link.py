"""Actual two-leaf full control link on research M11/M12; never whole-system STA."""
import argparse,copy,hashlib,heapq,json,os,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--c',type=Path,required=True);p.add_argument('--queue',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 assert os.environ.get('SLURM_JOB_ID') and len(os.sched_getaffinity(0))<=16
 a.out.mkdir(parents=True,exist_ok=False);receipt=dict(passed=False,job=os.environ['SLURM_JOB_ID'],commands=[],inputs={})
 def run(cmd,log):
  with (a.out/log).open('w') as f:q=subprocess.run(list(map(str,cmd)),cwd=a.out,stdout=f,stderr=subprocess.STDOUT)
  receipt['commands'].append(dict(command=list(map(str,cmd)),log=log,sha256=sha(a.out/log),returncode=q.returncode));assert q.returncode==0,log
 try:
  deliveries={};plans={}
  for label,folder in [('C',a.c),('EP',a.queue)]:
   d=json.loads((folder/'delivery.json').read_text());assert d['passed'] and d['native_leaf_accepted'];deliveries[label]=d
   for name,entry in d['final_files'].items():assert sha(entry['path'])==entry['sha256']
   assert sha(folder/'pins.json')==d['pins_sha256'];plans[label]=json.loads((folder/'pins.json').read_text())
   for op,g in d['gate_receipts'].items():assert sha(g['path'])==g['sha256'] and json.loads(Path(g['path']).read_text())['passed']
   receipt['inputs'][str(folder/'delivery.json')]=sha(folder/'delivery.json')
  tools=ROOT/'project/experiments/block_v1';sys.path.insert(0,str(tools));from overlay import generate
  technology=json.loads((tools/'technology-2um-v1.json').read_text())
  generate(Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lef/NangateOpenCellLibrary.tech.lef'),technology,a.out/'technology')
  placements={'C':[64,64],'EP':[64+deliveries['C']['die_um'][0]+96,64+4*round((deliveries['C']['die_um'][1]-deliveries['EP']['die_um'][1])/8)]}
  pairs=[('cmd_data_'+str(n),'C',f'task_data[{n}]','EP',f'cmd_data[{n}]') for n in range(32)]
  pairs += [('cmd_valid','C','task_valid','EP','cmd_valid'),('cmd_last','C','task_last','EP','cmd_last'),('cmd_ready','EP','cmd_ready','C','task_ready')]
  pairs += [('done_data_'+str(n),'EP',f'done_data[{n}]','C',f'done_data[{n}]') for n in range(32)]
  pairs += [('done_valid','EP','done_valid','C','done_valid'),('done_last','EP','done_last','C','done_last'),('done_ready','C','done_ready','EP','done_ready')]
  assert len(pairs)==70
  pins={label:{p['pin']:p for p in plan['pins']} for label,plan in plans.items()}
  def point(label,pin):
   x,y=pins[label][pin]['xy_um'];dx,dy=placements[label];gx=(x+dx-.095)/4;gy=(y+dy-.07)/4
   assert abs(gx-round(gx))<1e-8 and abs(gy-round(gy))<1e-8;return round(gx),round(gy)
  terminals={name:(point(l,p),point(r,q)) for name,l,p,r,q in pairs}
  width=4*int((placements['EP'][0]+deliveries['EP']['die_um'][0]+128)/4+1);height=4*int((max(deliveries['C']['die_um'][1],deliveries['EP']['die_um'][1])+192)/4+1)
  nx,ny=int(width/4),int(height/4);occupied=[{},{}]
  for name,ends in terminals.items():
   for x,y in ends:assert (x,y) not in occupied[0];occupied[0][x,y]=name
  paths={};expanded=0
  for name in sorted(terminals,key=lambda n:-(abs(terminals[n][0][0]-terminals[n][1][0])+abs(terminals[n][0][1]-terminals[n][1][1]))):
   start=(*terminals[name][0],0);goal=(*terminals[name][1],0);queue=[];distance={start:0};parent={};serial=0
   def heuristic(v):return abs(v[0]-goal[0])+abs(v[1]-goal[1])+(3 if v[2] else 0)
   heapq.heappush(queue,(heuristic(start),serial,start))
   while queue:
    estimate,_,v=heapq.heappop(queue);cost=distance[v]
    if estimate!=cost+heuristic(v):continue
    if v==goal:break
    expanded+=1;assert expanded<30000000,'Explicit route search budget exhausted'
    x,y,layer=v;choices=[((x-1,y,0),1),((x+1,y,0),1)] if layer==0 else [((x,y-1,1),1),((x,y+1,1),1)]
    # Chessboard via11 sites enforce 2.2um cut spacing on the 4um wire grid.
    if (x+y)%2==0:choices.append(((x,y,1-layer),3))
    for w,step in choices:
     xx,yy,ll=w
     if not (4<=xx<nx-4 and 4<=yy<ny-4) or occupied[ll].get((xx,yy),name)!=name:continue
     if cost+step<distance.get(w,10**20):distance[w]=cost+step;parent[w]=v;serial+=1;heapq.heappush(queue,(cost+step+heuristic(w),serial,w))
   else:raise AssertionError(('No legal two-layer route',name,len(paths)))
   path=[goal]
   while path[-1]!=start:path.append(parent[path[-1]])
   path.reverse();paths[name]=path
   for x,y,l in path:assert occupied[l].get((x,y),name)==name;occupied[l][x,y]=name
  def xy(v):return [190+8000*v[0],140+8000*v[1]]
  shapes=[];segments={};via_sites={};rc=[]
  def box(layer,a,b,net):shapes.append(dict(layer=layer,box_dbu=[min(a[0],b[0])-2000,min(a[1],b[1])-2000,max(a[0],b[0])+2000,max(a[1],b[1])+2000],net=net))
  for name,path in paths.items():
   seg=[];vias=[];length=0;run_start=path[0]
   for i in range(1,len(path)):
    before,now=path[i-1],path[i]
    if now[2]!=before[2]:
     if before!=run_start:seg.append((run_start,before))
     vias.append(now);run_start=now
    elif i==len(path)-1:seg.append((run_start,now))
   segments[name]=seg;via_sites[name]=vias
   for first,last in seg:
    aa,bb=xy(first),xy(last);box('metal11' if first[2]==0 else 'metal12',aa,bb,name);length+=(abs(aa[0]-bb[0])+abs(aa[1]-bb[1]))/2000
   for site in vias:
    pp=xy(site);box('via11',pp,pp,name);box('metal11',pp,pp,name);box('metal12',pp,pp,name)
   for terminal in [path[0],path[-1]]:
    pp=xy(terminal);box('metal10',pp,pp,name);box('via10',pp,pp,name);box('metal11',pp,pp,name)
   estimates=json.loads((a.out/'technology/early-rc-estimates.json').read_text())['variants']
   rc.append(dict(net=name,length_um=length,via10=2,via11=len(vias),estimates={label:dict(wire_cap_ff=length*e['capacitance'],series_ohm=length*e['resistance']+(2+len(vias))*e['via_resistance']) for label,e in estimates.items()}))
  fixture=dict(schema='two-qualified-leaf-control-link/1',expected_bits=70,dbu_per_um=2000,shapes=shapes,
    terminals={name:[xy((*v,0)) for v in ends] for name,ends in terminals.items()},paths=paths,placements_um=placements,
    width_um=width,height_um=height,rc_estimate_only=rc,whole_system_qualified=False)
  (a.out/'routing.json').write_text(json.dumps(fixture,indent=2)+'\n')
  # Full port inventory in each actual-size physical abstract. Existing M1-M10
  # geometry is never edited; the ODB upper netlist has exactly two endpoints.
  lef=['VERSION 5.6 ;','UNITS DATABASE MICRONS 2000 ; END UNITS']
  for label,d in deliveries.items():
   lef += [f'MACRO LINK_{label}',' CLASS BLOCK ;',' ORIGIN 0 0 ;',f' SIZE {d["die_um"][0]} BY {d["die_um"][1]} ;',' SYMMETRY X Y ;']
   for pin in plans[label]['pins']:
    x,y=pin['xy_um'];lef += [f' PIN {pin["pin"]}',f'  DIRECTION {pin["direction"].upper()} ;','  USE SIGNAL ;','  PORT','   LAYER metal10 ;',f'   RECT {x-1:.6f} {y-1:.6f} {x+1:.6f} {y+1:.6f} ;','  END',f' END {pin["pin"]}']
   lef += [f'END LINK_{label}']
  lef+=['END LIBRARY'];(a.out/'leaves.lef').write_text('\n'.join(lef)+'\n')
  text=['VERSION 5.8 ;','DIVIDERCHAR "/" ;','BUSBITCHARS "[]" ;','DESIGN control70 ;','UNITS DISTANCE MICRONS 2000 ;',f'DIEAREA ( 0 0 ) ( {width*2000} {height*2000} ) ;','COMPONENTS 2 ;']
  for label,(x,y) in placements.items():text.append(f'- {label} LINK_{label} + FIXED ( {int(x*2000)} {int(y*2000)} ) N ;')
  text += ['END COMPONENTS','NETS 70 ;']
  for name,l,pin,r,qpin in pairs:
   text.append(f'- {name} ( {l} {pin} ) ( {r} {qpin} )')
   for n,terminal in enumerate([paths[name][0],paths[name][-1]]):
    x,y=xy(terminal);text.append(f' {"+ ROUTED" if n==0 else "NEW"} metal10 ( {x} {y} ) BV1_via10')
   for site in via_sites[name]:
    x,y=xy(site);text.append(f' NEW metal11 ( {x} {y} ) BV1_via11')
   for first,last in segments[name]:
    x,y=xy(first);xx,yy=xy(last);text.append(f' NEW metal{11+first[2]} ( {x} {y} ) ( {xx} {yy} )')
   text.append(' ;')
  text+=['END NETS','END DESIGN'];(a.out/'upper.def').write_text('\n'.join(text)+'\n')
  script='set_thread_count 16\nread_lef {'+str(a.out/'technology/research12.tech.lef')+'}\nread_lef {'+str(a.out/'leaves.lef')+'}\nread_def {'+str(a.out/'upper.def')+'}\n'
  script+='set block [ord::get_db_block]\nif {[llength [$block getNets]] != 70 || [llength [$block getInsts]] != 2} {error "Incomplete actual control link"}\n'
  script+='foreach net [$block getNets] {if {[llength [$net getITerms]] != 2} {error "Wrong connected endpoint count"}}\n'
  script+='source {'+str(tools/'odb_geometry.tcl')+'}\nbvgeom::export {'+str(a.out/'actual-geometry.tsv')+'}\nwrite_db {'+str(a.out/'upper.odb')+'}\nwrite_def {'+str(a.out/'roundtrip.def')+'}\n'
  (a.out/'readback.tcl').write_text(script);run(['openroad','-no_init','-exit',a.out/'readback.tcl'],'readback.log')
  from revision300_escape import geometry,compare
  compare(geometry(a.out/'actual-geometry.tsv',set(paths)),shapes)
  request=dict(fixture=str(a.out/'routing.json'),native={label:dict(path=d['final_files']['6_final.gds']['path'],sha256=d['final_files']['6_final.gds']['sha256']) for label,d in deliveries.items()},output=str(a.out/'joined.gds'))
  (a.out/'join-input.json').write_text(json.dumps(request,indent=2)+'\n')
  script=(Path(__file__).parent/'upper_link_gds.py').read_text().replace('INPUT_MANIFEST_PLACEHOLDER',str(a.out/'join-input.json'))
  (a.out/'join.py').write_text(script);run(['klayout','-b','-r',a.out/'join.py'],'gds.log');proof=json.loads((a.out/'joined-readback.json').read_text());assert proof['passed']
  receipt.update(passed=True,connected_control_bits=70,actual_odb_def_readback=True,actual_joined_gds_readback=True,
   buffer_cells_added=0,scope='Actual C-to-queue two-way control channel geometry, all native masks unchanged; minimal physical composition, not whole-system timing/process/RC qualification',
   whole_system_qualified=False,calibrated_rc_qualified=False,early_rc_over_50ff_high=[r['net'] for r in rc if r['estimates']['high']['wire_cap_ff']>50])
 finally:
  receipt['outputs']={str(f.relative_to(a.out)):sha(f) for f in a.out.rglob('*') if f.is_file()};(a.out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
if __name__=='__main__':main()
