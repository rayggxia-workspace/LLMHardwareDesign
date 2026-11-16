#!/bin/bash
#SBATCH --job-name=yl-250MCsize
#SBATCH --partition=c64
#SBATCH --nodes=1
#SBATCH --ntasks=6
#SBATCH --cpus-per-task=10
#SBATCH --time=00:05:00
#SBATCH --output=slurm-%j.out
set -euo pipefail
cd "${CONTROL_SOURCE_DIR:?}"
mkdir -p results
sha256sum project/experiments/mother_control_native/audit_wholegraph_capacity.py inputs/wholegraph-scopes.json > results/source.sha256
srun --exclusive --ntasks=1 --cpus-per-task=10 /usr/bin/python3.11 -B \
  project/experiments/mother_control_native/audit_wholegraph_capacity.py \
  --input inputs/wholegraph-scopes.json --out results/wholegraph-capacity.json > results/audit.log
