from pathlib import Path
import hashlib,json,os,runpy,sys
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');base=b/'dynamic-03/node5';rows=[]
for source,expected in [(82,False),(83,True)]:
 root=b/('source-'+str(source));folder=base/('race-control-source-'+str(source));folder.mkdir()
 for name in('pending','results','commands'):(folder/name).mkdir()
 path=folder/'pending/race.json';path.write_text(json.dumps(dict(script='run.py',forecast_gib=1,args=[],requires=[str(folder/'unavailable.json')])));raw=path.read_bytes();(folder/'queue-closed').touch();original=Path.read_bytes;moved=[]
 def moving_read(p):
  if p==path and not moved:
   p.rename(folder/'moved-before-read.json');moved.append(True)
  return original(p)
 Path.read_bytes=moving_read;sys.argv=[str(root/'project/experiments/control_v1/dynamic_queue.py'),str(root),str(folder),'unused-no-task-admitted'];error=None
 try:runpy.run_path(sys.argv[0],run_name='__main__');passed=True
 except FileNotFoundError as e:passed=False;error=str(e)
 finally:Path.read_bytes=original
 assert passed==expected and moved and (folder/'moved-before-read.json').read_bytes()==raw
 if passed:assert json.loads((folder/'queue-result.json').read_text())['passed']
 rows.append(dict(source=source,controller_sha256=hashlib.sha256(Path(sys.argv[0]).read_bytes()).hexdigest(),survived_removed_unadmitted_task=passed,expected_survival=expected,error=error))
(base/'queue-race-regression.json').write_text(json.dumps(dict(passed=True,job=os.environ['SLURM_JOB_ID'],cases=rows,scope='Actual controller filesystem-race negative and positive controls; no EDA task or hardware acceptance synthesized.'),indent=2))
print(json.dumps(dict(passed=True,cases=rows)))
