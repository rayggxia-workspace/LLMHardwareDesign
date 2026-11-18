#!/usr/bin/env bash
#SBATCH --job-name=mdt-280op-check
#SBATCH --partition=v6_384
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=12
#SBATCH --time=0
#SBATCH --output=slurm-%j.log
set -euo pipefail
bundle=${SLURM_SUBMIT_DIR:?}
root=$(dirname "$bundle")
cd "$bundle"
sha256sum --quiet -c inputs.sha256
set +u
source /public3/soft/modules/module.sh
module load singularity/3.7.0
set -u
out=$bundle/preflight-$SLURM_JOB_ID
mkdir "$out"
for item in 38820601-llama 38820602-granite 38820798-phi 38821513-gemma 38821601-qwen35 38821511-falcon; do
    srun --ntasks=1 --cpus-per-task=12 --cpu-bind=cores singularity exec --cleanenv --bind "$root" \
        --bind "$root/replay/sourcefs:/public/home/yuzelu:ro" \
        --bind "$root/six-model-energy-01/sourcefs/Melodydt/runs/issue-274:/public/home/yuzelu/Melodydt/runs/issue-274:ro" \
        "$HOME/LLMHardware/opt/orfs-current-repacked.rootfs" \
        bash "$bundle/run_operator_capture.sbatch" inside prepare "$root/six-model-energy-01/run-$item" "$out/$item" "$bundle" "$root"
done
echo OPERATOR_PREFLIGHT_PASS
