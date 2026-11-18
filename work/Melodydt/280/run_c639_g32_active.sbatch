#!/usr/bin/env bash
#SBATCH --job-name=mdt-280ag639
#SBATCH --partition=c64,c96
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --time=00:30:00
#SBATCH --output=slurm-%j.log
set -euo pipefail
base=/public/home/yuzelu
bundle=${SLURM_SUBMIT_DIR:?}
job=$SLURM_JOB_ID
runs=$base/Melodydt/runs/issue-280
sealed=$runs/c639-g32-gate-01/c639-g32-116937
obj=$sealed/replay-116937/obj
powered=$runs/c639-g32-power-03
work=$bundle/active-$job
exp=project/experiments/block_local_native
top=test_native_decode638_product_replay
singularity=/public/software/singularity-ce-4.3.4/bin/singularity
image=$base/opt/eda/containers/orfs-current-repacked.sif
cd "$bundle"
sha256sum -c bundle.sha256
(cd "$sealed" && sha256sum --quiet -c gate-results.sha256 && sha256sum --quiet -c gate-source.sha256)
sha256sum --quiet -c "$powered/power-116943/power-results.sha256"
mkdir "$work"
cp -a "$sealed/"{source,source.tar,activity-0.txt,activity-1.txt} "$work/"

cat > "$work/g32_active.cpp" <<'CPP'
#include "Vtest_native_decode638_product_replay.h"
#include "Vtest_native_decode638_product_replay___024root.h"
#include "verilated.h"
#include "verilated_fst_c.h"

#include <cstdint>
#include <fstream>
#include <iostream>
#include <memory>
#include <string>

int main(int argc, char** argv) {
    const std::string output_prefix = "+DDR_OUTPUT=";
    const std::string schedule_prefix = "+CAPTURE_SCHEDULE=";
    std::string output, schedule;
    for (int i = 1; i < argc; ++i) {
        const std::string argument(argv[i]);
        if (argument.compare(0, output_prefix.size(), output_prefix) == 0) {
            output = argument.substr(output_prefix.size());
        } else if (argument.compare(0, schedule_prefix.size(), schedule_prefix) == 0) {
            schedule = argument.substr(schedule_prefix.size());
        }
    }
    std::ifstream frozen(schedule);
    std::string phase;
    uint64_t first_call = 0, old_gate_up_end = 0, first_down = 0, old_down_end = 0;
    if (output.empty() || !(frozen >> phase >> first_call >> old_gate_up_end) || phase != "gate-up" ||
        !(frozen >> phase >> first_down >> old_down_end) || phase != "down") return 1;

    auto context = std::make_unique<VerilatedContext>();
    context->commandArgs(argc, argv);
    context->traceEverOn(true);
    auto top = std::make_unique<Vtest_native_decode638_product_replay>(context.get());
    VerilatedFstC trace;
    top->trace(&trace, 4);
    constexpr uint64_t duration = 81920000;
    bool last_clock = false;
    bool last_fire = false;
    uint64_t first = 0;
    unsigned accepts = 0;
    while (!context->gotFinish()) {
        top->eval();
        const uint64_t now = context->time();
        const bool clock = top->rootp->test_native_decode638_product_replay__DOT__clk;
        const bool fire = top->rootp->test_native_decode638_product_replay__DOT__feed_forward__DOT__dut__DOT__g_adapter__DOT__stream__DOT__g_input_fire;
        const bool accepted = clock && !last_clock && last_fire;
        if (!first && now >= first_call && accepted) {
            if (now >= first_down || duration > first_down - now) return 2;
            first = now;
            trace.open((output + "/ffn-g32-active.fst").c_str());
            std::cout << "G32_FIRST_ACCEPT " << first << '\n';
        }
        if (first) {
            accepts += accepted;
            trace.dump(now);
            if (now >= first + duration) {
                trace.close();
                if (now != first + duration || accepts < 2) return 3;
                top->final();
                std::cout << "G32_ACTIVE " << first << ' ' << now << ' ' << accepts << '\n';
                return 0;
            }
        }
        last_clock = clock;
        last_fire = fire;
        if (!top->eventsPending()) break;
        context->time(top->nextTimeSlot());
    }
    std::cerr << "G32 active window did not complete\n";
    return 4;
}
CPP

