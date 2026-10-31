#!/bin/bash
#SBATCH --job-name=yzl-bv2-rhelp
#SBATCH --partition=c96
#SBATCH --cpus-per-task=16
#SBATCH --time=00:10:00
set -euo pipefail
base=/public/home/yuzelu/project-circuit/llm_routing_analysis/worktrees/issue143-seven-block-v2-20261030
out=$base/outputs/044
test ! -e "$out"
mkdir "$out"
image=/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif
read -r actual _ < <(sha256sum "$image")
test "$actual" = 49eae8b526c6eec806473b13db5d98f848424f38de9fa3430e8ce8e157144f3a
cp "$base/r-native-help.tcl" "$out/"
sha256sum "$out/r-native-help.tcl" "$base/r-native-help.sh" > "$out/inputs.sha256"
srun --ntasks=1 --cpus-per-task=16 --cpu-bind=cores \
 /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu \
 --pwd "$out" "$image" bash -c 'source /OpenROAD-flow-scripts/env.sh; exec openroad -no_init -exit r-native-help.tcl' \
 > "$out/native-help.log" 2>&1
sha256sum "$out/native-help.log" > "$out/outputs.sha256"
