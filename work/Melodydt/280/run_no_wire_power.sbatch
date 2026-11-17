#!/usr/bin/env bash
#SBATCH --job-name=mdt-280nowire
#SBATCH --partition=v6_384
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=12
#SBATCH --time=0
#SBATCH --output=slurm-%j.log
set -euo pipefail
if [[ ${1:-} != inside ]]; then
  bundle=${SLURM_SUBMIT_DIR:?}
  cd "$bundle"
  sha256sum --quiet -c inputs.sha256
  set +u
  source /public3/soft/modules/module.sh
  module load singularity/3.7.0
  set -u
  exec srun --ntasks=1 --cpus-per-task="$SLURM_CPUS_PER_TASK" --cpu-bind=cores \
    singularity exec --cleanenv --bind "$(dirname "$bundle")" \
    "$HOME/LLMHardware/opt/orfs-current-repacked.rootfs" \
    bash "$bundle/run_no_wire_power.sbatch" inside "$bundle" "$SLURM_JOB_ID" "$SLURM_CPUS_PER_TASK" "$@"
fi
source /OpenROAD-flow-scripts/env.sh
bundle=$2
out=$bundle/run-$3-${5:?family}
mkdir "$out"
openroad -version > "$out/openroad-version.txt"
python3 --version > "$out/python-version.txt"
sha256sum "$(command -v openroad)" "$bundle/inputs.sha256" "$bundle/source-commit.txt" > "$out/tools.sha256"
python3 -B "$bundle/no_wire_power.py" "$(dirname "$bundle")" "$out" "$5" --workers "$(( $4 / 3 ))"
cd "$out"
sha256sum calibration.json */receipt.json tools.sha256 openroad-version.txt python-version.txt > results.sha256
sha256sum -c results.sha256
