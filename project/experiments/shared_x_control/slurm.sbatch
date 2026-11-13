#!/bin/bash
#SBATCH --job-name=yl-250ctrl
#SBATCH --partition=c64
#SBATCH --nodes=1
#SBATCH --ntasks=6
#SBATCH --cpus-per-task=10
#SBATCH --time=00:10:00
#SBATCH --output=slurm-%j.out
set -euo pipefail
cd "${CONTROL_SOURCE_DIR:?pass --export=ALL,CONTROL_SOURCE_DIR=/absolute/source/directory}"
mkdir -p results
PYTHON_BIN=${PYTHON_BIN:-/usr/bin/python3.11}
"${PYTHON_BIN}" --version > results/python-version.txt
sha256sum contract.json private_s_candidate.json audit_protocol.py private_a_protocol.py run_audit.py slurm.sbatch > results/source.sha256
# User allocation policy is c64 6x10. These six independent protocol shards
# each use one Python process; report actual CPU, do not manufacture CPU load.
pids=()
for shard in 0 1 2 3 4 5; do
  srun --exclusive --ntasks=1 --cpus-per-task=10 \
    "${PYTHON_BIN}" -B run_audit.py --shard "${shard}" --shards 6 \
    --output "results/shard-${shard}.json" &
  pids+=("$!")
done
status=0
for task in "${pids[@]}"; do
  wait "${task}" || status=1
done
exit "${status}"
