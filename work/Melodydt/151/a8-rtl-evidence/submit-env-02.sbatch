#!/bin/bash
#SBATCH --job-name=zenanyan-a8-env
#SBATCH --partition=c64
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --time=00:05:00
#SBATCH --output=/public/home/yuzelu/Melodydt/LLMHardwareDesign/issue151/a8-1d72247-20261102/slurm/zenanyan-a8-env-%j.out
#SBATCH --error=/public/home/yuzelu/Melodydt/LLMHardwareDesign/issue151/a8-1d72247-20261102/slurm/zenanyan-a8-env-%j.err
set -eu
cd /public/home/yuzelu/Melodydt/LLMHardwareDesign/issue151/a8-1d72247-20261102
python3 - <<'PY'
import os,json,platform,subprocess,shutil
from pathlib import Path
def run(argv):
 try:
  p=subprocess.run(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,timeout=20)
  return {'argv':argv,'rc':p.returncode,'out':p.stdout,'err':p.stderr}
 except Exception as e:return {'argv':argv,'error':str(e)}
result={'hostname':platform.node(),'libc':platform.libc_ver(),'tools':{k:shutil.which(k) for k in ['python3','g++','singularity','apptainer','docker','verilator']},'versions':[run(['/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator','--version']),run(['g++','--version'])],'runtime_candidates':[p for p in ['/usr/bin/singularity','/usr/local/bin/singularity','/opt/singularity/bin/singularity','/usr/bin/apptainer','/usr/local/bin/apptainer'] if Path(p).is_file()]}
out=Path('/public/home/yuzelu/Melodydt/LLMHardwareDesign/issue151/a8-1d72247-20261102/runs/env-compute-02')
out.mkdir(exist_ok=False)
(out/'preflight.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
PY
