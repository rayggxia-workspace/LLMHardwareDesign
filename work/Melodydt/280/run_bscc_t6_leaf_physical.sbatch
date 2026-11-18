#!/usr/bin/env bash
#SBATCH --job-name=mdt-280leaf
#SBATCH --partition=v6_384
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --time=0
#SBATCH --output=slurm-%j.log
set -euo pipefail

if [[ ${1:-} != inside ]]; then
    bundle=${SLURM_SUBMIT_DIR:?}
    cd "$bundle"
    sha256sum --quiet -c inputs.sha256
    opt=$HOME/LLMHardware/opt
    set +u
    source /public3/soft/modules/module.sh
    module load singularity/3.7.0
    set -u
    exec srun --ntasks=1 --cpus-per-task="$SLURM_CPUS_PER_TASK" --cpu-bind=cores \
        singularity exec --cleanenv --bind "$(dirname "$bundle")" "$opt/orfs-current-repacked.rootfs" \
        bash "$bundle/run_bscc_t6_leaf_physical.sbatch" inside "$bundle" "$SLURM_JOB_ID" "$SLURM_CPUS_PER_TASK" "${1:?leaf}"
fi

source /OpenROAD-flow-scripts/env.sh
bundle=$2
root=$(dirname "$bundle")
out=$bundle/physical-$3
project=$root/wide/wide-38772137/source/project
mkdir "$out"
capacity=4096
case "$5" in
    u-arith)
        top=e_s32_ap64
        sources=("$project/rtl/w8a16_v1/"{e_s32_ap64,e_s32_native}.sv)
        side=840
        ;;
    u-dispatch)
        top=s32_add_scope
        file="$project/rtl/block_local_native/$top.sv"
        # Use the parameters exercised by the source-bound ADD2 fixture.
        sed -e "s/SCHEMA=0, PROVIDER_ABI=0, TOPOLOGY=0/SCHEMA=32'd3, PROVIDER_ABI=32'd7, TOPOLOGY=32'd9/" \
            -e "s/OPERATION=0/OPERATION=16'd2/" "$file" > "$out/$top.sv"
        grep -Fq "SCHEMA=32'd3, PROVIDER_ABI=32'd7, TOPOLOGY=32'd9" "$out/$top.sv"
        grep -Fq "OPERATION=16'd2" "$out/$top.sv"
        sources=("$out/$top.sv")
        side=260
        ;;
    u-lane)
        top=projection_bias_e32_s128
        sources=("$project/rtl/block_local_native/$top.sv")
        side=150
        ;;
    lc-pm)
        top=lc_program_store_1k
        sources=("$project/experiments/shared_x_control/rtl/$top.sv")
        side=480
        capacity=8192
        ;;
    *) exit 2 ;;
esac
openroad -version > "$out/openroad-version.txt"
yosys -V > "$out/yosys-version.txt"
cat > "$out/config.mk" <<EOF
export PLATFORM = nangate45
export DESIGN_NAME = $top
export SYNTH_HDL_FRONTEND = slang
export SYNTH_MEMORY_MAX_BITS = $capacity
export VERILOG_FILES = ${sources[*]}
export SDC_FILE = $root/write-span/target.sdc
export DIE_AREA = 0 0 $side $side
export CORE_AREA = 10 10 $((side-10)) $((side-10))
export PLACE_DENSITY = 0.55
EOF
sha256sum "${sources[@]}" "$out/config.mk" > "$out/source.sha256"
make -C /OpenROAD-flow-scripts/flow DESIGN_CONFIG="$out/config.mk" WORK_HOME="$out/flow" \
    NUM_CORES="$4" finish > "$out/flow.log" 2>&1
key=nangate45/$top/base
cd "$out"
sha256sum source.sha256 openroad-version.txt yosys-version.txt "flow/results/$key/"6_final.{v,odb,sdc,spef} \
    "flow/logs/$key/6_report.json" "flow/reports/$key/5_route_drc.rpt" > physical.sha256
sha256sum -c physical.sha256
