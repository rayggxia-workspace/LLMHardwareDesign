#!/bin/bash
#SBATCH --job-name=yzl-sc153-expert-residuals
#SBATCH --partition=c64
#SBATCH --nodelist=node1
#SBATCH --cpus-per-task=8
#SBATCH --time=01:00:00
set -euo pipefail
ROOT=/public/home/yuzelu/project-circuit/LLMHardwareDesign/systemc-llm-issue153
REV=${1:-r32}
cd "$ROOT"
mkdir "src-$REV"
tar -xzf "systemc-src-$REV.tar.gz" -C "src-$REV"
cmake -S "src-$REV/project/systemc" -B "build-$REV" -DCMAKE_PREFIX_PATH="$ROOT/install" -DCMAKE_BUILD_TYPE=Release
cmake --build "build-$REV" -j8
ctest --test-dir "build-$REV" --output-on-failure
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 SLURM_CPUS_PER_TASK=1 PYTHONDONTWRITEBYTECODE=1
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 LLM_PRECISE_ADAPTER=1
export ROOT REV
PY=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python
export PY
CP="granite-residual-$REV"
"$PY" "src-$REV/project/systemc/llm/tools/export_expert_residuals.py" "$ROOT/granite-g8-r28" "$ROOT/$CP"
export CP
printf '%s\n' systemc oracle | xargs -n1 -P2 bash -c '
 set -euo pipefail
 if [ "$0" = systemc ];then
  RUN="run-granite-$REV";mkdir "$RUN"
  sha256sum "systemc-src-$REV.tar.gz" "build-$REV/llm_bench" "$CP/metadata.txt" "$CP/weights.index" "$CP/weights.scales" > "$RUN/run-inputs.sha256"
  "build-$REV/llm_bench" "$ROOT/$CP" "$ROOT/$RUN" > "logs/run-granite-$REV.log" 2>&1
  "$PY" "src-$REV/project/systemc/llm/tools/validate_inference.py" "$ROOT/$CP" "$ROOT/$RUN" >> "logs/run-granite-$REV.log" 2>&1
 else
  RUN="oracle-granite-$REV";mkdir "$RUN"
  ln -s "$ROOT/run-granite-r31/systemc_receipt.json" "$RUN/systemc_receipt.json"
  "$PY" "src-$REV/project/systemc/llm/tools/diagnose_quantized_model.py" "$ROOT/$CP" "$ROOT/$RUN" > "logs/oracle-granite-$REV.log" 2>&1
 fi
'
