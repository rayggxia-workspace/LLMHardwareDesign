#!/bin/bash
#SBATCH --job-name=yzl-phase-state
#SBATCH --partition=debug,c64,c96
#SBATCH --cpus-per-task=2
#SBATCH --time=00:10:00
set -euo pipefail
cd /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search/blockv2-mod
export PYTHONDONTWRITEBYTECODE=1
python=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python
export PYTHONPATH="$("$python" -c 'import json,os;d=json.load(open("reproducibility/environment.json"));print(os.pathsep.join([os.getcwd()+"/hardware"]+d["module_roots"]+d["extra_python_roots"]))')"
base=evidence/architecture-revision-185/shared-memory-bound-packages-114908
"$python" compiler/build_phase_state_bridge.py "$base/prefill-package" "$base/decode-package" evidence/two-input-114228/native-recipe-graph.json evidence/two-input-114228/native-value-layout.json evidence/two-input-114287/native-recipe-graph.json "evidence/architecture-revision-185/phase-state-bridge-$SLURM_JOB_ID.json"
