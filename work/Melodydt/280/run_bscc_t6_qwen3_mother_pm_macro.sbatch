#!/usr/bin/env bash
#SBATCH --job-name=mdt-280pmmacro
#SBATCH --partition=v6_384
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=9
#SBATCH --time=0
#SBATCH --output=slurm-%j.log
set -euo pipefail
if [[ ${1:-} != inside ]]; then
    bundle=${SLURM_SUBMIT_DIR:?}
    cd "$bundle"
    sha256sum --quiet -c inputs.sha256
    opt=$HOME/LLMHardware/opt
    set +u
    source /public3/soft/modules/module.sh
    module load singularity/3.7.0
    set -u
    exec srun --ntasks=1 --cpus-per-task="$SLURM_CPUS_PER_TASK" --cpu-bind=cores \
        singularity exec --cleanenv --bind "$(dirname "$bundle")" --bind "$opt" \
        "$opt/orfs-current-repacked.rootfs" bash "$bundle/run_bscc_t6_qwen3_mother_pm_macro.sbatch" \
        inside "$bundle" "$SLURM_JOB_ID" "$SLURM_CPUS_PER_TASK"
fi

source /OpenROAD-flow-scripts/env.sh
bundle=$2
root=$(dirname "$bundle")
out=$bundle/result-$3
incoming=$root/incoming/macro-views
waves=$root/pm-real-length/pm-38795749
physical=$incoming/mother128/physical
bank=$incoming/source/issue-155/bank-views-011/generation/bank/s_sram_256x128_freepdk45_TT_1p1V_25C.lib
(cd "$incoming/source" && sha256sum --quiet -c ../source-files.sha256)
(cd "$incoming/mother128" && sha256sum --quiet -c ../mother-subset.sha256)
(cd "$waves" && sha256sum --quiet -c results.sha256)
mkdir "$out"
python3 -B "$bundle/qwen3_mother_pm_power.py" "$waves" "$physical" "$bank" "$out" --cores "$4"
cd "$out"
sha256sum "$bundle/inputs.sha256" "$incoming"/{source-files,mother-subset}.sha256 "$waves/results.sha256" \
    */{power.log,power.tcl} mother-pm-macro-power.json > results.sha256
sha256sum -c results.sha256
