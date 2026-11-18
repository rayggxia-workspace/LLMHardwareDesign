#!/usr/bin/env bash
#SBATCH --job-name=mdt-280bind
#SBATCH --partition=v6_384
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=12
#SBATCH --time=0
#SBATCH --output=slurm-%j.log
set -euo pipefail
if [[ ${1:-} != inside ]]; then
    bundle=${SLURM_SUBMIT_DIR:?}
    root=$(dirname "$bundle")
    cd "$bundle"
    sha256sum --quiet -c deployment-inputs.sha256
    unset TCL_LIBRARY TK_LIBRARY TCLLIBPATH
    exec srun --ntasks=1 --cpus-per-task=12 --cpu-bind=cores /public3/soft/singularity/3.7.0/bin/singularity exec --cleanenv \
      --bind "$root" --bind "$root/replay/sourcefs:/public/home/yuzelu:ro" \
      --bind "$root/six-model-energy-01/sourcefs/Melodydt/runs/issue-274:/public/home/yuzelu/Melodydt/runs/issue-274:ro" \
      "$HOME/LLMHardware/opt/orfs-current-repacked.rootfs" bash "$bundle/run_deployment.sbatch" inside "$bundle" "$SLURM_JOB_ID" "$@"
fi
bundle=$2 job=$3 source=$4 variant=$5 phase=$6
root=$(dirname "$bundle")
out=$bundle/deployment-$job-$variant-$phase
legacy=/public/home/yuzelu
p=$legacy/project-circuit
a=$p/issue234-native-fixed-skip-request-H2gY5uiN
experiments=$a/source/project/experiments
joint=$p/issue260-tlm-joint-9BiJdfEg
export PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
export PYTHONPATH="$out/runner:$legacy/Melodydt/runs/issue-270/ffn-weight-05/tlm:$p/issue260-native-sram512-SMbOWTw6:$joint/systemc_benchmark:$joint/block_local_native:$experiments/block_local_native:$experiments/mother_control_native:$experiments/shared_x_control:$a/algo1/project/experiments/block_synthesis"
python3 -B "$bundle/prepare_deployment.py" "$source" "$bundle" "$out" "$variant"
export SHORT_PROJECTION_MATH="$out/projection_math.so"
export QWEN3_COMPONENT_WINDOWS="$out/qualified-windows.json"
baseline=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["baseline"][sys.argv[2]])' "$out/transfer-verified.json" "$phase")
python3 -B "$out/runner/run_frozen_model_energy.py" "$baseline" "$root/component-observation/replay-38782605/ddr-dma-probe.so" \
  "$p/issue234-algo1-ffn-chain-20261112-01/DDR4-single-channel.ini" "$out/result" > "$out/run.log" 2>&1
cd "$out"
sha256sum provenance.json result/{acceptance,result,component-observation,deployment-observation,ddr-window-energy,dma-windows}.json result/deployment-events.jsonl.gz > results.sha256
sha256sum --quiet -c results.sha256
echo DEPLOYMENT_ACCEPTED
