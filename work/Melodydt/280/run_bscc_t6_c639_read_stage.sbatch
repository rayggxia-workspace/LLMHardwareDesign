#!/usr/bin/env bash
#SBATCH --job-name=mdt-280readstage
#SBATCH --partition=v6_384
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --time=0
#SBATCH --output=slurm-%j.log
set -euo pipefail

cd "${SLURM_SUBMIT_DIR:?}"
sha256sum --quiet -c inputs.sha256
out=stage-${SLURM_JOB_ID:?}
mkdir "$out"
python3 -B stage_c639_read_activity.py binding.json ../wave-audit/audit-38782228 "$out"
cd "$out"
sha256sum result.json */*/ports.vcd > results.sha256
sha256sum -c results.sha256
