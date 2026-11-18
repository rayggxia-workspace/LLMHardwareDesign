#!/bin/bash
#SBATCH -J yzl-289-C-joint
#SBATCH -p c96,c64
#SBATCH -N1
#SBATCH -n5
#SBATCH --nodelist=node22
#SBATCH -c8
#SBATCH --time=16:00:00
#SBATCH -o /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/c-joint-%j.log
set -u
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu
pids=()
for spec in '0 15' '0 30' '0 50' '20 15' '20 50';do
 read -r margin holdps <<< "$spec"
 srun --exclusive -N1 -n1 -c8 /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --env "OMP_NUM_THREADS=8,C_EXTRA_HOOKS=$C_EXTRA_HOOKS,C_EXTRA_RIP_HOOKS=$root/c-spacing-rip-v2.tcl,C_SPACING_RIP_LIST=$C_SPACING_RIP_LIST,C_ECO_SOURCE_ODB=$C_ECO_SOURCE_ODB,C_EXPECTED_ODB_SHA=$C_EXPECTED_ODB_SHA" /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash "$root/run-c-joint-v6.sh" "$margin" "$holdps" > "$root/c-joint-${SLURM_JOB_ID}-e${margin}-h${holdps}.log" 2>&1 &
 pids+=("$!")
done
rc=0
for p in "${pids[@]}";do wait "$p" || rc=1;done
exit "$rc"
