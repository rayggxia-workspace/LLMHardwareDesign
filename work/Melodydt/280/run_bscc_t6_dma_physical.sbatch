#!/usr/bin/env bash
#SBATCH --job-name=mdt-280dma300
#SBATCH --partition=v6_384
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=12
#SBATCH --time=0
#SBATCH --output=slurm-%j.log
set -euo pipefail

if [[ ${1:-} != inside ]]; then
    bundle=${SLURM_SUBMIT_DIR:?}
    cd "$bundle"
    sha256sum -c physical-inputs.sha256
    image=$HOME/LLMHardware/opt/orfs-current-repacked.rootfs
    component=${1:-shared}
    # The site module initializer can read variables that are unset in batch jobs.
    set +u
    source /public3/soft/modules/module.sh
    module load singularity/3.7.0
    set -u
    exec srun --ntasks=1 --cpus-per-task="$SLURM_CPUS_PER_TASK" --cpu-bind=cores \
        singularity exec --cleanenv --bind "$bundle" "$image" \
        bash "$bundle/run_bscc_t6_dma_physical.sbatch" inside "$bundle" "$SLURM_JOB_ID" "$SLURM_CPUS_PER_TASK" "$component"
fi

bundle=$2
out=$bundle/physical-$3
cores=$4
mkdir "$out"
source /OpenROAD-flow-scripts/env.sh
case "$5" in
    shared)
        top=mc_dma_fabric_typed_p
        sources="$bundle/$top.sv"
        side=2000
        ;;
    phase)
        top=c639_dma_phase_ports
        python3 -B "$bundle/flatten_c639_dma_phase_ports.py" "$bundle/native_typed_dma_port.sv" "$out/$top.sv"
        sources="$bundle/native_typed_dma_port.sv $bundle/mc_dma_fabric_typed_p.sv $bundle/native_typed_dma_phase_mux.sv $out/$top.sv"
        side=2400
        ;;
    writeback)
        top=ffn_down_store_scope
        sources="$bundle/ffn_down_store_scope.sv $bundle/ffn_down_store.sv $bundle/s128_ddr64_store.sv"
        side=650
        ;;
    *) exit 2 ;;
esac
openroad -version > "$out/openroad-version.txt"
yosys -V > "$out/yosys-version.txt"
sha256sum "$(command -v openroad)" "$(command -v yosys)" > "$out/tool.sha256"
cat > "$out/config.mk" <<EOF
export PLATFORM = nangate45
export DESIGN_NAME = $top
export DESIGN_NICKNAME = $top
export SYNTH_HDL_FRONTEND = slang
export VERILOG_FILES = $sources
export SDC_FILE = $bundle/target.sdc
export DIE_AREA = 0 0 $side $side
export CORE_AREA = 10 10 $((side-10)) $((side-10))
export PLACE_DENSITY = 0.55
EOF
make -C /OpenROAD-flow-scripts/flow DESIGN_CONFIG="$out/config.mk" WORK_HOME="$out/flow" NUM_CORES="$cores" \
    finish > "$out/flow.log" 2>&1
key=nangate45/$top/base
cd "$out"
sha256sum config.mk tool.sha256 openroad-version.txt yosys-version.txt \
    "flow/results/$key/"6_final.{v,odb,sdc,spef} "flow/logs/$key/6_report.json" > physical.sha256
sha256sum -c physical.sha256
echo C639_SHARED_DMA_300_ARTIFACTS_READY
