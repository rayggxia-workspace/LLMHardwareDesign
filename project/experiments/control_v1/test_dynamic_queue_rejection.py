"""Controller regression: invalid newly queued work cannot kill active steps."""
from pathlib import Path
from unittest.mock import patch
import tempfile,json,sys,os

def main():
 source=Path(__file__).with_name('dynamic_queue.py').read_text(); original_read=Path.read_text
 with tempfile.TemporaryDirectory(prefix='ctl162-queue-')as directory:
  base=Path(directory);root=base/'source-269';script=root/'project/experiments/control_v1/run.py';script.parent.mkdir(parents=True);script.write_text('pass\n');(root/'source-manifest.json').write_text('{}')
  out=base/'queue';out.mkdir()
  for sub in ['pending','commands','results']:(out/sub).mkdir()
  good=dict(script='run.py',source_root=str(root),forecast_gib=32,args=['--out',str(base/'leaf')],requires=[])
  (out/'pending/00-valid.json').write_text(json.dumps(good));ticks=[0];polls=[]
  class Process:
   def __init__(self,*args,**kw):self.calls=0
   def poll(self):self.calls+=1;polls.append(self.calls);return 0 if self.calls>=4 else None
  def sleep(seconds):
   ticks[0]+=1;assert ticks[0]<=6,'controller failed to finish'
   if ticks[0]==1:
    for name,spec in [('01-invalid-R-name',good),('02-bad-script',dict(good,script='hidden.py')),('03-bad-root',dict(good,source_root=str(base/'foreign')))]:
     (out/'pending'/(name+'.json')).write_text(json.dumps(spec))
    (out/'queue-closed').write_text('regression complete after drain')
  def read(path,*args,**kwargs):
   if str(path).replace('\\','/')=='/proc/meminfo':return 'MemAvailable: 1073741824 kB\n'
   return original_read(path,*args,**kwargs)
  with patch.object(sys,'argv',['dynamic_queue.py',str(root),str(out),'fixture.sif']),patch.dict(os.environ,{'SLURM_JOB_ID':'269','SLURM_CPUS_PER_TASK':'96'}),patch('subprocess.Popen',Process),patch('time.sleep',sleep),patch.object(Path,'read_text',read):exec(compile(source,'dynamic_queue.py','exec'),{})
  results=json.loads((out/'queue-result.json').read_text());assert not results['passed'];rows=results['finished'];assert rows['00-valid']['returncode']==0 and polls==[1,2,3,4]
  for name in ['01-invalid-R-name','02-bad-script','03-bad-root']:assert rows[name]['returncode']==-2 and rows[name]['rejected_before_admission'];assert not(out/'commands'/(name+'.json')).exists()
  state=json.loads((out/'queue-state.json').read_text());assert state['slots']==6 and state['cpus_per_slot']==16
  print(json.dumps(dict(passed=True,active_step_completed=True,invalid_new_work_rejected=3,allowed_script_and_source_boundary_preserved=True,slots=state['slots'],cpus_per_slot=state['cpus_per_slot'])))
if __name__=='__main__':main()
