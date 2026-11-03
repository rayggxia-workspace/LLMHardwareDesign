"""Queue16 analyses of already verified full paths, with no route replay."""
import subprocess,shlex
q=r'''from pathlib import Path
import json,hashlib,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');base=b/'s-ready-composition-01/1391';source=b/'source-211';record=b/'route-selection-102/sready212-complete-interface-analysis';assert not record.exists()
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();assert json.loads((source/'source-manifest.json').read_text())['commit']=='04dadd9628d0dbec693a6c039f6650018ce6e65c'
parent=b/'router-complete-path-full-205/receipt.json';child=parent.parent/'complete-paths/receipt.json';report=child.parent/'complete-path-diagnostics.json'
assert json.loads(parent.read_text())['passed']and json.loads(child.read_text())['passed'];assert json.loads(child.read_text())['outputs'][report.name]==sha(report)
done=json.loads(report.read_text())['cases'];assert len(done)==16
old=b/'route-selection-102/sready205-complete-path-with-PG/full-config.json';config=json.loads(old.read_text());assert config['kind']=='full';config['kind']='analysis';config['completed_snapshot_receipt']=str(child);config['completed_snapshot_report']=str(report);by_id={r['case']:r for r in done}
for case in config['cases']:
 row=by_id[case['case']];assert row['actual_original_round0']==case['expected_round0']and row['original_input_sha256']==case['input_sha256']
 for k in ['snapshot_path','snapshot_bytes','snapshot_sha256']:case[k]=row[k]
for row in config['sources']:
 if'/source-204/'in row['path']:
  assert sha(row['path'])==row['sha256'];row['path']=row['path'].replace('/source-204/','/source-211/');row['sha256']=sha(row['path'])
config['sources']+=[dict(path=str(p),sha256=sha(p))for p in [parent,child,report]]
record.mkdir();path=record/'config.json';path.write_text(json.dumps(config,indent=2));queue=b/'dynamic-04/node25';task=queue/'pending/00-j-sready212-complete-interface-analysis.json';out=b/'router-complete-interface-analysis-212';assert not task.exists()and not out.exists()
spec=dict(script='system_upper.py',source_root=str(source),forecast_gib=96,requires=list(map(str,[parent,child])),args=list(map(str,['--manifest',base/'selected/physical.json','--graph',base/'topology/boundary-graph.json','--router-conflict-snapshot-config',path,'--out',out])))
tmp=task.with_suffix('.tmp');tmp.write_text(json.dumps(spec));tmp.rename(task)
(record/'tasks.json').write_text(json.dumps(dict(time=time.time(),tasks=[dict(path=str(task),sha256=sha(task),spec=spec,config=str(path),config_sha256=sha(path))],completed_full_snapshot=dict(path=str(parent),sha256=sha(parent)),whole_system_qualified=False,scope='16 actual original complete path snapshots all independently passed exact replay/flood/grid/via/wire/count checks. Analyze same immutable1GB paths by full physical cluster group, no C++ compilation/search rerun. All original physical gates unchanged. Existing now-free own16CPU slot, unchanged memory guard and six-slot c96 queue.'),indent=2))
print(json.dumps(dict(queued=1,record=str(record),whole_system_qualified=False)))
'''
print(subprocess.check_output(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=45).decode())
