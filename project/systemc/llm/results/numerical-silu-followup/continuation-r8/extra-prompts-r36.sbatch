#!/bin/bash
#SBATCH --job-name=yzl-sc153-extra-prompts
#SBATCH --partition=c64
#SBATCH --nodelist=node1
#SBATCH --cpus-per-task=2
#SBATCH --time=00:30:00
set -euo pipefail
ROOT=/public/home/yuzelu/project-circuit/LLMHardwareDesign/systemc-llm-issue153
MODE=${1:?prepare or run}
export ROOT MODE
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 SLURM_CPUS_PER_TASK=1 PYTHONDONTWRITEBYTECODE=1
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 LLM_PRECISE_ADAPTER=1 LLM_BLOCK_SCALES=1 LLM_ACCURATE_SILU=1
PY=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python
export PY
cd "$ROOT"
printf '%s\n' qwen25 granite | xargs -n1 -P2 bash -c '
 set -euo pipefail
 MODEL=$0;CP="$MODEL-extra-r36";OLD=qwen25-r2
 if [ "$MODEL" = granite ];then OLD=granite-residual-r32;fi
 if [ "$MODE" = prepare ];then
  "$PY" src-r35/project/systemc/llm/tools/prepare_prompt_case.py "$ROOT/$OLD" "$ROOT/$CP" --prompt 1 > "logs/prepare-$CP.log" 2>&1
 elif [ "$MODE" = run ];then
  RUN="run-$CP";mkdir "$RUN"
  sha256sum systemc-src-r35.tar.gz build-r35/llm_bench "$CP/metadata.txt" "$CP/weights.index" > "$RUN/run-inputs.sha256"
  if [ -e "$CP/weights.scales" ];then sha256sum "$CP/weights.scales" >> "$RUN/run-inputs.sha256";fi
  build-r35/llm_bench "$ROOT/$CP" "$ROOT/$RUN" > "logs/$RUN.log" 2>&1
  "$PY" src-r35/project/systemc/llm/tools/validate_inference.py "$ROOT/$CP" "$ROOT/$RUN" >> "logs/$RUN.log" 2>&1
 else exit 2;fi
'
