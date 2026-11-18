#!/usr/bin/env bash
#SBATCH --job-name=mdt-280sramgate
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
    sha256sum --quiet -c inputs.sha256
    variant=${1:-both}
    opt=$HOME/LLMHardware/opt
    set +u
    source /public3/soft/modules/module.sh
    module load singularity/3.7.0
    set -u
    exec srun --ntasks=1 --cpus-per-task="$SLURM_CPUS_PER_TASK" --cpu-bind=cores \
        singularity exec --cleanenv --bind "$(dirname "$bundle")" --bind "$opt" \
        "$opt/orfs-current-repacked.rootfs" bash "$bundle/run_bscc_t6_qwen3_sram_macro.sbatch" \
        inside "$bundle" "$SLURM_JOB_ID" "$opt" "$SLURM_CPUS_PER_TASK" "$variant"
fi

source /OpenROAD-flow-scripts/env.sh
bundle=$2
root=$(dirname "$bundle")
out=$bundle/sram-$3
opt=$4
cores=$5
variant=$6
fixture=$bundle/qwen3_sram_macro_fixture.sv
measure=$bundle/qwen3_sram_macro_power.py
incoming=$root/incoming/macro-views
archive=$incoming/source/issue-200-compact-local-s
cell_lib=/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib
bank_lib=$incoming/source/issue-155/bank-views-011/generation/bank/s_sram_256x128_freepdk45_TT_1p1V_25C.lib
cells=$incoming/sim-models/cells.v
bank=$incoming/sim-models/bank-functional.v
vlt=$opt/verilator-5.042/bin/verilator

mkdir "$out"
(cd "$incoming/source" && sha256sum --quiet -c ../source-files.sha256)
printf '%s  %s\n' \
    62f202ce18b251e751f4c9bfda125e7eef1ce45d96d74d5e3d5c81a06bf4bdfe "$cells" \
    1871109017b197e12c03beb0a1f2a1bd9f0387898858a831535cf300744fe10e "$bank" \
    8d540a4d4cf6d09d27c87ad067857a9c0c2eeb023ab7a56e058cd3113db4e9b1 "$cell_lib" \
    47f8de1c22d27beb51982c73ab745e1f3f2b5a7819e53bcb6da73980ce077189 "$bank_lib" > "$out/libraries.sha256"
sha256sum -c "$out/libraries.sha256"
"$vlt" --version > "$out/verilator.txt"
openroad -version > "$out/openroad.txt"
sha256sum "$vlt" "$(command -v openroad)" "$bundle/inputs.sha256" "$incoming/source-files.sha256" \
    > "$out/tools.sha256"
cat > "$out/routed-lint.vlt" <<'VLT'
`verilator_config
lint_off -rule PINMISSING -file "*/6_final.v"
VLT

replay() {
    local name=$1
    local physical=$2
    local target=$out/$name
    local define=()
    local cases=(idle read128 write128 write256 write512)
    mkdir "$target"
    if [[ $name == s-base ]]; then
        define=(-DSRAM_BASE)
    else
        cases+=(read512)
    fi
    "$vlt" --binary --timing --trace --trace-depth 99 --assert -j "$cores" --timescale-override 1ns/1ps \
        --top-module qwen3_sram_macro_fixture --Mdir "$target/obj" -Wno-TIMESCALEMOD \
        "${define[@]}" "$out/routed-lint.vlt" "$fixture" "$physical/6_final.v" "$cells" "$bank" \
        > "$target/build.log" 2>&1
    for mode in "${cases[@]}"; do
        local sample=$target/$mode
        mkdir "$sample"
        "$target/obj/Vqwen3_sram_macro_fixture" "+CASE=$mode" "+VCD=$sample/raw.vcd" > "$sample/run.log"
        grep -Eq '^PASS SRAM ' "$sample/run.log"
    done
    python3 -B "$measure" "$target" "$physical" "$cell_lib" "$bank_lib" "$cores" "${cases[@]}"
    (cd "$target" && sha256sum calibration.json */{run.log,raw.vcd,gate-300mhz.vcd,power.tcl,power.log,receipt.json} > results.sha256 && sha256sum -c results.sha256)
}

case "$variant" in
    p|base|both) ;;
    *) printf 'Expected p, base or both: %s\n' "$variant" >&2; exit 2 ;;
esac
if [[ $variant == p || $variant == both ]]; then
    replay s-p "$archive/run10-delay1/results/4/flow/results/nangate45/local_s_p/base"
fi
if [[ $variant == base || $variant == both ]]; then
    replay s-base "$archive/run08-base0/results/0/flow/results/nangate45/local_s_base/base"
fi
(cd "$out" && sha256sum libraries.sha256 tools.sha256 verilator.txt openroad.txt s-*/results.sha256 > results.sha256 && sha256sum -c results.sha256)
