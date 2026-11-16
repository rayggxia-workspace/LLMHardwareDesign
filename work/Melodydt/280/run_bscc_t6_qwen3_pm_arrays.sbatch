#!/usr/bin/env bash
#SBATCH --job-name=mdt-280pmarray
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
        singularity exec --cleanenv --bind "$(dirname "$bundle")" --bind "$opt" "$opt/orfs-current-repacked.rootfs" \
        bash "$bundle/run_bscc_t6_qwen3_pm_arrays.sbatch" inside "$bundle" "$SLURM_JOB_ID" "$opt" "$@"
fi

source /OpenROAD-flow-scripts/env.sh
bundle=$2
root=$(dirname "$bundle")
out=$bundle/array-$3
stage=$5
mkdir "$out"
if [[ $stage == wave ]]; then
    project=$root/wide/wide-38772137/source/project
    bank=$root/wide/sourcefs/project-circuit/LLMHardwareDesign/issue-155/bank-views-011/generation/bank/s_sram_256x128_freepdk45.v
    python3 -B - "$root" "$out" <<'PY'
from hashlib import sha256
import json
from pathlib import Path
import sys
from zlib import crc32
root,out=map(Path,sys.argv[1:])
assets=root/"component-observation/replay-38782605/decode-live-w4-tile128-pr272-combined/assets"
pages={"local":assets/"local.bin","mother":assets/"pos513-l0-mc-0.bin"}
receipt={}
for role,path in pages.items():
    original=path.read_bytes()
    length=int.from_bytes(original[12:16],"little") if role=="local" else len(original)
    if (role=="local" and (length!=352 or any(original[length:]))) or length%16:
        raise ValueError(f"unexpected PM program extent: {role}/{length}")
    data=original[:length]
    (out/f"{role}.hex").write_text("".join(data[i:i+16][::-1].hex()+"\n" for i in range(0,length,16)))
    receipt[role]={"length":length,"sha256":sha256(data).hexdigest(),"original_sha256":sha256(original).hexdigest()}
    if role=="local":
        (out/"local.crc").write_text(f"{crc32(data):08x}\n")
(out/"pages.json").write_text(json.dumps(receipt,indent=2)+"\n")
PY
    verilator=$4/verilator-5.042/bin/verilator
    compile() {
        local top=$1
        shift
        "$verilator" --binary --timing --trace --trace-depth 5 --assert -j 4 --timescale-override 1ns/1ps \
            --top-module "$top" --Mdir "$out/obj-$top" "$bundle/test_qwen3_pm_arrays.sv" "$@" > "$out/build-$top.log" 2>&1
    }
    local_wave() {
        local top=test_qwen3_lc_pm
        compile "$top" "$project/experiments/shared_x_control/rtl/lc_program_store_1k.sv"
        for mode in 0 1 2; do
            "$out/obj-$top/V$top" "+IMAGE=$out/local.hex" "+CRC=$(cat "$out/local.crc")" \
                "+WAVE=$out/local-$mode.vcd" "+MODE=$mode" > "$out/local-$mode.log"
            grep '^PASS local PM ' "$out/local-$mode.log"
        done
    }
    mother_wave() {
        local top=test_qwen3_mother_pm
        compile "$top" "$project/rtl/mother_control_v1/control_pm.sv" "$project/rtl/s_sram/block_feed_s16k_sram.sv" "$bank"
        "$out/obj-$top/V$top" "+IMAGE=$out/mother.hex" "+WAVE=$out/mother.vcd" > "$out/mother.log"
        grep '^PASS mother PM ' "$out/mother.log"
    }
    local_wave & local_job=$!
    mother_wave & mother_job=$!
    failed=0
    wait "$local_job" || failed=1
    wait "$mother_job" || failed=1
    ((failed==0))
    cd "$out"
    sha256sum pages.json *.hex *.crc *.vcd local-*.log mother.log > results.sha256
else
    [[ $stage == power ]]
    wave=$bundle/array-${6:?wave job}
    physical=$root/leaf-physical/physical-${7:?physical job}
    (cd "$wave" && sha256sum --quiet -c results.sha256)
    (cd "$physical" && sha256sum --quiet -c physical.sha256)
    export PYTHONPATH=$root/writer-power/frozen
    python3 -B - "$wave" "$physical" "$out" <<'PY'
import json
from pathlib import Path
import sys
from extract_c639_m_ports import extract
from gate_power_300 import analyze

wave,physical,out=map(Path,sys.argv[1:])
netlist=physical/"flow/results/nangate45/lc_program_store_1k/base"
estimates={}
for mode in (0,1,2):
    vcd=out/f"local-{mode}.vcd"
    extract(netlist/"6_final.v",wave/f"local-{mode}.vcd",vcd,"test_qwen3_lc_pm/dut",0,10050000,100,None)
    if mode in (1,2):
        estimates[f"boot{mode}"]=analyze(vcd,netlist,"dut",out/f"boot{mode}",10000,0,6050000,8,clip=True)
    if mode in (0,1):
        estimates[f"read{mode}"]=analyze(vcd,netlist,"dut",out/f"read{mode}",10000,6050000,10050000,8,clip=True)
(out/"pm-increment.json").write_text(json.dumps({
    "boot_and_crc_nj":estimates["boot1"]["energy_nj"]-estimates["boot2"]["energy_nj"],
    "read_22_words_nj":estimates["read0"]["energy_nj"]-estimates["read1"]["energy_nj"],
    "scope":"lc_program_store_1k register-array candidate, matching completed boot before read control"
},indent=2)+"\n")
PY
    cd "$out"
    sha256sum pm-increment.json */receipt.json > results.sha256
fi
sha256sum -c results.sha256
