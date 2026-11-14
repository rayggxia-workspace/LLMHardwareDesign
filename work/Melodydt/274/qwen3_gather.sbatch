#!/usr/bin/env bash
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"
sha256sum -c source.sha256
sha256sum -c upstream.sha256
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
p=/public/home/yuzelu/project-circuit
input=$p/LLMHardwareDesign/systemc-llm-issue153/sequence-qwen3-f4
a=$p/issue234-native-fixed-skip-request-H2gY5uiN
j=$p/issue260-tlm-joint-9BiJdfEg
b=$a/source/project/experiments
deps=$a/algo1/project/experiments/block_synthesis
replay=$p/issue260-native-sram512-SMbOWTw6
compat=$p/LLMHardwareDesign/issue-234-systemc-benchmark/python-compat-001
py=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python
out="$PWD/run-$SLURM_JOB_ID"
srun --exact -n1 -c "$SLURM_CPUS_PER_TASK" --cpu-bind=cores \
 /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu \
 /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif \
 env PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 LD_LIBRARY_PATH="$compat" \
 PYTHONPATH="$replay:$j/systemc_benchmark:$j/block_local_native:$b/block_local_native:$b/mother_control_native:$b/shared_x_control:$deps" \
 "$py" -B qwen3_gather.py "$input" "$j/dram-106937.so" \
 "$p/issue234-algo1-ffn-chain-20261112-01/DDR4-single-channel.ini" "$out"
find "$out" -type f ! -name output.sha256 -print0 |
    sort -z | xargs -0 sha256sum > "$out/output.sha256"
