#!/usr/bin/env bash
#SBATCH --job-name=mdt-280wide
#SBATCH --partition=c64,c96
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --time=00:15:00
#SBATCH --output=slurm-%j.log
set -euo pipefail
base=/public/home/yuzelu
bundle=${SLURM_SUBMIT_DIR:?}
cd "$bundle"
if [[ ${1:-} != container ]]; then
    sha256sum -c bundle.sha256
    exec srun --exact -N1 -n1 -c "$SLURM_CPUS_PER_TASK" \
       /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind "$base" \
       --env "SLURM_SUBMIT_DIR=$bundle" "$base/opt/eda/containers/orfs-current-repacked.sif" \
       bash "$bundle/run_wide_sram_pm.sbatch" container "$SLURM_JOB_ID" "$SLURM_CPUS_PER_TASK"
fi
job=$2
cores=$3
out=$bundle/wide-$job
mkdir "$out"
project=$base/project-circuit/LLMHardwareDesign
archive=$project/issue-200-compact-local-s
calibration=$project/issue-234-systemc-benchmark/s-activity-002
native=$base/Melodydt/runs/issue-280/gate-c639-01/c639-116856/source/project
vlt=$base/opt/eda/verilator-5.042/bin/verilator
gate_p=$archive/run10-delay1/results/4/flow/results/nangate45/local_s_p/base/6_final.v
gate_base=$archive/run08-base0/results/0/flow/results/nangate45/local_s_base/base/6_final.v
testbench=$archive/sim03/source/project/experiments/compact_local_s/test_compact_s.sv
bank=$calibration/bank-functional.v
"$vlt" --version > "$out/verilator.txt"
printf '%s  %s\n' \
    add5e99b97b471d35ef6c1eb3161821968172a96af4feb130fd4ca45217254fc "$gate_base" \
    b93d064cb07d3978efe280cbddec91fb2c24d74c932078a808680705ca01e32d "$gate_p" \
    1871109017b197e12c03beb0a1f2a1bd9f0387898858a831535cf300744fe10e "$bank" > "$out/physical.sha256"
sha256sum -c "$out/physical.sha256"
for name in local_s_base local_s_p block_feed_s16k_sram; do
    cmp "$native/rtl/s_sram/$name.sv" "$calibration/$name.sv"
done
sha256sum "$vlt" "$testbench" "$calibration/"{local_s_base.sv,local_s_p.sv,block_feed_s16k_sram.sv,block_feed_loader.sv,cells.v} \
  "$native/rtl/mother_control_v1/control_pm.sv" \
  "$native/experiments/shared_x_control/rtl/lc_program_store_1k.sv" > "$out/tools-inputs.sha256"

python3 -B - "$testbench" "$out/test_compact_s.sv" <<'PY'
from pathlib import Path
import sys

source, target = map(Path, sys.argv[1:])
text = source.read_text()
anchor = "    initial begin\n        repeat (2) @(negedge clk);"
monitor = ["    wire [3:0] bank_enable, bank_write;", "    wire [31:0] bank_address;"]
for index in range(4):
    rtl = f"p.storage.banks[{index}].memory"
    gate = f"p.\\storage.banks[{index}].memory "
    monitor.append("`ifdef ROUTED_SRAM")
    for name, pin, prefix in (("bank_enable", "csb0", "~"), ("bank_write", "web0", "~"), ("bank_address", "addr0", "")):
        target_bit = f"{name}[{index}]" if name != "bank_address" else f"{name}[{8 * index} +: 8]"
        monitor.append(f"    assign {target_bit} = {prefix}{gate}.{pin};")
    monitor.append("`else")
    for name, pin, prefix in (("bank_enable", "csb0", "~"), ("bank_write", "web0", "~"), ("bank_address", "addr0", "")):
        target_bit = f"{name}[{index}]" if name != "bank_address" else f"{name}[{8 * index} +: 8]"
        monitor.append(f"    assign {target_bit} = {prefix}{rtl}.{pin};")
    monitor.append("`endif")
