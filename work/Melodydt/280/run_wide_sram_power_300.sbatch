#!/usr/bin/env bash
#SBATCH --job-name=mdt-280s512pwr
#SBATCH --partition=c64,c96
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --time=00:30:00
#SBATCH --output=slurm-%j.log
set -euo pipefail
base=/public/home/yuzelu
bundle=$SLURM_SUBMIT_DIR
cd "$bundle"
if [[ ${1:-} != inside ]]; then
    sha256sum -c bundle.sha256
    exec srun --exact -n1 -c "$SLURM_CPUS_PER_TASK" --cpu-bind=cores \
      /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind "$base" \
      "$base/opt/eda/containers/orfs-current-repacked.sif" bash "$bundle/run_wide_sram_power_300.sbatch" inside "$bundle" "$SLURM_JOB_ID" "$SLURM_CPUS_PER_TASK"
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
version=$runs/wide-sram-pm-02/wide-116938
flow=$project/issue-200-compact-local-s
physical=$flow/run10-delay1/results/4/flow/results/nangate45/local_s_p/base
storage=$flow/run08-base0/results/0/flow/results/nangate45/local_s_base/base/6_final.v
cal=$project/issue-234-systemc-benchmark/s-activity-002
bank=$project/issue-155/bank-views-011/generation/bank/s_sram_256x128_freepdk45_TT_1p1V_25C.lib
vlt=$base/opt/eda/verilator-5.042/bin/verilator
sha256sum -c "$version/wide-results.sha256" "$version/physical.sha256" > "$out/source-check.log"
"$vlt" --version > "$out/verilator-version.txt"
sha256sum "$vlt" "$cal/cells.v" "$cal/bank-functional.v" "$bank" "$version/test_compact_s.sv" \
  "$physical"/6_final.{odb,sdc,spef,v} > "$out/inputs.sha256"
python3 - "$version/test_compact_s.sv" "$out/test_compact_s.sv" <<'PY'
from pathlib import Path
import sys

src, output = map(Path, sys.argv[1:])
text = src.read_text()
text = text.replace("    local_s_base base (", "    reg [9:0] feed_base = 0;\n    local_s_base base (")
text = text.replace(".load_a_base(10'd0), .load_b_base(10'd0)", ".load_a_base(feed_base), .load_b_base(feed_base)")
text = text.replace("bank_address !== 32'b0", "bank_address !== {4{feed_base[9:2]}}")
start = text.index("    initial begin\n        repeat (2) @(negedge clk);")
end = text.index("    initial begin\n        #5000;", start)
output.write_text(text[:start] + r"""
    localparam int ROWS = 16, WINDOW_CYCLES = 1024;
    string mode;
    string dump_path;
    bit activity_done = 0;
    int reads_before, writes_before, narrow_before;

    function automatic logic [127:0] word_data(input int address);
        logic [31:0] x;
        x = (32'(address) + 32'h95a1258e) * 32'h9e3779b9;
        return {x, x ^ 32'h59867b12, ~x, x ^ 32'hb79d641e};
    endfunction

    task automatic read_feed(input int row);
        feed_base = 10'(4 * row);
        load_valid = 1;
        do @(posedge clk); while (!load_ready);
        @(negedge clk);
        load_valid = 0;
        do @(negedge clk); while (!a_valid || !b_valid);
        if (a_data !== word_data(4*row) ||
            b_data !== {word_data(4*row+3), word_data(4*row+2), word_data(4*row+1), word_data(4*row)})
            $fatal(1, "512-bit data mismatch at row %0d", row);
        a_ready = 1;
        b_ready = 1;
        @(negedge clk);
        a_ready = 0;
        b_ready = 0;
        do @(negedge clk); while (!done_valid);
        if (done_error) $fatal(1, "feeder error");
        done_take = 1;
        @(negedge clk);
        done_take = 0;
    endtask

    initial begin
        if (!$value$plusargs("POWER_MODE=%s", mode) || !$value$plusargs("POWER_DUMP=%s", dump_path))
            $fatal(1, "power mode and dump path required");
        repeat (2) @(negedge clk);
        reset = 0;
        for (int address = 0; address < ROWS*4; address++) begin
            issue(1, 10'(address), word_data(address));
            wait_response(0);
            retire();
        end
        $dumpfile(dump_path);
        $dumpvars;
        repeat (4) @(negedge clk);
        reads_before = wide_reads;
        writes_before = narrow_writes;
        narrow_before = narrow_reads;
        $display("POWER_START_PS %0d", $time * 1000);
        fork
            begin
                case (mode)
                    "read": for (int row = 0; row < ROWS; row++) read_feed(row);
                    "write": for (int address = 0; address < ROWS*4; address++) begin
                        issue(1, 10'(address), ~word_data(address));
                        wait_response(0);
                        retire();
                    end
                    "idle": begin end
                    default: $fatal(1, "unknown power mode %s", mode);
                endcase
                activity_done = 1;
            end
            begin
                repeat (WINDOW_CYCLES) @(negedge clk);
                if (!activity_done) $fatal(1, "power window ended before activity");
                $display("POWER_END_PS %0d", $time * 1000);
            end
        join
        if (wide_reads - reads_before != (mode == "read" ? ROWS * 2 : 0) ||
            narrow_writes - writes_before != (mode == "write" ? ROWS * 4 : 0) ||
            narrow_reads != narrow_before)
            $fatal(1, "unmatched active/idle bank transaction counts");
        $display("POWER_COUNTS %s %0d %0d", mode, wide_reads-reads_before, narrow_writes-writes_before);
        if (mode == "write") begin
            for (int address = 0; address < ROWS*4; address++) begin
                issue(0, 10'(address), '0);
                wait_response(~word_data(address));
                retire();
            end
        end
        $display("POWER_FUNCTIONAL_PASS %s", mode);
        $finish;
    end

""" + text[end:].replace("#5000;", "#150000;"))
PY
"$vlt" --binary --timing --assert --trace -j "$cores" --timescale-override 1ns/1ps \
    --top-module test_compact_s -Wno-TIMESCALEMOD -DROUTED_SRAM --Mdir "$out/obj" \
    "$version/routed-lint.vlt" "$storage" "$physical/6_final.v" "$cal/cells.v" "$cal/bank-functional.v" \
    "$out/test_compact_s.sv" > "$out/build.log" 2>&1
