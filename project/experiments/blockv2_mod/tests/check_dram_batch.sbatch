#!/bin/bash
#SBATCH --job-name=yzl-dram-batch
#SBATCH --partition=debug,c64,c96
#SBATCH --cpus-per-task=2
#SBATCH --time=00:20:00
set -euo pipefail
cd /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search/blockv2-mod
mkdir -p tmp
python=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python
export PYTHONPATH="$("$python" -c 'import json,os;d=json.load(open("reproducibility/environment.json"));print(os.pathsep.join([os.getcwd()+"/hardware"]+d["module_roots"]+d["extra_python_roots"]))')"
tool=/public/home/yuzelu/project-circuit/issue250-u-n32-stored-link-20261112-01/tool.sh
src=/public/home/yuzelu/project-circuit/issue234-ddr-quiet-JDehtRNz/quiet/source
lib="$PWD/evidence/architecture-revision-185/dram-batch-$SLURM_JOB_ID.so"
"$tool" g++ -O2 -std=c++17 -shared -fPIC -I"$src/src" -I"$src/ext/headers" tlm/native_dram_batch.cpp -L"$src" -ldramsim3 -Wl,-rpath,"$src" -o "$lib"
"$tool" env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PYTHONPATH" "$python" tests/check_dram_batch.py /public/home/yuzelu/project-circuit/issue260-tlm-joint-9BiJdfEg/dram-106937.so "$lib" /public/home/yuzelu/project-circuit/issue234-algo1-ffn-chain-20261112-01/DDR4-single-channel.ini "evidence/architecture-revision-185/dram-batch-$SLURM_JOB_ID"
