#!/bin/bash
#SBATCH --job-name=yzl-r166-stage728
#SBATCH --partition=c96
#SBATCH --cpus-per-task=16
#SBATCH --time=0
#SBATCH --mem=0
#SBATCH --exclude=node16,node19,node20,node21,node25,node26
set -euo pipefail
cd "${1}"
sha256sum -c FILES.sha256 > source-check.log
printf '%s  %s\n' 49eae8b526c6eec806473b13db5d98f848424f38de9fa3430e8ce8e157144f3a /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif | sha256sum -c -
exec /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --pwd "${1}" /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash -c 'source /OpenROAD-flow-scripts/env.sh; set -e; python3 -c '"'"'from pathlib import Path;import json;Path("EARLY_NATIVE_BINDING.json").write_text('"'"'"'"'"'"'"'"'{\n  "physical": "/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-166-r-local-state/attempt718/physical",\n  "source_odb": "/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-166-r-local-state/attempt718/physical/flow/results/nangate45/r166_1024/base/6_final.odb",\n  "source_odb_sha256": "1d848b36183b6fb15fb1cce7b7fe6116119a889030720685133344d039ec2b44",\n  "source_v_sha256": "c7c59ae0560563f317650e729e88bf173b89ca3b5c5c2b7c17508971c8b98ab8",\n  "original_658_v_sha256": "c7c59ae0560563f317650e729e88bf173b89ca3b5c5c2b7c17508971c8b98ab8",\n  "qualification": false,\n  "scope": "Early independent native whole-die diagnostic of actual718 final ODB while original final LEC/RCX continues. Original724 native gate and all original final gates still run; no qualification inferred or transferred."\n}\n'"'"'"'"'"'"'"'"')'"'"'; python3 project/experiments/r_local_state/check_native_tool_source.py --root /public/home/yuzelu/opt/eda/r166-openroad-gc-cache-2eba27b2-offline01 --archives /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-166-r-local-state/native-diagnostic; exec python3 project/experiments/r_local_state/native_complete.py --capacity 1024 --physical /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-166-r-local-state/attempt718/physical --checker-root /public/home/yuzelu/opt/eda/r166-openroad-gc-cache-2eba27b2-offline01 --source-recheck /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-166-r-local-state/attempt728/TOOL_SOURCE_RECHECK.json'
