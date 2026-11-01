#!/bin/bash
#SBATCH --job-name=yzl-sc153-staticprep
#SBATCH --partition=c64
#SBATCH --nodelist=node3
#SBATCH --cpus-per-task=8
#SBATCH --time=01:00:00
set -euo pipefail
ROOT=/public/home/yuzelu/project-circuit/LLMHardwareDesign/systemc-llm-issue153
cd "$ROOT";export ROOT
mkdir src-f14;tar -xzf systemc-src-f14.tar.gz -C src-f14
cmake -S src-f14/project/systemc -B build-f14 -DCMAKE_PREFIX_PATH="$ROOT/install" -DCMAKE_BUILD_TYPE=Release
cmake --build build-f14 -j8
ctest --test-dir build-f14 --output-on-failure
sha256sum systemc-src-f14.tar.gz build-f14/llm_bench
printf '%s\n' gemma falcon | xargs -n1 -P2 bash -c '
 set -euo pipefail
 export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 SLURM_CPUS_PER_TASK=1 PYTHONDONTWRITEBYTECODE=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
 PY=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python
 MODEL=$0;TOOLS="$ROOT/src-f14/project/systemc/llm/tools"
 exec >"logs/static-parameter-$MODEL-f14.log" 2>&1
 if [[ "$MODEL" == gemma ]];then OLD=sequence-gemma-f7;else OLD=sequence-falcon-f8;fi
 "$PY" "$TOOLS/requantize_parameters.py" "$ROOT/$OLD" "$ROOT/sequence-$MODEL-f14"
 sha256sum systemc-src-f14.tar.gz "$TOOLS/requantize_parameters.py" "$TOOLS/diagnose_quantized_model.py" "sequence-$MODEL-f14/weights.bin" "sequence-$MODEL-f14/parameters.scales" "sequence-$MODEL-f14/export_receipt.json" > "sequence-diagnostic-$MODEL-static-f14.inputs.sha256"
 "$PY" "$TOOLS/diagnose_quantized_model.py" "$ROOT/sequence-$MODEL-f14" "$ROOT/run-$MODEL-f4-sequence" --out "$ROOT/sequence-diagnostic-$MODEL-static-f14.json"
'
