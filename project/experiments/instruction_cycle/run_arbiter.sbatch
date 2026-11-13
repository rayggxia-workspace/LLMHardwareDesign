#!/usr/bin/env bash
#SBATCH --job-name=zny-cycle
#SBATCH --partition=c64,c96
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --time=00:10:00
#SBATCH --output=slurm-%j.out
set -euo pipefail

root=$PWD
sha256sum -c source.sha256
image=/public/home/yuzelu/opt/eda/containers/orfs-26Q1-repacked.sif
verilator=/public/home/yuzelu/opt/eda/verilator-5-042-repro02/bin/verilator
sha256sum "$image" "$verilator" > tools.sha256
srun --exact -n1 -c "$SLURM_CPUS_PER_TASK" --cpu-bind=cores \
    /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv \
    --bind /public/home/yuzelu "$image" bash -s -- "$root" "$verilator" "$SLURM_CPUS_PER_TASK" <<'RUN'
set -euo pipefail
cd "$1"
"$2" --version > verilator-version.txt
"$2" --binary --timing -Wno-TIMESCALEMOD --top-module arbiter_tb -j "$3" \
    block_local_s_arbiter.sv arbiter_tb.sv > build.log 2>&1
for scenario in 0 1; do
    ./obj_dir/Varbiter_tb +CASE="$scenario" > "rtl-$scenario.log"
done
sha256sum rtl-0.log rtl-1.log verilator-version.txt build.log tools.sha256 > output.sha256
RUN
