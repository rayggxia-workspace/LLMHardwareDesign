#!/bin/bash
#SBATCH -J yzl-289-C-native
#SBATCH -p c96,c64
#SBATCH -N1
#SBATCH -n2
#SBATCH -c8
#SBATCH --time=16:00:00
#SBATCH -o /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/c-native-%j.log
set -u
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu
pids=()
for clock in 2 4;do
 srun --exclusive -N1 -n1 -c8 /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --env OMP_NUM_THREADS=8 /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash "$root/run-c-native-probe.sh" "$clock" > "$root/c-native-${SLURM_JOB_ID}-clock${clock}.log" 2>&1 &
 pids+=("$!")
done
rc=0
for p in "${pids[@]}";do wait "$p" || rc=1;done
exit "$rc"