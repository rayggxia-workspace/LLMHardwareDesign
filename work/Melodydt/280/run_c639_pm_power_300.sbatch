#!/usr/bin/env bash
#SBATCH --job-name=mdt-280pm300
#SBATCH --partition=c64,c96
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=12
#SBATCH --time=01:45:00
#SBATCH --output=slurm-%j.log
set -euo pipefail
base=/public/home/yuzelu
if [[ ${1:-} == inside ]]; then
    bundle=$2
else
    bundle=${SLURM_SUBMIT_DIR:?}
fi
cd "$bundle"
if [[ ${1:-} != inside ]]; then
    sha256sum -c bundle.sha256
    exec srun --exact -n1 -c "$SLURM_CPUS_PER_TASK" --cpu-bind=cores \
      /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind "$base" \
      "$base/opt/eda/containers/orfs-current-repacked.sif" bash "$bundle/run_c639_pm_power_300.sbatch" inside "$bundle" "$SLURM_JOB_ID" "$SLURM_CPUS_PER_TASK"
fi
source /OpenROAD-flow-scripts/env.sh
bundle=$2
runs=$base/Melodydt/runs/issue-280
project=$base/project-circuit/LLMHardwareDesign
out=$bundle/result-$3
cores=$4
mkdir "$out"
openroad -version > "$out/openroad-version.txt"
sha256sum "$(command -v openroad)" > "$out/openroad.sha256"
common=$base/project-circuit
frozen=$runs/c639-g32-gate-01/c639-g32-116937/source/project/experiments/shared_x_control/rtl/lc_program_store_1k.sv
source=$common/issue234-native-pm-stream-20261112-01
baseline=$source/run-103489
basis=$common/issue234-algo1-ffn-ddr-both-20261112-02
dram=$common/issue234-algo1-ffn-chain-20261112-01/dramsim3
cells=$common/issue234-rope-to-qk-rtl-20261112-01/source/cells.sv
vlt=$base/opt/eda/verilator-5.042/bin/verilator
(cd "$source" && sha256sum -c source.sha256)
sha256sum -c "$baseline/proof.sha256"
cmp "$frozen" "$source/lc_program_store_1k.sv"
cp "$frozen" "$out/lc_program_store_1k.sv"
cp "$runs/c639-m-physical-03/route-116976/native/input.sdc" "$out/target.sdc"
sha256sum "$out"/{lc_program_store_1k.sv,target.sdc} "$cells" "$source/source.sha256" "$baseline/proof.sha256" "$vlt" \
    "$dram/libdramsim3.so" "$basis/DDR4-single-channel.ini" > "$out/inputs.sha256"
cat > "$out/config.mk" <<EOF
export PLATFORM = nangate45
export DESIGN_NAME = lc_program_store_1k
export DESIGN_NICKNAME = mdt_pm_store
export VERILOG_FILES = $out/lc_program_store_1k.sv
export SDC_FILE = $out/target.sdc
export CORE_UTILIZATION = 35
export PLACE_DENSITY = 0.55
EOF
make -C /OpenROAD-flow-scripts/flow DESIGN_CONFIG="$out/config.mk" WORK_HOME="$out/flow" NUM_CORES="$cores" \
  finish > "$out/flow.log" 2>&1
physical=$out/flow/results/nangate45/mdt_pm_store/base
reports=$out/flow/reports/nangate45/mdt_pm_store/base
metrics=$out/flow/logs/nangate45/mdt_pm_store/base/6_report.json
sha256sum "$physical"/6_final.{v,sdc,odb,spef} "$metrics" > "$out/physical.sha256"
echo PM_STORE_ROUTED
python3 - "$source/test_native_pm_image_stream.sv" "$out/test_native_pm_image_stream.sv" <<'PY'
from pathlib import Path
import sys
source, dest = map(Path, sys.argv[1:])
text = source.read_text()
first = "        config_pm(0);\n        loading=1;"
last = "        while(!done_valid) @(negedge clk);\n        repeat(3) begin"
if text.count(first) != 1 or text.count(last) != 1:
    raise ValueError("PM testbench launch anchors differ")
