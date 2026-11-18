#!/usr/bin/env bash
#SBATCH --job-name=mdt-280nw-legacy
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
  exec srun --ntasks=1 --cpus-per-task=12 --cpu-bind=cores \
    singularity exec --cleanenv --bind "$(dirname "$bundle")" \
      "$HOME/LLMHardware/opt/orfs-current-repacked.rootfs" \
      bash "$bundle/run_no_wire_legacy.sbatch" inside "$bundle" "$SLURM_JOB_ID"
fi
source /OpenROAD-flow-scripts/env.sh
bundle=$2
out=$bundle/run-$3
mkdir "$out"
openroad -version > "$out/openroad-version.txt"
sha256sum "$(command -v openroad)" "$bundle/inputs.sha256" "$bundle/source-commit.txt" "$bundle/transfer.json" > "$out/tools.sha256"
python3 -B "$bundle/no_wire_power.py" "$(dirname "$bundle")" "$out" legacy --workers 4
python3 -B "$bundle/mother_macro_no_wire.py" "$(dirname "$bundle")" "$out/mother-pm"
cd "$out"
sha256sum calibration.json */receipt.json mother-pm/mother-pm-macro-power.json tools.sha256 openroad-version.txt > results.sha256
sha256sum --quiet -c results.sha256
