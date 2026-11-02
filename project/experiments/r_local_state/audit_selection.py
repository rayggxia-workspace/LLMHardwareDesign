"""Inspect the real pre-buffer mapped state selection, not only port fanout."""
from pathlib import Path
import argparse,json,collections,hashlib
p=argparse.ArgumentParser();p.add_argument('mapped',type=Path);p.add_argument('--capacity',type=int,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
m=json.loads(a.mapped.read_text())['modules']['r_stream_local'];loads=collections.defaultdict(list);drivers=collections.defaultdict(list)
for name,c in m['cells'].items():
 for port,bits in c['connections'].items():
  direction=c['port_directions'][port]
  for bit in bits:
   if isinstance(bit,int):(loads if direction=='input'else drivers)[bit].append((name,port,c['type']))
netnames=collections.defaultdict(list)
for name,n in m['netnames'].items():
 for bit in n['bits']:
  if isinstance(bit,int):netnames[bit].append(name)
def selection(kind):
 names={n:v for n,v in m['netnames'].items()if n.endswith('.'+kind)}
 bits={b for v in names.values()for b in v['bits']if isinstance(b,int)}
 return {'named_arrays':len(names),'unique_bits':len(bits),'max_direct_fanout':max((len(loads[b])for b in bits),default=0),'worst':[{'bit':b,'fanout':len(loads[b]),'names':netnames[b]}for b in sorted(bits,key=lambda b:len(loads[b]),reverse=True)[:8]]}
def cone(bit):
 todo=[bit];seen=set();endpoints=set();comb=set();max_loads=0
 while todo:
  bit=todo.pop()
  if bit in seen:continue
  seen.add(bit);max_loads=max(max_loads,len(loads[bit]))
  for name,pin,typ in loads[bit]:
   c=m['cells'][name]
   if any(k in c['connections']for k in ['CK','CLK','C']):endpoints.add((name,pin));continue
   if name in comb:continue
   comb.add(name)
   for p,bb in c['connections'].items():
    if c['port_directions'][p]=='output':todo.extend(b for b in bb if isinstance(b,int))
 return {'sequential_endpoint_pins':len(endpoints),'combinational_cells':len(comb),'max_cone_net_fanout':max_loads}
cone_summary={}
for kind in ['rsel_q','wsel_q']:
 bits={b for n,v in m['netnames'].items()if n.endswith('.'+kind)for b in v['bits']if isinstance(b,int)}
 rows=[cone(b)for b in bits];cone_summary[kind]={'bits':len(rows),'max_sequential_endpoint_pins':max(r['sequential_endpoint_pins']for r in rows),'max_cone_net_fanout':max(r['max_cone_net_fanout']for r in rows),'max_combinational_cells':max(r['combinational_cells']for r in rows)}
r=selection('rsel_q');w=selection('wsel_q');expected=2*(a.capacity//128)*8*16
checks={'read_local_regs_unique':r['unique_bits']==expected,'write_local_regs_unique':w['unique_bits']==expected,'read_local_fanout_budget':0<r['max_direct_fanout']<=64,'write_local_fanout_budget':0<w['max_direct_fanout']<=64}
checks['read_cone_endpoint_budget']=0<cone_summary['rsel_q']['max_sequential_endpoint_pins']<=32
checks['write_cone_endpoint_budget']=0<cone_summary['wsel_q']['max_sequential_endpoint_pins']<=32
result={'selection_cones':cone_summary,'passed':all(checks.values()),'scope':'structural gate only; not timing or physical qualification','checks':checks,'capacity':a.capacity,'expected_local_selection_bits':expected,'read_selection':r,'write_selection':w,'mapped_sha256':hashlib.sha256(a.mapped.read_bytes()).hexdigest(),'global_top20':[{'bit':b,'fanout':len(v),'names':netnames[b],'drivers':drivers[b]}for b,v in sorted(loads.items(),key=lambda x:len(x[1]),reverse=True)[:20]]}
a.out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items()if k!='global_top20'},indent=2));raise SystemExit(0 if result['passed']else 1)
