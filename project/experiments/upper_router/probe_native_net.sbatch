#!/usr/bin/env bash
#SBATCH --job-name=yzl-native-net
#SBATCH --partition=c64
#SBATCH --cpus-per-task=10
#SBATCH --time=0
set -euo pipefail
task=$1;root=$2
srun --exact --ntasks=1 --cpus-per-task=10 --cpu-bind=cores /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --pwd "$task/source" --env OMP_NUM_THREADS=10 /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash -c '
set -euo pipefail
source /OpenROAD-flow-scripts/env.sh
task=$1;root=$2;r=project/experiments/upper_router
export ROUTER_PROBE_ODB=$root/attempt01/packages/P/native/6_final.odb ROUTER_PROBE_OUT=$task/source.tsv ROUTER_PROBE_NET=clknet_2_0_0_clk
openroad -no_init -threads 10 -exit "$r/probe_native_net.tcl" > "$task/source.log" 2>&1
export ROUTER_PROBE_ODB=$root/attempt37/flat/assembled.odb ROUTER_PROBE_OUT=$task/actual.tsv ROUTER_PROBE_NET=P0/clknet_2_0_0_clk
openroad -no_init -threads 10 -exit "$r/probe_native_net.tcl" > "$task/actual.log" 2>&1
' bash "$task" "$root"
