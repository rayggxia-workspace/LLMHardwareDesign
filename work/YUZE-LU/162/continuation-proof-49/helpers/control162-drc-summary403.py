import subprocess,shlex
q=r'''from pathlib import Path
import json,hashlib,time,re,collections
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');folder=b/'r256-current-cugr-snapshot-394';out=b/'r256-current-cugr-drc-summary-403';assert not out.exists();sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();r=json.loads((folder/'receipt.json').read_text());d=json.loads((folder/'snapshot.json').read_text());assert r['passed']and r['stage']=='bounded-routing-diagnostic-only'and d['execution_passed']and not d['actual_router_drc_empty']and not d['independent_original_grid_check']['passed']
counts=collections.Counter()
with(folder/'drc.rpt').open()as f:
 for line in f:
  if line.startswith('violation type:'):counts[line.strip()[16:]]+=1
log=(folder/'openroad.log').read_text();totals=[int(n)for n in re.findall(r'Number of violations\s*=\s*(\d+)',log)];assert totals and sum(counts.values())<totals[-1]
out.mkdir();result=dict(executed=True,time=time.time(),whole_system_qualified=False,inputs={str(folder/name):sha(folder/name)for name in ['receipt.json','snapshot.json','drc.rpt','openroad.log','snapshot.def','snapshot.odb']},current_scene='r256-seven-native/2',actual_current3751_inputs=True,bounded_drt_iterations=1,final_log_violation_count=totals[-1],reported_violation_entries=sum(counts.values()),reported_type_counts=dict(counts),report_complete_coverage_verified=False,independent_original_grid_check=d['independent_original_grid_check'],scope='Actual current345instance snapshot runs original one-iteration diagnosis only. Nonempty DRC plus independently rejected noncheckerboard via excludes this snapshot from qualification. Report contains16809 entries against1573232 final log count and is a partial diagnostic: type counts cannot be interpreted as full global frequencies or proof that only these types exist. Original full3751 remains running; this does not prove all future full results impossible. No pin/rule/threshold changes.')
(out/'summary.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:result[k]for k in ['final_log_violation_count','reported_violation_entries','reported_type_counts','report_complete_coverage_verified','independent_original_grid_check']}))
'''
print(subprocess.check_output(['ssh','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=35).decode())
