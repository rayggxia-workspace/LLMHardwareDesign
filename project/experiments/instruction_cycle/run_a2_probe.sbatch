#!/usr/bin/env bash
#SBATCH --job-name=zny-a2cycle
#SBATCH --partition=c64,c96
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --time=00:10:00
#SBATCH --output=slurm-%j.out
set -euo pipefail

root=$PWD
printf '%s  %s\n' 71c49b72ec70e74ef163e01bd333604adba9bc81bf7fb36ad6a085d106bf6c26 source.tar | sha256sum -c -
sha256sum -c probe.sha256
mkdir source
tar -xf source.tar -C source
image=/public/home/yuzelu/opt/eda/containers/orfs-26Q1.sif
verilator=/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator
sha256sum "$image" "$verilator" > tools.sha256
srun --exact -n1 -c "$SLURM_CPUS_PER_TASK" --cpu-bind=cores \
    /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv \
    --bind /public/home/yuzelu "$image" bash -s -- "$root" "$verilator" <<'RUN'
set -euo pipefail
cd "$1"
python3 --version > python-version.txt
"$2" --version > verilator-version.txt
python3 -B probe_a2.py --source source --out results --verilator "$2"
sha256sum results/a2/{single_signed,boundary_reuse_stall}/{mother.bin,local.bin,seed.bin,run.log} \
    results/a2/report.json results/heldout.log python-version.txt verilator-version.txt tools.sha256 > output.sha256
RUN
