#!/usr/bin/env bash
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"
sha256sum -c source.sha256
sha256sum -c upstream.sha256
root=/public/home/yuzelu/Melodydt/runs/issue-274
base=/public/home/yuzelu/project-circuit
a=$base/issue234-native-fixed-skip-request-H2gY5uiN
b=$a/source/project/experiments
j=$base/issue260-tlm-joint-9BiJdfEg
r=$base/issue260-native-sram512-SMbOWTw6
py=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python
compat=$base/LLMHardwareDesign/issue-234-systemc-benchmark/python-compat-001
input=$base/LLMHardwareDesign/systemc-llm-issue153/sequence-qwen3-f4
test "${1:-}" = pilot && modes=(prefill:1) || modes=(prefill:28 decode:28)
out="$PWD/run-$SLURM_JOB_ID"
mkdir "$out"
pids=()
for entry in "${modes[@]}"; do
    mode=${entry%:*}
    layers=${entry#*:}
    srun --exact -N1 -n1 -c "$SLURM_CPUS_PER_TASK" --cpu-bind=cores \
      /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu \
      /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif \
      env PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 LD_LIBRARY_PATH="$compat" \
      PYTHONPATH="$PWD:$r:$j/systemc_benchmark:$j/block_local_native:$b/block_local_native:$b/mother_control_native:$b/shared_x_control:$a/algo1/project/experiments/block_synthesis" \
      "$py" -B qwen3_short.py "$input" "$root/qwen3-gather-01/run-114290" \
      "$root/qwen3-pack-01/packed-114340" "$root/reference-workloads-01/ref-114294/qwen3" \
      "$j/dram-106937.so" "$base/issue234-algo1-ffn-chain-20261112-01/DDR4-single-channel.ini" \
      "$out/$mode" --mode "$mode" --layers "$layers" > "$out/$mode.log" 2>&1 &
    pids+=("$!")
done
status=0
for pid in "${pids[@]}"; do wait "$pid" || status=$?; done
find "$out" -type f ! -name output.sha256 -print0 | sort -z | xargs -0 sha256sum > "$out/output.sha256"
exit "$status"