runner=$work/source/$exp/run_decode638_q_tile_replay.sh
python3 -B - "$runner" <<'PY'
from pathlib import Path
import sys

file = Path(sys.argv[1])
text = file.read_text()
begin = text.index('"$vlt" --cc --exe --build')
end = text.index('\nrun_mode() {', begin)
text = text[:begin] + 'mkdir "$case_dir/obj"\nln -s "$run/V$top" "$case_dir/obj/V$top"\n' + text[end:]
end = text.index("\n grep -E '^(PASS q projection|")
text = text[:end] + """
 grep '^G32_ACTIVE ' "$case_dir/replay-$mode.log"
}
pids=()
for mode in "${modes[@]}"; do
 run_mode "$mode" &
 pids+=("$!")
done
failed=0
for pid in "${pids[@]}"; do
 if ! wait "$pid"; then failed=1; fi
done
exit "$failed"
"""
file.write_text(text)
PY
bash -n "$runner"

cat > "$work/link.sh" <<'BASH'
#!/usr/bin/env bash
set -euo pipefail
work=$1
obj=$2
top=$3
base=/public/home/yuzelu
include=$base/opt/eda/verilator-5.042/share/verilator/include
dram=$base/project-circuit/issue234-algo1-ffn-chain-20261112-01/dramsim3
objects=("$obj/"{ddr_read_bridge,verilated,verilated_dpi,verilated_fst_c,verilated_timing,verilated_threads}.o "$obj/V${top}__ALL.a")
sha256sum "${objects[@]}" "$obj/V$top" "$obj/V${top}___024root.h" "$dram/libdramsim3.so" > "$work/reused-model.sha256"
g++ -Os -std=c++17 -fcoroutines -DVERILATOR=1 -DVM_TIMING=1 -DVM_TRACE=1 -DVM_TRACE_FST=1 \
    -I"$obj" -I"$include" -I"$include/vltstd" "$work/g32_active.cpp" "${objects[@]}" \
    -lz -L"$dram" -Wl,-rpath,"$dram" -ldramsim3 -pthread -latomic -o "$work/V$top"
BASH
srun --exact -n1 -c "$SLURM_CPUS_PER_TASK" --cpu-bind=cores "$singularity" exec --cleanenv --bind "$base" \
    "$image" bash "$work/link.sh" "$work" "$obj" "$top" > "$work/link.log" 2>&1
srun --exact -n1 -c "$SLURM_CPUS_PER_TASK" --cpu-bind=cores "$singularity" exec --cleanenv --bind "$base" \
    --env "SLURM_JOB_ID=$job,SLURM_CPUS_PER_TASK=$SLURM_CPUS_PER_TASK,FORCE_SECOND_FFN_REARM=1" \
    "$image" bash "$runner" "$work" \
    "$base/project-circuit/issue260-token-decode638-live-qkv-xWSJhdWQ/linked-103952" history-final-product-ffn-repeat 636 2

replay=$work/replay-$job
python3 -B - "$work" "$replay" "$sealed/replay-116937" <<'PY'
import json
from pathlib import Path
import re
import sys

work, replay, reference = map(Path, sys.argv[1:])
receipts = []
for mode in (0, 1):
    log = replay / f"replay-{mode}.log"
    match = None
    with log.open() as stream:
        for line in stream:
            if line.startswith("G32_ACTIVE "):
                if match is not None:
                    raise ValueError("duplicate G32 window")
                match = re.fullmatch(r"G32_ACTIVE (\d+) (\d+) (\d+)\n", line)
    if not match:
        raise ValueError(f"missing G32 window: {log}")
    start, end, accepts = map(int, match.groups())
    (work / f"g32-active-{mode}.txt").write_text(f"g32-active {start} {end}\n")
    prefix_bytes = {}
    for item in ("transactions.tsv", "write-transactions.tsv", "activation-transactions.tsv"):
        sample = replay / f"DDR-{mode}" / item
        baseline = reference / f"DDR-{mode}" / item
        with sample.open("rb") as active, baseline.open("rb") as original:
            for chunk in iter(lambda: active.read(1024 * 1024), b""):
                if chunk != original.read(len(chunk)):
                    raise ValueError(f"G32 capture changed the frozen DDR prefix: {sample}")
        prefix_bytes[item] = sample.stat().st_size
    if not prefix_bytes["transactions.tsv"] or end - start != 81920000 or accepts < 2:
        raise ValueError("missing active G32 workload evidence")
    receipts.append({"mode": mode, "start_ps": start, "end_ps": end, "accepted_inputs_including_first_edge": accepts,
                     "matching_frozen_ddr_prefix_bytes": prefix_bytes})
