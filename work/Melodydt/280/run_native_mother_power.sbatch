#!/usr/bin/env bash
#SBATCH --job-name=mdt-280mc-nowire
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
      bash "$bundle/run_native_mother_power.sbatch" inside "$bundle" "$SLURM_JOB_ID"
fi
source /OpenROAD-flow-scripts/env.sh
bundle=$2
out=$bundle/run-$3
mkdir "$out"
yosys -V > "$out/yosys-version.txt"
openroad -version > "$out/openroad-version.txt"
python3 --version > "$out/python-version.txt"
sha256sum "$(command -v yosys)" "$(command -v openroad)" "$bundle/inputs.sha256" "$bundle/source-commit.txt" > "$out/tools.sha256"
python3 -B "$bundle/synth_native_mother_power.py" "$(dirname "$bundle")" "$out"
cd "$out"
sha256sum calibration.json mapped.v mapped.json tools.sha256 *version.txt */power.log > results.sha256
sha256sum --quiet -c results.sha256
