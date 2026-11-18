#!/usr/bin/env bash
#SBATCH --job-name=mdt-280mbaseidle
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
        bash "$bundle/run_bscc_t6_m_baseline_idle.sbatch" inside "$bundle" "$SLURM_JOB_ID" "$opt" "$SLURM_CPUS_PER_TASK" "${1:?baseline wave job}"
fi

source /OpenROAD-flow-scripts/env.sh
bundle=$2
root=$(dirname "$bundle")
out=$bundle/idle-$3
source=$root/wide/wide-38772137/source/project/rtl/w8a16_v1
archive=$root/m-sta
wave=$bundle/m-$6
(cd "$archive" && sha256sum --quiet -c inputs.sha256)
(cd "$wave" && sha256sum --quiet -c results.sha256)
mkdir "$out" "$out/physical"
ln -s "$archive"/6_final.{odb,sdc,spef} "$wave/6_final.v" "$out/physical/"
# Keep the same routed port contract, with no requests issued after reset.
python3 -B - "$wave/m-ports.v" "$out/test_m_clocked_idle.sv" <<'PY'
from pathlib import Path
import re
import sys

ports,testbench=map(Path,sys.argv[1:])
decl=[]
connections=[]
enabled={"lr_ready","mc_req_ready","mc_close_ready","mc_fence_req_ready"}
for row in ports.read_text().splitlines():
    direction,width,name=re.fullmatch(r"\s*(input|output)\s+(\[\d+:\d+\]\s+)?(\w+);\s*",row).groups()
    initial = (" = '1" if name in enabled or name=="reset" else " = '0") if direction=="input" else ""
    decl.append(f"logic {width or ''}{name}{initial};")
    connections.append(f".{name}({name})")
testbench.write_text("`timescale 1ns/1ps\nmodule test_m_clocked_idle;\n"
    + "\n".join(decl) + "\nm_native_leaf_s32 dut(" + ", ".join(connections) + ");\n"
    + """always #5 clk=~clk;
initial begin
    $dumpfile("idle.vcd");
    $dumpvars(1,dut);
    repeat(5) @(negedge clk);
    reset=0;
    repeat(8287) @(negedge clk);
    if(lr_valid || mc_req_valid || mc_close_valid || mc_fence_req_valid)
        $fatal(1,"traffic during reset-empty idle capture");
    $display("PASS old M reset-empty clocked idle");
    $finish;
end
endmodule
""")
PY
vlt=$4/verilator-5.042/bin/verilator
"$vlt" --version > "$out/verilator.txt"
"$vlt" --binary --timing --trace --trace-depth 2 --assert -j "$5" --timescale-override 1ns/1ps \
    --top-module test_m_clocked_idle --Mdir "$out/obj" "$out/test_m_clocked_idle.sv" \
    "$source/"{m_native_leaf_s32,m_native_s32,weight_records,m_group_s32,projection_context_s32,scale_group_s32}.sv \
    > "$out/build.log" 2>&1
cd "$out"
./obj/Vtest_m_clocked_idle > run.log
grep -q '^PASS old M reset-empty clocked idle' run.log
helper=$root/writer-power/frozen
python3 -B "$helper/extract_c639_m_ports.py" "$wave/m-ports.v" idle.vcd ports.vcd test_m_clocked_idle/dut 0 82920000 100
python3 -B "$helper/gate_power_300.py" ports.vcd physical dut power 10000 1000000 82920000 --cores "$5" --clip
sha256sum test_m_clocked_idle.sv verilator.txt run.log ports.{vcd,json} power/receipt.json > results.sha256
sha256sum -c results.sha256