monitor.append("""    int wide_reads = 0;
    int narrow_writes = 0;
    int narrow_reads = 0;
    always @(posedge clk) begin
        if (!reset) begin
            if (req_valid && req_ready) begin
                if (bank_enable !== (4'b0001 << req_addr[1:0])) $fatal(1, "SRAM ordinary bank mask");
                if ((bank_write & bank_enable) !== (req_write ? bank_enable : 4'b0)) $fatal(1, "SRAM ordinary bank direction");
                if (req_write) narrow_writes <= narrow_writes + 1;
                else narrow_reads <= narrow_reads + 1;
            end else if (bank_enable != 0) begin
                if (bank_enable !== 4'b1111 || bank_write !== 4'b0000 || bank_address !== 32'b0)
                    $fatal(1, "SRAM 512-bit feeder read must select all four banks at the same address");
                wide_reads <= wide_reads + 1;
            end
        end
    end
""")
if text.count(anchor) != 1:
    raise ValueError("unexpected #200 SRAM testbench")
text = text.replace(anchor, "\n".join(monitor) + anchor)
text = text.replace('        $display("PASS compact S', '''        if (wide_reads != 2 || narrow_writes != 4 || narrow_reads != 1)
            $fatal(1, "unexpected SRAM bank transaction counts %0d %0d %0d", wide_reads, narrow_writes, narrow_reads);
        $display("PASS SRAM BANKS wide_512_reads=%0d narrow_128_writes=%0d narrow_128_reads=%0d mask_wide=1111",
                 wide_reads, narrow_writes, narrow_reads);
        $display("PASS compact S''')
target.write_text(text)
PY
for mode in rtl gate; do
    if [[ $mode == rtl ]]; then
        source=("$calibration/"{local_s_base.sv,local_s_p.sv,block_feed_s16k_sram.sv,block_feed_loader.sv})
        define=()
    else
        source=("$gate_base" "$gate_p" "$calibration/cells.v")
        define=(-DROUTED_SRAM)
    fi
    "$vlt" --binary --timing --assert -j "$cores" --timescale-override 1ns/1ps \
        --top-module test_compact_s -Wno-TIMESCALEMOD "${define[@]}" --Mdir "$out/obj-$mode" \
        "${source[@]}" "$bank" "$out/test_compact_s.sv" > "$out/build-$mode.log" 2>&1
    "$out/obj-$mode/Vtest_compact_s" > "$out/run-$mode.log" 2>&1
    grep '^PASS' "$out/run-$mode.log" | tee "$out/pass-$mode.txt"
done
cmp "$out/pass-rtl.txt" "$out/pass-gate.txt"

python3 -B - "$native" "$out/pm-interface.json" <<'PY'
import json
from pathlib import Path
import re
import sys

native, output = map(Path, sys.argv[1:])
checks = {
    "rtl/mother_control_v1/control_pm.sv": ("req_data_i", "rsp_data_o"),
    "experiments/shared_x_control/rtl/lc_program_store_1k.sv": ("cfg_data", "pm_data"),
    "rtl/mother_control_native/native_product_controller.sv": ("pm_rsp_data",),
}
widths = {}
for path, ports in checks.items():
    text = (native / path).read_text().split(");", 1)[0]
    widths[path] = {}
    for port in ports:
        match = re.search(r"\[(\d+):0\]\s+" + re.escape(port) + r"\b", text)
        if not match:
            raise ValueError(f"unverified PM port {port}: {path}")
        widths[path][port] = int(match[1]) + 1
if list(widths.values()) != [{"req_data_i": 128, "rsp_data_o": 128}, {"cfg_data": 128, "pm_data": 128}, {"pm_rsp_data": 512}]:
    raise ValueError("native program-memory interface changed")
output.write_text(json.dumps(widths, indent=2) + "\n")
print(output.read_text(), end="")
PY
sha256sum "$out/"{physical.sha256,tools-inputs.sha256,test_compact_s.sv,verilator.txt,pm-interface.json} \
    "$out"/{run,pass}-{rtl,gate}.* > "$out/wide-results.sha256"
sha256sum -c "$out/wide-results.sha256"
printf '%s\n' 'NATIVE_512_FEEDER_AND_PM_INTERFACE_PASS'
