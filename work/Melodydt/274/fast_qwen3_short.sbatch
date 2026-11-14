#!/usr/bin/env bash
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"
sha256sum -c source.sha256
sha256sum -c upstream.sha256
r=/public/home/yuzelu/Melodydt/runs/issue-274
p=/public/home/yuzelu/project-circuit
a=$p/issue234-native-fixed-skip-request-H2gY5uiN
b=$a/source/project/experiments
t=$p/issue260-native-sram512-SMbOWTw6
j=$p/issue260-tlm-joint-9BiJdfEg
compat=$p/LLMHardwareDesign/issue-234-systemc-benchmark/python-compat-001
py=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python
bridge=/public/home/yuzelu/Melodydt/runs/issue-270/ffn-weight-05/tlm
model="${1:?model required}"
case "$model" in
qwen3)
    input=$p/LLMHardwareDesign/systemc-llm-issue153/sequence-qwen3-f4
    packed=$r/qwen3-pack-01/packed-114340
    reference=$r/reference-workloads-01/ref-114294/qwen3
    layers=28 ;;
llama)
    input=$r/llama-checkpoint-01/model
    packed=$r/pack-rest-01/packed-115021/llama
    reference=$r/reference-workloads-01/ref-114313/llama
    layers=16 ;;
phi)
    packed=$r/pack-rest-01/packed-115021/phi
    reference=$r/reference-workloads-01/ref-114294/phi
    input=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["checkpoint"])' "$reference/reference.json")
    layers=32 ;;
gemma)
    packed=$r/pack-rest-01/packed-115021/gemma
    reference=$r/reference-workloads-01/ref-114294/gemma
    input=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["checkpoint"])' "$reference/reference.json")
    layers=34 ;;
granite)
    packed=$r/pack-granite-02/packed-115035/granite
    reference=$r/reference-workloads-01/ref-114294/granite
    input=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["checkpoint"])' "$reference/reference.json")
    layers=32 ;;
falcon|qwen35)
    packed=$r/pack-rest-01/packed-115021/$model
    if [[ $model == qwen35 ]]; then packed=$r/pack-qwen35-02/packed-115110/qwen35; fi
    reference=$r/reference-workloads-01/ref-114294/$model
    input=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["checkpoint"])' "$reference/reference.json")
    layers=32 ;;
*) exit 2 ;;
esac
shift
out="$PWD/run-$SLURM_JOB_ID"
mkdir "$out"
pids=()
for mode in "$@"; do
    count=$layers
    if [[ $mode == pilot ]]; then mode=prefill; count=1; fi
    srun --exact -N1 -n1 -c "$SLURM_CPUS_PER_TASK" --cpu-bind=cores \
      /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu \
      /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif \
      env PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 LD_LIBRARY_PATH="$compat" \
      PYTHONPATH="$PWD:$bridge:$t:$j/systemc_benchmark:$j/block_local_native:$b/block_local_native:$b/mother_control_native:$b/shared_x_control:$a/algo1/project/experiments/block_synthesis" \
      "$py" -B fast_qwen3_short.py "$input" "$r/qwen3-gather-01/run-114290" "$packed" "$reference" \
      "$bridge/run-113164.dram.so" "$p/issue234-algo1-ffn-chain-20261112-01/DDR4-single-channel.ini" \
      "$out/$mode" --model "$model" --mode "$mode" --layers "$count" > "$out/$mode.log" 2>&1 &
    pids+=("$!")
done
status=0
for pid in "${pids[@]}"; do wait "$pid" || status=$?; done
find "$out" -type f ! -name output.sha256 -print0 | sort -z | xargs -0 sha256sum > "$out/output.sha256"
exit "$status"
