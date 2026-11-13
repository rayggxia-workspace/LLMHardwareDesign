#!/usr/bin/env bash
#SBATCH --job-name=yzl-gcopy-a
#SBATCH --partition=c64
#SBATCH --ntasks=6
#SBATCH --cpus-per-task=10
#SBATCH --nodes=1
#SBATCH --time=0
set -euo pipefail
root=$SLURM_SUBMIT_DIR
cd "$root/source"
sha256sum -c "$root/source.sha256" > "$root/source-check.log"
cd "$root"
scontrol show job "$SLURM_JOB_ID" > allocation.txt
image=/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif
sha256sum "$image" \
 /public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator \
 /public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator_bin > tools.sha256
pids=()
for seed in 25001 25002 25003 25004 25005 25006; do
 srun --exact -n1 -c10 --cpu-bind=cores \
 /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv \
 --bind /public/home/yuzelu --env "SLURM_JOB_ID=$SLURM_JOB_ID,PYTHONDONTWRITEBYTECODE=1,OMP_NUM_THREADS=10" \
 "$image" python3 -B "$root/source/project/experiments/block_local_native/check_g_quant_copy_a.py" \
 --source "$root/source" --out "$root/seed-$seed" --seed "$seed" \
 --verilator /public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator \
 > "$root/seed-$seed.log" 2>&1 &
 pids+=("$!")
done
failed=0
for pid in "${pids[@]}"; do wait "$pid" || failed=1; done
exit "$failed"
