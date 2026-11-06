#!/usr/bin/env bash
#SBATCH --job-name=mdt-fchain179
#SBATCH --partition=debug
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --time=00:20:00
#SBATCH --output=slurm-%j.log
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"
root="$(dirname "$PWD")"
printf 'START %s host=%s job=%s cpus=%s\n' "$(date -Is)" "$(hostname)" "$SLURM_JOB_ID" "$SLURM_CPUS_PER_TASK"
git -C source rev-parse HEAD
sha256sum source.tar
mkdir -p "$root/container-cache" "$root/tmp"
module load singularity/4.3.4
export SINGULARITY_CACHEDIR="$root/container-cache"
export SINGULARITY_TMPDIR="$root/tmp"
singularity exec --cleanenv --containall --bind /public/home/yuzelu/opt/eda:/eda:ro \
  --bind "$PWD:/work" --pwd /work/source /public/home/yuzelu/opt/eda/containers/orfs-26Q1.sif /bin/bash -c '
set -euo pipefail
verilator=/eda/verilator-5.042/bin/verilator
export SLURM_CPUS_PER_TASK=4
mkdir -p /work/results
python3 -B project/control_r4_v0_1/check_contract.py > /work/results/r4-static.json
(
  python3 -B project/control_p_compute_v0_1/run_handoff.py --f-store --verilator "$verilator" --out /work/results/f-chain &&
  python3 -B project/control_p_compute_v0_1/run_handoff.py --verilator "$verilator" --out /work/results/p-chain
) &
chain_pid=$!
(
  python3 -B project/control_f_compute_v0_1/run_f.py --verilator "$verilator" --out /work/results/f &&
  python3 -B project/control_u_compute_v0_1/run_u.py --verilator "$verilator" --out /work/results/u &&
  python3 -B project/control_j_compute_v0_1/run_j.py --verilator "$verilator" --out /work/results/j &&
  python3 -B project/control_c_compute_v0_1/run_c.py --verilator "$verilator" --out /work/results/c &&
  python3 -B project/control_p_compute_v0_1/run_a2.py --silu --verilator "$verilator" --out /work/results/p-silu &&
  python3 -B project/control_p_compute_v0_1/run_a2.py --verilator "$verilator" --out /work/results/p-raw
) &
reg_pid=$!
chain_rc=0; reg_rc=0
wait "$chain_pid" || chain_rc=$?
wait "$reg_pid" || reg_rc=$?
printf "RESULT chain=%s regression=%s\n" "$chain_rc" "$reg_rc"
test "$chain_rc" = 0 && test "$reg_rc" = 0
'
printf 'PASS %s\n' "$(date -Is)"
