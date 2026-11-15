"""PR273 range frontier adapted to actual native commit units.

No new service or implicit link: each range is encoded by the existing backend.
Full reductions remain atomic. Workspace reuse has an explicit dependency.
"""
from collections import defaultdict
from copy import deepcopy

SPLITTABLE={'MatMul','Add','RoPE','RMSNorm','Attention','Gather','Gated'}

def accesses(tile):
 return tile.get('read',[])+tile.get('key_rows',[])+tile.get('value_rows',[])

def expand(tasks,after,order,*,tiles_per_range=1):
 if type(tiles_per_range) is not int or tiles_per_range<1:raise ValueError('positive range size')
 expanded={};parts={};writes=defaultdict(list)
 for name in order:
  task=tasks[name];tiles=task['tiles']
  groups=[tiles[i:i+tiles_per_range] for i in range(0,len(tiles),tiles_per_range)] if task['kind'] in SPLITTABLE else [tiles]
  parts[name]=[]
  for i,group in enumerate(groups):
   key=name if len(groups)==1 else name+'::native_range::'+str(i)
   if key in expanded or (key!=name and key in tasks):raise ValueError('range ID collision')
   node=deepcopy(task);node.update(id=key,tiles=group,range_parent=name)
   expanded[key]=node;parts[name].append(key)
   for tile in group:
    w=tile['write'];lo=w['element_offset'];hi=lo+w['elements']
    if hi<=lo:raise ValueError('empty output range')
    writes[w['value']].append((lo,hi,key))
 for value,rows in writes.items():
  rows.sort()
  if any(a[1]>b[0] for a,b in zip(rows,rows[1:])):raise ValueError('overlapping SSA writers '+value)
 deps={};new_order=[]
 for name in order:
  original=set(after[name])
  for i,key in enumerate(parts[name]):
   node=expanded[key];parents=set();matched=set()
   for tile in node['tiles']:
    for access in accesses(tile):
     for segment in access['segments']:
      lo=segment['source_element'];hi=lo+segment['elements'];covered=0
      for a,b,writer in writes.get(access['root'],[]):
       overlap=max(0,min(hi,b)-max(lo,a))
       if overlap:
        parents.add(writer);matched.add(expanded[writer]['range_parent']);covered+=overlap
      if access['root'] in writes and covered!=hi-lo:raise ValueError('unpublished operand range '+access['root'])
   # Preserve control-only dependencies and unsupported/opaque operand relations.
   for parent in original-matched:parents.update(parts[parent])
   # Existing candidates reuse parent-owned workspaces; do not alias two scopes.
   if i:parents.add(parts[name][i-1])
   if key in parents:raise ValueError('self-dependent range')
   deps[key]=sorted(parents);node['after']=deps[key];new_order.append(key)
 return expanded,deps,new_order,parts
