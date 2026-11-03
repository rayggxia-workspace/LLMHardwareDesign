"""Refill one exact own very slow coupled-weight8 slot, preserve evidence."""
from pathlib import Path
import ast,subprocess,shlex
p=Path(r'D:\Data\电路实验\control162-retire-obsolete335-143.py')
tree=ast.parse(p.read_text(encoding='utf-8'));q=ast.literal_eval(next(n.value for n in tree.body if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='q'for t in n.targets)))
q=q.replace('sready143-twelve-obsolete335-retired','sready144-slow-coupled8-retired')
q=q.replace('sready143-exact-cache-comparison.json','sready144-history-product-comparison.json').replace("comp['identical_successful_route_count']==132","comp['identical_default_routes']==132 and comp['independent_product_cases']==8")
q=q.replace('s-ready-cache-refill-source143.json','s-ready-history-product-refill-source144.json').replace("len(new['tasks'])==84","len(new['tasks'])==7")
q=q.replace("b/'composition-drive-pg-01/topology/boundary-graph.json'","c/'topology/boundary-graph.json'")
q=q.replace("len(g['instances'])==335 and sum(v=='control_link8'for v in g['instances'].values())==309","len(g['instances'])==235 and sum(v=='control_link8'for v in g['instances'].values())==209")
start=q.index('groups=[');end=q.index('\nrows=[]',start)
q=q[:start]+"groups=[(4,25,95204,['00-k-sready140-route-1412'])]"+q[end:]
q=q.replace("source.name in ['source-102','source-105','source-106','source-113','source-114']","source.name=='source-140'")
q=q.replace("assert b in out.parents and not(out/'receipt.json').exists();targets=[]","assert out==c/'upper-candidates/1412/route'and args[args.index('--route-heuristic-weight')+1]=='8'and '--route-congestion-scale'not in args\n  assert b in out.parents and not(out/'receipt.json').exists();targets=[]")
q=q.replace("len(rows)==12 and len({row['target']['step']for row in rows})==12","len(rows)==1 and len({row['target']['step']for row in rows})==1")
q=q.replace('Only individually verified Issue162 obsolete335 external-S searches; user selected S-internal drive, actual235 function/native leaf/bounds qualified. Twelve replacement235 routes plus72 unchanged full gates already queued. Preserve every original spec/output, all eight parent allocations, current235 searches, other tasks and R. Unfinished obsolete searches, not completed physical failures; no threshold relaxed.',
 'Only exact own coupled heuristic8/congestion8 search1412, still first round after other original weight1 searches reached7-12 rounds. Source142 uncoupled8/16 controls and all other current searches retained. Qualified source144 weight1/history-product comparison1511 plus six unchanged full physical gates already queued. Preserve all parent allocations, immutable specs/partial results, other tasks and R. Incomplete search retirement, not a physical failure; no acceptance threshold changed.')
compile(q,'exact_slow_coupled8_refill','exec')
print(subprocess.check_output(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=55).decode())
