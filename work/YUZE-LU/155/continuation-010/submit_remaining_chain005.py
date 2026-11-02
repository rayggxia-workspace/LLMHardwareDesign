import argparse,subprocess,pathlib,hashlib,json,shlex
ap=argparse.ArgumentParser();ap.add_argument('--eco-job',required=True);a=ap.parse_args();assert a.eco_job.isdigit()
r=pathlib.Path.cwd();base='/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-155';host='yuzelu@10.129.166.172';image='/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif';runtime='/public/software/singularity-ce-4.3.4/bin/singularity'
commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip();archive=r/'.local/sram-remaining-source.tar'
subprocess.run(['git','-c','core.autocrlf=false','archive','-o',str(archive),commit,'project/rtl','project/experiments'],check=True);digest=hashlib.sha256(archive.read_bytes()).hexdigest()
def launch(name,short,cpus,hours,dependency,inner):
 remote=base+'/'+name
 subprocess.run(['ssh',host,'test ! -e '+remote+'/source.tar && mkdir -p '+remote],check=True)
 batch=f'''#!/bin/bash
#SBATCH --job-name=yzl-sram-{short}
#SBATCH --partition=c64
#SBATCH --cpus-per-task={cpus}
#SBATCH --mem=0
#SBATCH --time={hours}
set -euo pipefail
cd {remote}
echo '49eae8b526c6eec806473b13db5d98f848424f38de9fa3430e8ce8e157144f3a  {image}' | sha256sum -c -
{runtime} exec --cleanenv --bind /public/home/yuzelu --pwd "$PWD" --env SLURM_JOB_ID="$SLURM_JOB_ID" --env SLURM_CPUS_PER_TASK={cpus} --env OMP_NUM_THREADS={min(cpus,16)} --env OPENBLAS_NUM_THREADS=1 {image} bash run.sh
'''
 local=r/'.local'/name;local.mkdir(exist_ok=False)
 (local/'run.sh').write_text('set -euo pipefail\nsource /OpenROAD-flow-scripts/env.sh\n'+inner+'\n',newline='\n')
 (local/'job.sbatch').write_text(batch,newline='\n')
 sub=dict(source_commit=commit,archive_sha256=digest,remote=remote,dependency=dependency,cpus=cpus,scope='S SRAM only; stage completion is not physical qualification')
 (local/'submission.json').write_text(json.dumps(sub,indent=2)+'\n')
 for p,n in [(archive,'source.tar')]+[(local/n,n) for n in ['run.sh','job.sbatch','submission.json']]:subprocess.run(['scp',str(p),host+':'+remote+'/'+n],check=True)
 cmd='cd '+remote+" && echo '"+digest+"  source.tar' | sha256sum -c - && mkdir source && tar -xf source.tar -C source && sbatch --parsable --dependency="+dependency+' --output=slurm-%j.log job.sbatch'
 raw=subprocess.check_output(['ssh',host,cmd],text=True);job=raw.splitlines()[-1].split(';')[0];assert job.isdigit();sub['job_id']=job
 (local/'submission.json').write_text(json.dumps(sub,indent=2)+'\n');subprocess.run(['scp',str(local/'submission.json'),host+':'+remote+'/submission.json'],check=True)
 print(name,job,flush=True);return job
views=launch('bank-views-005','views',1,'00:15:00','afterok:94836:94839:'+a.eco_job,f'python3 source/project/experiments/s_sram/assemble_eco_views.py --generation {base}/generate-009/generation --eco {base}/bank-eco-004 --model-test {base}/actual-model-009/test/receipt.json --refined-lef /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-155/lef-refinement-003 --out "$PWD/generation"')
physical=launch('physical-013','physical',16,'24:00:00','afterok:'+views,f'python3 source/project/experiments/s_sram/physical.py --generation {base}/bank-views-005/generation --out "$PWD/implementation"')
final_inner=f'''python3 source/project/experiments/s_sram/inspect_final.py --physical {base}/physical-013/implementation --out "$PWD/audit" > audit-launch.log 2>&1 &
audit_pid=$!
OMP_NUM_THREADS=4 python3 source/project/experiments/s_sram/run_actual.py --physical {base}/physical-013/implementation --generation {base}/bank-views-005/generation --verilator /public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator --out "$PWD/function" > function-launch.log 2>&1 &
function_pid=$!
set +e
wait "$audit_pid"; audit_rc=$?
wait "$function_pid"; function_rc=$?
printf 'audit=%s function=%s\\n' "$audit_rc" "$function_rc"
test "$audit_rc" -eq 0 && test "$function_rc" -eq 0'''
final=launch('final-011','final',20,'06:00:00','afterok:'+physical,final_inner)
formal=launch('formal-009','formal',4,'04:00:00','afterok:'+physical,f'python3 source/project/experiments/s_sram/formal_banks.py --physical {base}/physical-013/implementation --out "$PWD/proof"')
(r/'.local/remaining-chain-005.json').write_text(json.dumps(dict(source_commit=commit,bank_eco=a.eco_job,bank_views=views,physical=physical,final=final,formal=formal),indent=2)+'\n')
