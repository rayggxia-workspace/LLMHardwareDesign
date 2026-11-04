from pathlib import Path
import json,hashlib,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');source=b/'source-828';src=source/'project/experiments/control_v1';record=b/'route-selection-102/sready848-pin-exit-diagnostic64';assert not record.exists();record.mkdir();sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();header=b/'pin-exit-probe841.h';assert header.is_file()
original=(src/'tree_router.cpp').read_text();code=original;transforms=[]
def replace(a,z):
 global code
 assert code.count(a)==1,a;code=code.replace(a,z,1);transforms.append(dict(original=a,observed=z))
for name in ['resource_search.h','ordinary_zero_pattern.h','ordinary_endpoint_escape.h','weighted_bidirectional.h','ordinary_zero_maze.h']:
 replace('#include "'+name+'"','#include "'+str(src/name)+'"')
replace('#include "'+str(src/'ordinary_zero_maze.h')+'"','#include "'+str(src/'ordinary_zero_maze.h')+'"\n#include "'+str(header)+'"')
a=' size_t resource_label_limit=4000000;bool label_option=false,critical_first=false,ordinary_zero=false,ordinary_escape=false,weighted_bidir=false,phase_trace=false;int ordinary_congestion_scale=0,ordinary_search_margin=0,weighted_pair_margin=0,threshold_pattern_rounds=0,ordinary_maze_budget=0;'
z=a.replace('resource_label_limit=4000000','resource_label_limit=8000000').replace('label_option=false','label_option=true').replace('critical_first=false','critical_first=true').replace('ordinary_zero=false','ordinary_zero=true').replace('ordinary_escape=false','ordinary_escape=true').replace('weighted_bidir=false','weighted_bidir=true').replace('phase_trace=false','phase_trace=true').replace('ordinary_maze_budget=0','ordinary_maze_budget=65536');replace(a,z)
a='   trees[n]=move(tree);for(int v:trees[n])++usage[v];++number;';replace(a,a+'\n   if(!iteration&&number==locked_count)write_pin_exit_probe(string(argv[2])+".pin-prefix.json","after-native-prefix",nx,ny,locked_count,ends,fixed,trees,usage);')
a='  previous_conflicts=conflicts;';replace(a,a+'\n  if(!iteration)write_pin_exit_probe(string(argv[2])+".pin-final.json","after-round0",nx,ny,locked_count,ends,fixed,trees,usage);')
restored=code
for row in reversed(transforms):assert restored.count(row['observed'])==1;restored=restored.replace(row['observed'],row['original'],1)
assert restored==original;kernel=record/'observation-kernel.cpp';kernel.write_text(code)
graph=b/'r256-composition-453/topology/boundary-graph.json';parent=b/'r256-composition-453/upper-candidates/8301/route';cases=[]
for i in range(16):
 folder=parent/('trial-'+str(i));inp=folder/'input.txt';log=folder/'router.log';raw=log.read_bytes();snapshot=record/('original-log-'+str(i)+'.txt');snapshot.write_bytes(raw);rounds=[]
 for line in raw.decode().splitlines():
  if not line.startswith('{')or '"conflict_nodes"'not in line:continue
  try:row=json.loads(line)
  except ValueError:continue
  rounds.append(row)
 first=next(r for r in rounds if r['round']==0);assert first['conflict_nodes']>0
 cases.append(dict(case=i,input=str(inp),input_sha256=sha(inp),original_log_path=str(log),original_log_snapshot=str(snapshot),original_log_snapshot_sha256=sha(snapshot),expected_round0=first))
paths=[src/'tree_router.cpp',src/'resource_search.h',src/'ordinary_zero_pattern.h',src/'ordinary_endpoint_escape.h',src/'weighted_bidirectional.h',src/'ordinary_zero_maze.h',src/'router_conflict_snapshot.py',src/'r256_scene.py',kernel,header,graph,parent/'router']
config=dict(schema='control162-complete-path-snapshot-v1',kind='full',kernel=str(kernel),graph=str(graph),sources=[dict(path=str(p),sha256=sha(p))for p in paths],cases=cases)
cp=record/'config.json';cp.write_text(json.dumps(config,indent=2)+'\n');(record/'observation-provenance.json').write_text(json.dumps(dict(original_kernel=str(src/'tree_router.cpp'),original_kernel_sha256=sha(src/'tree_router.cpp'),observed_kernel=str(kernel),observed_kernel_sha256=sha(kernel),normalized_kernel_byte_exact=True,transformations=transforms,scope='Only absolute include paths, effective defaults identical to actual8301 CLI, and observation-only calls change. Existing SHA-bound complete-path helper adds dump after round0; original search decisions, failure and all physical gates untouched. No frozen source modified.'),indent=2)+'\n')
out=b/'r256-pin-exit-diagnostic-848';spec=dict(script='system_upper.py',source_root=str(source),forecast_gib=96,requires=[str(b/'r256-pin-exit-diagnostic-841/receipt.json'),str(b/'r256-zero-maze-regression-829/receipt.json'),str(b/'r256-maze-legacy45-byte-audit-835/receipt.json')],args=['--manifest',str(b/'r256-composition-359/selected/physical.json'),'--graph',str(graph),'--router-conflict-snapshot-config',str(cp),'--out',str(out)])
pending=b/'dynamic-02/node6/pending/00-k-sready848-pin-exit-diagnostic64.json';assert not pending.exists()and not out.exists();tmp=pending.with_suffix('.tmp');tmp.write_text(json.dumps(spec));tmp.rename(pending)
(record/'tasks.json').write_text(json.dumps(dict(time=time.time(),tasks=[dict(path=str(pending),sha256=sha(pending),spec=spec)],config=str(cp),config_sha256=sha(cp),whole_system_qualified=False,scope='Reuse original complete-path snapshot/flood/wire-budget checker for16 actual8301 round0 replays, exact original round counters required. Add observational terminal-exit counts after original native prefix and round0; no routing state/order/cost change. Effective fixed CLI defaults equal actual8301 because original snapshot worker supplies only input/output. All11149 nets have full actual trees per case,16 independent workers in one own16CPU slot. Conservative96GiB full-snapshot forecast reused from actual337 component. Replace only exact own5120/source510/oldS4610 after843 rawspecSHA/UID/job/actualnode/PID/cmd/source/out/graph and fresh memory guard; current8300/8301 and all full chains/other tasks/8parents/externalR remain. Current node6 other forecasts128GiB plus96=224GiB need284.8GiB actualMemAvailable, actual scheduler must freshly admit. Diagnostic only, never a final route/system pass.'),indent=2)+'\n');print(json.dumps(dict(queued=1,cases=16,source=str(source),config=str(cp))))
