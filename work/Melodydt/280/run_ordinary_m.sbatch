#!/usr/bin/env bash
#SBATCH --job-name=mdt-280qwen-m
#SBATCH --partition=v6_384
#SBATCH --nodes=1
#SBATCH --ntasks=2
#SBATCH --cpus-per-task=12
#SBATCH --time=0
#SBATCH --output=slurm-%j.log
set -euo pipefail
bundle=${SLURM_SUBMIT_DIR:?}
root=$(dirname "$bundle")
prior=$root/component-observation
shared=$prior/replay-38782605
out=$bundle/qwen3-$SLURM_JOB_ID
cd "$bundle"
sha256sum --quiet -c inputs.sha256
mkdir "$out"
set +u
source /public3/soft/modules/module.sh
module load singularity/3.7.0
set -u
run() {
  srun --exact --ntasks=1 --cpus-per-task=12 --cpu-bind=cores \
    singularity exec --cleanenv --bind "$root" --bind "$prior/sourcefs:/public/home/yuzelu:ro" \
      "$HOME/LLMHardware/opt/orfs-current-repacked.rootfs" "$@"
}
run python3 -B "$bundle/prepare_ordinary_m.py" prepare "$bundle" "$shared" "$out"
run bash "$prior/run_bscc_t6_qwen3_dma.sbatch" inside prefill "$out" "$prior" > "$out/prefill.log" 2>&1 &
pre=$!
run bash "$prior/run_bscc_t6_qwen3_dma.sbatch" inside decode "$out" "$prior" > "$out/decode.log" 2>&1 &
dec=$!
status=0
wait "$pre" || status=$?
wait "$dec" || status=$?
[[ $status == 0 ]] || exit "$status"
run bash "$prior/run_bscc_t6_qwen3_dma.sbatch" inside audit "$out" "$prior"
run python3 -B "$bundle/prepare_ordinary_m.py" audit "$bundle" "$shared" "$out"
cd "$out"
sha256sum "$bundle/inputs.sha256" "$bundle/source-commit.txt" runner/*.py \
  acceptance.json dma-windows.json {prefill,decode-live}-w4-tile128-pr272-combined/{result,component-observation}.json > results.sha256
sha256sum --quiet -c results.sha256
