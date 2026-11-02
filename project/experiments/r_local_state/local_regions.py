"""Generate physical fences for actual mapped local storage/read logic."""
from pathlib import Path
import json,re,argparse,collections
p=argparse.ArgumentParser();p.add_argument('mapped',type=Path);p.add_argument('--capacity',type=int,required=True);p.add_argument('--die',type=int,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--lane-local',action='store_true');a=p.parse_args()
m=json.loads(a.mapped.read_text())['modules']['r_stream_local'];driver={};seq=set()
for name,c in m['cells'].items():
 if any(k in c['connections']for k in ['CK','CLK','C']):seq.add(name)
 for pin,bits in c['connections'].items():
  if c['port_directions'][pin]=='output':
   for bit in bits:
    if isinstance(bit,int):driver[bit]=name
groups=collections.defaultdict(set)
for name,n in m['netnames'].items():
 pattern=r'state_store\.BANK\[(\d+)\]\.GROUP\[(\d+)\]'+(r'\.LANE\[(\d+)\]'if a.lane_local else'')
 match=re.search(pattern,name)
 if not match:continue
 key=tuple(map(int,match.groups()))
 for bit in n['bits']:
  if bit in driver and driver[bit]in seq:groups[key].add(driver[bit])
# Include local combinational fan-in of the selected registers, stop at any flop.
for key,cells in groups.items():
 roots=list(cells);todo=[]
 for name in roots:
  c=m['cells'][name]
  for port,bits in c['connections'].items():
   if c['port_directions'][port]=='input' and port not in ['CK','CLK','C']:todo.extend(bits)
 seen=set()
 while todo:
  bit=todo.pop();name=driver.get(bit)
  if name is None or name in seen or name in seq:continue
  seen.add(name);cells.add(name);c=m['cells'][name]
  for port,bits in c['connections'].items():
   if c['port_directions'][port]=='input':todo.extend(bits)
owners=collections.Counter(c for cs in groups.values()for c in cs)
# Shared global decode stays outside local fences.
groups={key:sorted(c for c in cs if owners[c]==1)for key,cs in groups.items()}
expected=2*(a.capacity//128)*(8 if a.lane_local else 1);assert len(groups)==expected and all(groups.values())
ng=a.capacity//128;span=a.die-40;lines=['set block [ord::get_db_block]', 'set dbu [$block getDbUnitsPerMicron]']
for key,cells in sorted(groups.items()):
 b,g=key[:2]
 x0=20 if b==0 else 20+span*.70;x1=20+span*.30 if b==0 else a.die-20
 y0=20+g*span/ng;y1=20+(g+1)*span/ng
 name=f'r166_b{b}_g{g}'
 if a.lane_local:
  lane=key[2];width=(x1-x0)/4;height=(y1-y0)/2
  x0+=(lane%4)*width;x1=x0+width;y0+=(lane//4)*height;y1=y0+height
  name+=f'_l{lane}'
 lines.append(f'set region [odb::dbRegion_create $block {name}]')
 lines.append('$region setRegionType EXCLUSIVE')
 lines.append(f'set group [odb::dbGroup_create $block {name}_cells]')
 lines.append('$region addGroup $group')
 lines.append('$group setType PHYSICAL_CLUSTER')
 lines.append('odb::dbBox_create $region '+' '.join('[expr {round('+f'{v:.3f}'+'*$dbu)}]'for v in [x0,y0,x1,y1]))
 lines.append('foreach name { '+' '.join('{'+c.replace('[',r'\[').replace(']',r'\]')+'}'for c in cells)+' } {set inst [$block findInst $name]; if {$inst eq "NULL"} {error "missing fenced cell $name"}; $region addInst $inst; $group addInst $inst}')
a.out.write_text('\n'.join(lines)+'\n')
a.out.with_suffix('.json').write_text(json.dumps({'regions':{':'.join(map(str,key)):len(c)for key,c in groups.items()},'lane_local':a.lane_local,'lane_grid':'4 columns x 2 rows per 16-row tile'if a.lane_local else None,'shared_cells_unfenced':sum(n>1 for n in owners.values())},indent=2)+'\n')
