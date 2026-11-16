#!/usr/bin/env bash
#SBATCH --job-name=yzl-m-leaf-unit
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
sha256sum "$image" /public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator /public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator_bin > tools.sha256
container=(/public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --env "SLURM_JOB_ID=$SLURM_JOB_ID,PYTHONDONTWRITEBYTECODE=1,OMP_NUM_THREADS=10" "$image")
srun --exact -n1 -c10 --cpu-bind=cores "${container[@]}" python3 -B "$root/source/project/experiments/w8a16_weight/codec.py" --source "$root/source" --out "$root/vectors" --check-model-sha > "$root/codec.log" 2>&1
srun --exact -n1 -c10 --cpu-bind=cores "${container[@]}" python3 -B "$root/source/project/experiments/w8a16_weight/leaf_vectors.py" "$root/vectors" > "$root/leaf-vectors.log" 2>&1
pids=()
for seed in 25011 25012 25013 25014 25015 25016; do
 srun --exact -n1 -c10 --cpu-bind=cores "${container[@]}" python3 -B "$root/source/project/experiments/w8a16_weight/leaf_check.py" --source "$root/source" --out "$root/leaf-seed-$seed" --vectors "$root/vectors" --seed "$seed" --jobs 10 --verilator /public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator > "$root/seed-$seed.log" 2>&1 &
 pids+=("$!")
done
failed=0
for pid in "${pids[@]}"; do wait "$pid" || failed=1; done
exit "$failed"
