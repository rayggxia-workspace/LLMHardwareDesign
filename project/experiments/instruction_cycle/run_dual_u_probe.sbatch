#!/usr/bin/env bash
#SBATCH --job-name=zny-dualu
#SBATCH --partition=c64,c96
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --time=00:10:00
#SBATCH --output=slurm-%j.out
set -euo pipefail

root=$PWD
sha256sum -c probe.sha256
image=/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif
verilator=/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator
sha256sum "$image" "$verilator" > tools.sha256
srun --exact -n1 -c "$SLURM_CPUS_PER_TASK" --cpu-bind=cores \
    /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv \
    --bind /public/home/yuzelu --env "SLURM_CPUS_PER_TASK=$SLURM_CPUS_PER_TASK" "$image" \
    bash -s -- "$root" "$verilator" <<'RUN'
set -euo pipefail
export LC_ALL=C PYTHONDONTWRITEBYTECODE=1
cd "$1"
python3 --version > python-version.txt
"$2" --version > verilator-version.txt
python3 -B probe_dual_u.py --root "$PWD" --verilator "$2"
sha256sum results/dual_u/{normal,stalled,heldout}.log results/dual_u/tb_native_pair.sv \
    results/dual_u/compile.log results/dual_u/probe-report.json \
    python-version.txt verilator-version.txt tools.sha256 > output.sha256
RUN