text = text.replace(first, """        config_pm(0);
        $display("POWER_START_PS %0d", $time * 1000);
        if ($test$plusargs("PM_IDLE")) begin
            repeat (4096) @(negedge clk);
            $display("POWER_IDLE_PASS");
            ddr_read_finish();
            $finish;
        end
        loading=1;""").replace(last, """        while(!done_valid) @(negedge clk);
        $display("POWER_END_PS %0d", $time * 1000);
        repeat(3) begin""")
text = text.replace("    initial clk=0;", """    initial clk=0;
    initial begin
        string dump_path;
        if (!$value$plusargs("POWER_DUMP=%s", dump_path)) $fatal(1,"trace path");
        $dumpfile(dump_path);
        $dumpvars;
    end""")
dest.write_text(text)
PY
"$vlt" --binary --timing --assert --trace --timescale-override 1ns/1ps -j "$cores" \
    --top-module test_native_pm_image_stream -Wno-TIMESCALEMOD -Wno-PINMISSING \
    -CFLAGS "-std=c++17 -isystem $dram/src -isystem $dram/ext/headers" \
    -LDFLAGS "-L$dram -Wl,-rpath,$dram -ldramsim3" "$source/ddr_read_bridge.cpp" --Mdir "$out/obj" \
    "$source/native_pm_image_stream.sv" "$physical/6_final.v" "$cells" "$out/test_native_pm_image_stream.sv" \
    > "$out/build.log" 2>&1
for mode in active idle; do
    mkdir "$out/ddr-$mode"
    args=()
    if [[ $mode == idle ]]; then args+=(+PM_IDLE); fi
    "$out/obj/Vtest_native_pm_image_stream" "+DDR_CONFIG=$basis/DDR4-single-channel.ini" "+DDR_OUTPUT=$out/ddr-$mode" \
        "+IMAGE=$baseline/local.ddr.bin" "+HEX=$baseline/local.hex" "+CRC=$(cat "$baseline/crc.txt")" \
        "+POWER_DUMP=$out/$mode.vcd" "${args[@]}" > "$out/$mode.log" 2>&1
done
grep '^PASS native DDR-to-LC PM' "$out/active.log"
grep '^POWER_IDLE_PASS' "$out/idle.log"
cmp "$baseline/trace/transactions.tsv" "$out/ddr-active/transactions.tsv"
first=$(awk '/^POWER_START_PS /{print $2}' "$out/active.log")
last=$(awk '/^POWER_END_PS /{print $2}' "$out/active.log")
quiet=$(awk '/^POWER_START_PS /{print $2}' "$out/idle.log")
python3 -B "$bundle/gate_power_300.py" "$out/active.vcd" "$physical" test_native_pm_image_stream/store "$out/active" 10000 "$first" "$last" --cores 4 --escape --clip
python3 -B "$bundle/gate_power_300.py" "$out/idle.vcd" "$physical" test_native_pm_image_stream/store "$out/idle" 10000 "$quiet" "$((quiet+last-first))" --cores 4 --escape --clip
python3 - "$out" <<'PY'
import json
from pathlib import Path
import sys
out = Path(sys.argv[1])
a, i = [json.loads((out / case / "receipt.json").read_text()) for case in ("active", "idle")]
if a["timing"]["window_ps"] != i["timing"]["window_ps"]:
    raise ValueError("PM active and idle windows disagree")
result = {"scope": "local PM store, 512-bit DDR response to 22 checked 128-bit writes, six bursts",
          "active_power_w": a["power_w"], "idle_power_w": i["power_w"],
          "window_ps": a["timing"]["window_ps"], "incremental_nj": a["energy_nj"] - i["energy_nj"],
          "incremental_nj_per_write": (a["energy_nj"] - i["energy_nj"]) / 22}
(out / "summary.json").write_text(json.dumps(result, indent=2) + "\n")
PY
cd "$out"
sha256sum physical.sha256 inputs.sha256 openroad.sha256 summary.json {active,idle}.log \
  {active,idle}/{receipt.json,power.log} "$reports/6_finish.rpt" > results.sha256
sha256sum -c results.sha256
echo MATCHED_C639_LC_PM_POWER_300_PASS
