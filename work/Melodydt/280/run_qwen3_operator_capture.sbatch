#!/usr/bin/env bash
#SBATCH --job-name=mdt-280q3op
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
original=$root/no-wire-extension-01/qwen3-38825995
out=$bundle/qwen3-$SLURM_JOB_ID
cd "$bundle"
sha256sum --quiet -c inputs.sha256
set +u
source /public3/soft/modules/module.sh
module load singularity/3.7.0
set -u
run() {
    srun --exact --ntasks=1 --cpus-per-task=12 --cpu-bind=cores \
        singularity exec --cleanenv --bind "$root" --bind "$prior/sourcefs:/public/home/yuzelu:ro" \
        "$HOME/LLMHardware/opt/orfs-current-repacked.rootfs" "$@"
}
(cd "$original" && sha256sum --quiet -c results.sha256)
run python3 -B "$bundle/prepare_qwen3_operator_capture.py" "$root" "$bundle" "$out"
run bash "$prior/run_bscc_t6_qwen3_dma.sbatch" inside prefill "$out" "$prior" > "$out/prefill.log" 2>&1 &
pre=$!
run bash "$prior/run_bscc_t6_qwen3_dma.sbatch" inside decode "$out" "$prior" > "$out/decode.log" 2>&1 &
dec=$!
status=0
wait "$pre" || status=$?
wait "$dec" || status=$?
[[ $status == 0 ]] || exit "$status"
run bash "$prior/run_bscc_t6_qwen3_dma.sbatch" inside audit "$out" "$prior"
run python3 -B "$root/no-wire-extension-01/prepare_ordinary_m.py" audit "$bundle" "$original" "$out"
for phase in prefill decode-live; do
    run python3 -B "$bundle/verify_arithmetic_capture.py" "$out/$phase-w4-tile128-pr272-combined/arithmetic-observation.json"
    run env PYTHONPATH="$out/runner:$root/m-product/wide-38792112/source/project/experiments/native_s32_n" python3 -B "$bundle/verify_operator_capture.py" "$out/$phase-w4-tile128-pr272-combined/operator-observation.json"
done
cd "$out"
sha256sum capture-provenance.json operator-provenance.json instrumented-source.json acceptance.json dma-windows.json \
    {prefill,decode-live}-w4-tile128-pr272-combined/{result,arithmetic-observation,arithmetic-capture-check,operator-observation,operator-capture-check}.json > results.sha256
sha256sum --quiet -c results.sha256
echo QWEN3_OPERATOR_CAPTURE_ACCEPTED
