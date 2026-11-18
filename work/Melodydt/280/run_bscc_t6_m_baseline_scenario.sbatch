#!/usr/bin/env bash
#SBATCH --job-name=mdt-280mbasecase
#SBATCH --partition=v6_384
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --time=0
#SBATCH --output=slurm-%j.log
set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?}"
sha256sum --quiet -c scenario-inputs.sha256
active=m-${1:?baseline power job}
idle=idle-${2:?idle power job}
out=scenario-${SLURM_JOB_ID:?}
(cd "$active" && sha256sum --quiet -c results.sha256)
(cd "$idle" && sha256sum --quiet -c results.sha256)
mkdir "$out"
python3 -B qwen3_m_baseline_scenario.py ../independent-rollup/rollup-38782605.json \
    "$active/baseline-power.json" "$idle/power/receipt.json" "$out/qwen3-m-reference.json"
sha256sum "$out/qwen3-m-reference.json" > "$out/results.sha256"
sha256sum -c "$out/results.sha256"
