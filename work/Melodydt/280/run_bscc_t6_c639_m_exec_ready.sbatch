#!/usr/bin/env bash
#SBATCH --job-name=mdt-280mexec
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
    sha256sum -c inputs.sha256
    opt=$HOME/LLMHardware/opt
    set +u
    source /public3/soft/modules/module.sh
    module load singularity/3.7.0
    set -u
    exec srun --ntasks=1 --cpus-per-task="$SLURM_CPUS_PER_TASK" --cpu-bind=cores \
        singularity exec --cleanenv --bind "$(dirname "$bundle")" --bind "$opt" \
        "$opt/orfs-current-repacked.rootfs" bash "$bundle/run_bscc_t6_c639_m_exec_ready.sbatch" \
        inside "$bundle" "$SLURM_JOB_ID" "$opt"
fi

source /OpenROAD-flow-scripts/env.sh
bundle=$2
out=$bundle/check-$3
verilator=$4/verilator-5.042/bin/verilator
frozen=$(dirname "$bundle")/wide/wide-38772137/source/project
project=$out/source/project
mkdir -p "$project/rtl" "$project/experiments"
cp -R "$frozen/rtl/w8a16_v1" "$project/rtl/"
cp -R "$frozen/experiments/w8a16_weight" "$project/experiments/"
leaf=$project/experiments/w8a16_weight
template=$leaf/m_native_leaf_s32.sv.in
cmp "$frozen/experiments/w8a16_weight/m_native_leaf_s32.sv.in" "$template"
python3 -B "$bundle/prepare_c639_m_exec_ready.py" "$template" "$out/exec-ready-guard.v"
python3 -B "$leaf/generate_leaf.py"
yosys -Q -p "read_verilog $out/exec-ready-guard.v; prep -top exec_ready_guard; sat -verify -prove equal 1 -show-inputs" > "$out/guard-sat.log"
grep -Fq 'SAT proof finished - no model found: SUCCESS!' "$out/guard-sat.log"
python3 -B "$leaf/leaf_check.py" --source "$out/source" --out "$out/lint" --verilator "$verilator"
diff -u "$frozen/experiments/w8a16_weight/m_native_leaf_s32.sv.in" "$template" > "$out/m-exec-ready.patch" || [[ $? == 1 ]]
cd "$out"
sha256sum exec-ready-guard.v guard-sat.log m-exec-ready.patch lint/*.json lint/lint.log \
    source/project/rtl/w8a16_v1/m_native_leaf_s32.sv > results.sha256
sha256sum -c results.sha256
