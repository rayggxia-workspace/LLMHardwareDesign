"""Read-only mapped-netlist inventory; pin counts and nominal Liberty capacitance."""
from pathlib import Path
from collections import Counter,defaultdict,deque
import json,hashlib,re,argparse,sys
sys.setrecursionlimit(20000)
from mapped_cost import bodies
from strict_state import canonical_state_name

def inventory(folder,lib,top=None):
 data=json.loads((folder/'mapped.json').read_text());modules={k:v for k,v in data['modules'].items()if not v.get('attributes',{}).get('blackbox')};tops=[k for k,v in modules.items()if v.get('attributes',{}).get('top')in('1','00000000000000000000000000000001',1)];top=top or tops[0]
 text=lib.read_text();areas={};caps={}
 for cell,body in bodies(text,r'\bcell\s*\(\s*(\w+)\s*\)'):
  areas[cell]=float(re.search(r'\barea\s*:\s*([\d.]+)',body)[1])
  for pin,pbody in bodies(body,r'\bpin\s*\(\s*(\w+)\s*\)'):
   cap=re.search(r'\bcapacitance\s*:\s*([\d.]+)',pbody)
   if cap:caps[cell+'/'+pin]=float(cap[1])
 unit=re.search(r'capacitive_load_unit\s*\(\s*([\d.]+)\s*,\s*(\w+)\s*\)',text).groups();scale=float(unit[0])*(1000 if unit[1]=='pf'else 1)
 count=Counter();direct={};alltops=[];details={}
 def visit(name):
  m=modules[name];local=Counter();loads=defaultdict(list);names={};drivers={}
  for n,v in sorted(m['netnames'].items(),key=lambda x:x[0].startswith('$')):
   for i,b in enumerate(v['bits']):
    if isinstance(b,int)and b not in names:names[b]=canonical_state_name(n)+(('['+str(i)+']')if len(v['bits'])>1 else'')
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
  nonclock=[b for b in loads if names.get(b)!='clk'];high=[b for b in nonclock if len(loads[b])>=256]
  summary=dict(nonclock_nets_fanout_ge256=len(high),pin_capacitance_sum_ff=sum(caps.get(t+'/'+p,0)*scale for b in high for n,t,p in loads[b]),direct_input_pins_sum=sum(len(loads[b])for b in high),definition='all non-clock nets with at least 256 input-pin loads; includes high-fanout data nets; not effective root capacitance or power')
  primary={b for p in m['ports'].values()if p['direction']=='input'for b in p['bits']}
  source_cache={};depth_cache={};class_cache={}
  def seq(t):return t.startswith(('DFF','SDFF','DLH','DLL'))
  def sources(b):
   if b in source_cache:return source_cache[b]
   if b in primary or b not in drivers:result={names.get(b,str(b))}
   else:
    n,t,p=drivers[b]
    if seq(t)or t not in areas:result={names.get(b,str(b))}
    else:
     result=set()
     for pin,bs in m['cells'][n]['connections'].items():
      if m['cells'][n]['port_directions'][pin]=='input':
       for bit in bs:
        if isinstance(bit,int):result.update(sources(bit))
   source_cache[b]=result;return result
  def depth(b):
   if b in depth_cache:return depth_cache[b]
   if b not in drivers:return 0
   n,t,p=drivers[b]
   if seq(t)or t not in areas:return 0
   c=m['cells'][n];value=1+max((depth(v)for p,bs in c['connections'].items()if c['port_directions'][p]=='input'for v in bs if isinstance(v,int)),default=0);depth_cache[b]=value;return value
  nonclock_top=[info(b)for b in sorted(nonclock,key=lambda b:len(loads[b]),reverse=True)[:20]]
  for row in nonclock_top:row['first_sequential_or_input_sources']=sorted(sources(row['bit']))
  paths={'state_write_D':[],'operand_read_D':[]}
  if name in ['block_v1_r','r_stream']:
   for n,c in m['cells'].items():
    if not seq(c['type'])or'D'not in c['connections']:continue
    q=c['connections'].get('Q',c['connections'].get('QN',[]));label=names.get(q[0],'')if q else''
    group='state_write_D'if label.startswith(('bank0[','bank1['))else'operand_read_D'if label.startswith(('operand_a[','operand_b[','operand_state_base[','oa[','ob[','obase['))else None
    if group:paths[group].append(depth(c['connections']['D'][0]))
  def classes(cell):
   if cell in class_cache:return class_cache[cell]
   c=m['cells'][cell]
   if seq(c['type']):
    q=c['connections'].get('Q',c['connections'].get('QN',[]));label=names.get(q[0],'')if q else''
    result={'write'}if label.startswith(('bank0[','bank1['))else{'read'}if label.startswith(('operand_a[','operand_b[','operand_state_base[','oa[','ob[','obase[','rsp_data['))else{'commit'}if label in ['bank_role','role']else{'other'}
   else:
    result=set()
    for p,bs in c['connections'].items():
     if c['port_directions'][p]=='output':
      for b in bs:
       for child,t,pin in loads.get(b,[]):result.update(classes(child))
   class_cache[cell]=result;return result
  role_classification={}
  role_bits=m['netnames'].get('bank_role',m['netnames'].get('role',{})).get('bits',[])
  if role_bits:
   for n,t,p in loads[role_bits[0]]:
    key='+'.join(sorted(classes(n)))or'no_sequential_endpoint';role_classification[key]=role_classification.get(key,0)+1
  details[name]=dict(top20_nonclock=nonclock_top,high_fanout_summary=summary,max_logic_depth_all_fanins={k:max(v,default=0)for k,v in paths.items()},role_direct_first_sequential_classes=role_classification)

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
 return dict(folder=str(folder),top=top,mapped_sha256=hashlib.sha256((folder/'mapped.json').read_bytes()).hexdigest(),liberty_sha256=hashlib.sha256(lib.read_bytes()).hexdigest(),cell_count=sum(count.values()),area_um2=sum(areas[k]*v for k,v in count.items()),cells=dict(count),bank_role=direct,module_details=details,top20=sorted(alltops,key=lambda v:v['direct_pins'],reverse=True)[:20])
def main():
 p=argparse.ArgumentParser();p.add_argument('folder',type=Path);p.add_argument('--lib',type=Path,default=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib'));a=p.parse_args();print(json.dumps(inventory(a.folder,a.lib),indent=2))
if __name__=='__main__':main()