(work / "active.json").write_text(json.dumps(receipts, indent=2) + "\n")
print((work / "active.json").read_text(), end="")
PY
(cd "$replay" && sha256sum generated/{program.json,reference.hex,local.hex,mother.hex} \
    replay-?.log DDR-*/{ffn-g32-active.fst,transactions.tsv,write-transactions.tsv,activation-transactions.tsv} > proof.sha256)
sha256sum "$work/"{link.sh,link.log,g32_active.cpp,reused-model.sha256,active.json,g32-active-0.txt,g32-active-1.txt} \
    "$runner" "$replay/proof.sha256" > "$work/gate-results.sha256"

power=$powered/run_c639_g32_power.sbatch
printf '%s  %s\n' 90a250612ab4d4ee9568b53ea64f0db70c9709024ecd8e21002a2a0ed7ab800f "$power" | sha256sum -c -
python3 -B - "$power" "$work/active-power.sh" <<'PY'
from pathlib import Path
import sys

source, output = map(Path, sys.argv[1:])
text = source.read_text()
changes = {
    'root=$base/Melodydt/runs/issue-280/c639-g32-gate-01/c639-g32-116937': 'root=$bundle/active-$job',
    'replay=$root/replay-116937': 'replay=$root/replay-$job',
    'cases=(0:gate-up 0:down 1:gate-up 1:down)': 'cases=(0:g32-active 1:g32-active)',
    '$root/activity-$mode.txt': '$root/g32-active-$mode.txt',
    'C639_G32_FOUR_WINDOWS_POWER_PASS': 'C639_G32_ACTIVE_WINDOWS_POWER_PASS',
}
for before, after in changes.items():
    if text.count(before) != 1:
        raise ValueError(before)
    text = text.replace(before, after)
output.write_text(text)
PY
bash -n "$work/active-power.sh"
srun --exact -n1 -c "$SLURM_CPUS_PER_TASK" --cpu-bind=cores "$singularity" exec --cleanenv --bind "$base" \
    --env "SLURM_SUBMIT_DIR=$bundle" "$image" \
    bash "$work/active-power.sh" container "$job" "$SLURM_CPUS_PER_TASK" 0

python3 -B - "$work/active.json" "$bundle/power-$job" <<'PY'
import json
from pathlib import Path
import sys

summary, output = map(Path, sys.argv[1:])
results = json.loads(summary.read_text())
for mode in results:
    sample = output / f"mode-{mode['mode']}-g32-active"
    vcd = json.loads((sample / "functional.json").read_text())["handshakes_after_first_timestamp"]
    if vcd["input_accepts"] + 1 != mode["accepted_inputs_including_first_edge"] or vcd["output_accepts"] < 1:
        raise ValueError(f"G32 driver and exported waveform do not agree: {mode} {vcd}")
    power = json.loads((sample / "openroad/receipt.json").read_text())
    mode.update(vcd, total_w=power["power_w"]["total"], pin_coverage=power["pin_coverage_fraction"])
    mode["window_j"] = mode["total_w"] * (mode["end_ps"] - mode["start_ps"]) * 1e-12
(output / "summary.json").write_text(json.dumps(results, indent=2) + "\n")
print((output / "summary.json").read_text(), end="")
PY
sha256sum "$work/"{gate-results.sha256,active-power.sh} "$bundle/power-$job/"{power-results.sha256,summary.json} > "$work/active-results.sha256"
sha256sum -c "$work/active-results.sha256"
printf '%s\n' C639_G32_ACTIVE_ENERGY_PASS
