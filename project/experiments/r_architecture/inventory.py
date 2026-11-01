"""Read-only mapped-netlist inventory; pin counts and nominal Liberty capacitance."""
from pathlib import Path
from collections import Counter,defaultdict,deque
import json,hashlib,re,argparse
from mapped_cost import bodies

def inventory(folder,lib,top=None):
 data=json.loads((folder/'mapped.json').read_text());modules={k:v for k,v in data['modules'].items()if not v.get('attributes',{}).get('blackbox')};tops=[k for k,v in modules.items()if v.get('attributes',{}).get('top')in('1','00000000000000000000000000000001',1)];top=top or tops[0]
 text=lib.read_text();areas={};caps={}
 for cell,body in bodies(text,r'\bcell\s*\(\s*(\w+)\s*\)'):
  areas[cell]=float(re.search(r'\barea\s*:\s*([\d.]+)',body)[1])
  for pin,pbody in bodies(body,r'\bpin\s*\(\s*(\w+)\s*\)'):
   cap=re.search(r'\bcapacitance\s*:\s*([\d.]+)',pbody)
   if cap:caps[cell+'/'+pin]=float(cap[1])
 unit=re.search(r'capacitive_load_unit\s*\(\s*([\d.]+)\s*,\s*(\w+)\s*\)',text).groups();scale=float(unit[0])*(1000 if unit[1]=='pf'else 1)
 count=Counter();direct={};alltops=[]
 def visit(name):
  m=modules[name];local=Counter();loads=defaultdict(list);names={};drivers={}
  for n,v in sorted(m['netnames'].items(),key=lambda x:x[0].startswith('$')):
   for i,b in enumerate(v['bits']):
    if isinstance(b,int)and b not in names:names[b]=n+(('['+str(i)+']')if len(v['bits'])>1 else'')
  for n,c in m['cells'].items():
   t=c['type']
   if t in areas:count[t]+=1;local[t]+=1
   elif t in modules:visit(t)
   else:raise ValueError(('unmapped cell',t))
   for p,bits in c['connections'].items():
    if c['port_directions'].get(p)=='input':
     for b in bits:
      if isinstance(b,int):loads[b].append((n,t,p))
    elif c['port_directions'].get(p)=='output':
     for b in bits:drivers[b]=(n,t,p)
  def info(b):
   return dict(module=name,net=names.get(b,str(b)),bit=b,direct_pins=len(loads[b]),nominal_input_capacitance_ff=sum(caps.get(t+'/'+p,0)*scale for n,t,p in loads[b]),load_types=dict(Counter(t+'/'+p for n,t,p in loads[b])))
  tops=[info(b)for b in sorted(loads,key=lambda b:len(loads[b]),reverse=True)[:20]];alltops.extend(tops)
  root=m['netnames'].get('bank_role',m['netnames'].get('role',{})).get('bits',[])
  if root:
   b=root[0];net=info(b);seen={b};todo=deque([b]);comb=set();ends=set()
   while todo:
    v=todo.popleft()
    for n,t,p in loads[v]:
     if t.startswith(('DFF','SDFF','DLH','DLL')):ends.add((n,p));continue
     if n in comb:continue
     comb.add(n);c=m['cells'][n]
     for port,bits in c['connections'].items():
      if c['port_directions'].get(port)=='output':
       for x in bits:
        if isinstance(x,int)and x not in seen:seen.add(x);todo.append(x)
   net.update(transitive_combinational_cells=len(comb),transitive_sequential_input_pins=len(ends),transitive_unique_nets=len(seen));direct[name]=net
  return local
 visit(top)
 return dict(folder=str(folder),top=top,mapped_sha256=hashlib.sha256((folder/'mapped.json').read_bytes()).hexdigest(),liberty_sha256=hashlib.sha256(lib.read_bytes()).hexdigest(),cell_count=sum(count.values()),area_um2=sum(areas[k]*v for k,v in count.items()),cells=dict(count),bank_role=direct,top20=sorted(alltops,key=lambda v:v['direct_pins'],reverse=True)[:20])
def main():
 p=argparse.ArgumentParser();p.add_argument('folder',type=Path);p.add_argument('--lib',type=Path,default=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib'));a=p.parse_args();print(json.dumps(inventory(a.folder,a.lib),indent=2))
if __name__=='__main__':main()