for mode in read write idle; do
  "$out/obj/Vtest_compact_s" "+POWER_MODE=$mode" "+POWER_DUMP=$out/$mode.vcd" > "$out/$mode.log" 2>&1
  grep -E '^POWER_(FUNCTIONAL_PASS|COUNTS) ' "$out/$mode.log"
  first=$(awk '/^POWER_START_PS /{print $2}' "$out/$mode.log")
  last=$(awk '/^POWER_END_PS /{print $2}' "$out/$mode.log")
  [[ $((last - first)) == 20480000 ]]
  python3 -B "$bundle/gate_power_300.py" "$out/$mode.vcd" "$physical" TOP/test_compact_s/p \
      "$out/$mode" 20000 "$first" "$last" --cores 4 --lib "$bank" --escape --clip
done
python3 - "$out" <<'PY'
import json
from pathlib import Path
import sys
out = Path(sys.argv[1])
docs = {mode: json.loads((out / mode / "receipt.json").read_text()) for mode in ("read", "write", "idle")}
idle = docs["idle"]
rows = {}
for mode, count, partition in (("read", 32, "512-bit same-address four-bank read"), ("write", 64, "128-bit one-bank write")):
    active = docs[mode]
    if active["timing"]["window_ps"] != idle["timing"]["window_ps"]:
        raise ValueError("unpaired activity duration")
    rows[mode] = {"meaning": partition, "transactions": count, "active_power_w": active["power_w"],
                  "idle_power_w": idle["power_w"], "annotated": active["annotated"],
                  "incremental_nj_per_transaction": (active["energy_nj"] - idle["energy_nj"]) / count}
(out / "summary.json").write_text(json.dumps(rows, indent=2) + "\n")
PY
cd "$out"
sha256sum summary.json test_compact_s.sv inputs.sha256 openroad.sha256 {read,write,idle}.log \
  {read,write,idle}/{receipt.json,power.log} > results.sha256
sha256sum -c results.sha256
echo LOCAL_S_P_512_PAIRED_300_PASS
