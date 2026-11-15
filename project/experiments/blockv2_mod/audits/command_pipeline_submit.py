"""One entry: production regressions -> both graph compiles -> assembly -> chained decode."""
import argparse,json,subprocess
from pathlib import Path
from check_pr185_control_admission import validate
from command_pipeline_contract import validate_service_pipeline
p=argparse.ArgumentParser()
p.add_argument('--hardware',type=Path,required=True);p.add_argument('--services',type=Path,required=True)
p.add_argument('--output',type=Path,required=True);a=p.parse_args()
hardware=json.loads(a.hardware.read_text());validate(hardware)
validate_service_pipeline(hardware)
for h in (512,513):
 scenario=json.loads(Path(f'evidence/joint-frontier/decode512-standard/graph-{h}/scenario.json').read_text())
 if scenario['history_positions']!=h or scenario['decode_steps_total']!=2:raise ValueError('wrong scenario')
a.output.mkdir(parents=True,exist_ok=False);jobs={}
def submit(name,script,args=(),deps=()):
 command=['sbatch','--parsable','--output',str(a.output/(name+'-%j.log'))]
 if deps:command+=['--dependency=afterok:'+':'.join(map(str,deps))]
 command+=[script,*map(str,args)]
 job=int(subprocess.check_output(command,text=True).strip().split(';')[0]);jobs[name]=job
 (a.output/'jobs.json').write_text(json.dumps(jobs,indent=2)+'\n')
 return job
tests=submit('tests','audits/command_pipeline_full_tests.sbatch')
plans=a.output/'plans'
first=submit('compile512','audits/command_pipeline_compile.sbatch',(512,plans/'512',a.hardware,a.services),(tests,))
second=submit('compile513','audits/command_pipeline_compile.sbatch',(513,plans/'513',a.hardware,a.services),(tests,))
packages=a.output/'packages'
pack=submit('package','audits/command_pipeline_package.sbatch',(plans,packages,a.hardware),(first,second))
submit('execute','audits/command_pipeline_run.sbatch',(packages,plans,a.output/'execution'),(pack,))
print(json.dumps(jobs))
