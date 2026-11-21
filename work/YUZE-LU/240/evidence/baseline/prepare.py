"""Read frozen selected services; no new compiler/hardware or timing claim."""
import hashlib,json,sys,heapq
from pathlib import Path
sys.path.insert(0,sys.argv[1]);sys.dont_write_bytecode=True
from verify_loop_dp import verify
from verify_primitive_cost import verify as verify_cost
from selected_order_profile import execution_units
ir_path=Path(sys.argv[1])/'generated/ir.json';plan_path=Path(sys.argv[1])/'generated/conditional-dp.json'
ir=json.loads(ir_path.read_text());plan=json.loads(plan_path.read_text())
native=verify_cost(ir);audit=verify(ir['tasks'],ir['hardware'],plan,wire_budget=18)
units=execution_units(ir['tasks'],plan);parents=[set(u['parents']) for u in units];claims={}
for u in units:
 if u['binding'].get('materialized_tile'):raise ValueError('offset-window replay not implemented')
 for r in u['binding']['resources']:
  if ir['hardware']['resources'][r]!=1:raise ValueError('multi-capacity resource requires slot assignment')
  claims.setdefault(r,[]).append((u['row']['start'],u['row']['end'],u['id']))
for r,rows in claims.items():
 rows.sort()
 for prev,nxt in zip(rows,rows[1:]):
  if prev[1]>nxt[0]:raise ValueError('overlapping exclusive reservations')
  parents[nxt[2]].add(prev[2])
children=[[] for _ in units];degree=[len(p) for p in parents];finish=[0]*len(units)
for i,ps in enumerate(parents):
 for p in ps:children[p].append(i)
queue=[i for i,d in enumerate(degree) if not d];heapq.heapify(queue);visited=0
while queue:
 i=heapq.heappop(queue);visited+=1
 finish[i]=max((finish[p] for p in parents[i]),default=0)+units[i]['row']['end']-units[i]['row']['start']
 for c in children[i]:
  degree[c]-=1
  if not degree[c]:heapq.heappush(queue,c)
if visited!=len(units):raise ValueError('cycle')
out=Path('generated');out.mkdir()
with (out/'tasks.txt').open('w') as f:
 f.write(str(len(units))+'\n')
 for u,ps in zip(units,parents):f.write(' '.join(map(str,[u['row']['end']-u['row']['start'],len(ps),*sorted(ps)]))+'\n')
result={'input_sha256':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (ir_path,plan_path)},
 'native_cost_check':native,'schedule_check':audit,'execution_units':len(units),'selected_plan_ticks':plan['makespan'],
 'dependency_resource_order_ticks':max(finish),'logical_128bit_records':plan['external_words'],
 'memory_model':ir['hardware']['virtual_memory'],'scope':'compiled service/resource-order timing replay, not independent command/DRAM/MC/LC calibration; no KV decode'}
(out/'input-report.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:result[k] for k in ('execution_units','selected_plan_ticks','dependency_resource_order_ticks')}))
