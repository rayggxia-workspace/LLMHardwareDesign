#!/usr/bin/env bash
#SBATCH --job-name=mdt-280idle380
#SBATCH --partition=c64,c96
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --time=00:25:00
#SBATCH --output=slurm-%j.log
set -euo pipefail
base=/public/home/yuzelu
bundle=${SLURM_SUBMIT_DIR:?}
runs=$base/Melodydt/runs/issue-280
job=$SLURM_JOB_ID
work=$bundle/idle-$job
baseline=$runs/gate-c380-routed-02/c380-gate-116908
runner=project/experiments/block_local_native
cd "$bundle"
sha256sum -c bundle.sha256
(cd "$baseline" && sha256sum -c gate-results.sha256 && sha256sum -c gate-source.sha256)
mkdir "$work"
cp -a "$baseline"/{source,algo1,source.tar,algo1.tar} "$work/"
cd "$work"
python3 -B - "source/$runner" <<'PY'
from pathlib import Path
import sys

root = Path(sys.argv[1])

def edit(filename, changes):
    path = root / filename
    text = path.read_text()
    for before, after in changes:
        if text.count(before) != 1:
            raise ValueError(f"unexpected fixture source: {filename}: {before}")
        text = text.replace(before, after)
    path.write_text(text)

edit("test_native_attention_core_scope.sv", [
    ("(output logic [31:0] sample_kv_callbacks);", "(input logic sample_idle, output logic [31:0] sample_kv_callbacks);"),
    ("    local_s_base storage(", """    logic idle_write = 0;
    logic [9:0] idle_address = '0;
    logic [127:0] idle_data = '0;
    always_ff @(posedge sample_idle) begin
        idle_write <= engine_write;
        idle_address <= engine_address;
        idle_data <= engine_data;
    end
    local_s_base storage("""),
    (".req_valid(active ? engine_req && allow_request : host_valid)",
     ".req_valid(!sample_idle && (active ? engine_req && allow_request : host_valid))"),
    (".req_write(active ? engine_write : host_write),.req_addr(active ? engine_address : host_address)",
     ".req_write(sample_idle ? idle_write : (active ? engine_write : host_write)),\n        .req_addr(sample_idle ? idle_address : (active ? engine_address : host_address))"),
    (".req_data(active ? engine_data : host_data)", ".req_data(sample_idle ? idle_data : (active ? engine_data : host_data))"),
    (".rsp_ready(active ? engine_take && allow_ack : host_take)", ".rsp_ready(sample_idle || (active ? engine_take && allow_ack : host_take))"),
    ("assign engine_ready=active &&", "assign engine_ready=!sample_idle && active &&"),
    ("assign engine_rsp=active &&", "assign engine_rsp=!sample_idle && active &&"),
])
edit("c380_activity_driver.cpp", [
    ("    std::string output;", "    std::string output;\n    bool idle = false;"),
    ("        if (arg.compare", "        if (arg == \"+C380_IDLE\") idle = true;\n        if (arg.compare"),
    ("    VerilatedFstC trace;", "    top->sample_idle = 0;\n    VerilatedFstC trace;"),
    ("            trace.dump(now_ps);", "            trace.dump(now_ps);\n            if (idle && now_ps == first_ps) top->sample_idle = 1;"),
    ("                          << \" end_callback=\" << top->sample_kv_callbacks << '\\n';",
     """                          << " end_callback=" << top->sample_kv_callbacks << '\\n';
                if (idle) {
                    top->final();
                    std::cout << "IDLE SRAM WINDOW COMPLETE\\n";
                    return 0;
                }"""),
])
edit("run_native_attention_core_scope.sh", [
    ("--trace-depth 4 --timing", "--trace-depth 4 --trace-max-array 256 --timing"),
    ("for mode in 0 1; do\n run_dir=$out/mode-$mode", "for scenario in mode-0 mode-1 idle-0 idle-1; do\n mode=${scenario##*-}\n idle=()\n if [[ $scenario == idle-* ]]; then idle=(+C380_IDLE); fi\n run_dir=$out/$scenario"),
    ('"+verilator+rand+reset+$mode" >', '"+verilator+rand+reset+$mode" "${idle[@]}" >'),
    (' grep \'^PASS typed AttentionCore \' "$run_dir/run.log"\n cmp "$generated/expected.hex" "$run_dir/readback.hex"',
     ' if [[ $scenario == idle-* ]]; then\n   grep \'^IDLE SRAM WINDOW COMPLETE$\' "$run_dir/run.log"\n else\n   grep \'^PASS typed AttentionCore \' "$run_dir/run.log"\n   cmp "$generated/expected.hex" "$run_dir/readback.hex"\n fi'),
])
PY
sha256sum source/"$runner"/{run_native_attention_core_scope.sh,test_native_attention_core_scope.sv,c380_activity_driver.cpp} > idle-source.sha256
export SELECT_V_BEAT=1 DDR_RESPONSE_QUEUE=1 OVERLAP_REFILL=1 HALF_TILE=1 OVERLAP_DOT=1
export SLURM_SUBMIT_DIR="$work"
bash "$work/source/$runner/run_native_attention_core_scope.sh"
export SLURM_SUBMIT_DIR="$bundle"
replay=$work/replay-$job
for mode in 0 1; do
    prior=$baseline/replay-116908/mode-$mode
    current=$replay/mode-$mode
    cmp "$prior/readback.hex" "$current/readback.hex"
    cmp "$prior/transactions.tsv" "$current/transactions.tsv"
    cmp <(grep -E '^(ACTIVITY_WINDOW|PASS typed AttentionCore|S overlap cycles=)' "$prior/run.log") \
        <(grep -E '^(ACTIVITY_WINDOW|PASS typed AttentionCore|S overlap cycles=)' "$current/run.log")
    cmp <(grep '^ACTIVITY_WINDOW ' "$current/run.log" | cut -d' ' -f1-4) \
        <(grep '^ACTIVITY_WINDOW ' "$replay/idle-$mode/run.log" | cut -d' ' -f1-4)
done
sha256sum idle-source.sha256 "$replay/proof.sha256" "$replay"/{mode,idle}-*/{attention.fst,run.log} > gate-results.sha256
sha256sum -c gate-results.sha256
cd "$bundle"

power=$runs/gate-c380-power-03/run_c380_gate_power.sbatch
printf '%s  %s\n' d70003d1730d809dae3f8b25d3e407315e223ff9eadeddce8ba9c50afc8d07fc "$power" | sha256sum -c -
python3 -B - "$power" "$work/paired-power.sh" <<'PY'
from pathlib import Path
import sys

source, target = map(Path, sys.argv[1:])
text = source.read_text()
changes = {
    'gate=$runs/gate-c380-routed-02/c380-gate-116908': 'gate=$bundle/idle-$job',
    'replay=$gate/replay-116908': 'replay=$gate/replay-$job',
    'for mode in 0 1; do\n    sample=$out/mode-$mode': 'for mode in mode-0 mode-1 idle-0 idle-1; do\n    sample=$out/$mode',
    '$replay/mode-$mode/': '$replay/$mode/',
    'if "\\nPASS typed AttentionCore " not in text or': 'if not any(marker in text for marker in ("\\nPASS typed AttentionCore ", "\\nIDLE SRAM WINDOW COMPLETE\\n")) or',
    '"$out"/mode-*/{functional.json,openroad/receipt.json,openroad/power.log}': '"$out"/{mode,idle}-*/{functional.json,openroad/receipt.json,openroad/power.log}',
    'C380_ROUTED_ACTIVE_POWER_PASS': 'C380_PAIRED_POWER_ANNOTATION_PASS',
}
for before, after in changes.items():
    if before not in text:
        raise ValueError(before)
    text = text.replace(before, after)
target.write_text(text)
PY
bash -n "$work/paired-power.sh"
srun --exact -N1 -n1 -c "$SLURM_CPUS_PER_TASK" \
  /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind "$base" \
  --env "SLURM_SUBMIT_DIR=$bundle" "$base/opt/eda/containers/orfs-current-repacked.sif" \
  bash "$work/paired-power.sh" container "$job" "$SLURM_CPUS_PER_TASK"

python3 -B - "$bundle/power-$job" <<'PY'
import json
from pathlib import Path
import re
import sys

out = Path(sys.argv[1])
leaf = "TOP/test_native_attention_core_scope/storage"

def checkpoint(vcd, idle):
    names = {}
    queue = set()
    trace = {}
    active_inputs = {"req_valid": "0", "req_write": None, "req_addr": None, "req_data": None}
    stack = []
    first = None
    time = None
    initial = None
    for line in vcd.open():
        f = line.split()
        if f[:1] == ["$scope"]:
            stack.append(f[2])
        elif f[:1] == ["$upscope"]:
            stack.pop()
        elif f[:1] == ["$var"]:
            scope = "/".join(stack)
            label = scope + "/" + f[4]
            if scope == leaf or scope.startswith(leaf + "/"):
                names[label] = f[3]
                if scope == leaf and f[4] in active_inputs or re.fullmatch(re.escape(leaf) + r"/storage\.banks\[\d+\]\.memory/csb0", label):
                    queue.add(label)
        elif line.startswith("#"):
            time = int(line[1:])
            if first is None:
                first = time
            elif initial is None:
                initial = {name: trace[identifier] for name, identifier in names.items()}
                if not idle:
                    break
            if idle and time >= first + 10000:
                for label in queue:
                    observed = trace[names[label]]
                    default = active_inputs.get(label.rsplit("/", 1)[1], "1")
                    expected = initial[label] if default is None else default
                    if observed != expected:
                        raise ValueError(f"idle SRAM request or bank activation at {time}: {label}={observed}, expected {expected}")
        elif line[:1] in ("0", "1", "x", "z"):
            trace[line[1:].strip()] = line[0]
        elif line.startswith("b"):
            value, identifier = f
            trace[identifier] = value[1:]
    macro_words = sum(bool(re.fullmatch(re.escape(leaf) + r"/storage\.banks\[\d+\]\.memory/mem\[\d+\]", name)) for name in names)
    if len(queue) != 8 or macro_words != 1024 or not initial:
        raise ValueError(f"checkpoint incomplete: observed {len(queue)} controls and {macro_words} macro words")
    return initial, macro_words

results = []
for mode in (0, 1):
    active_scope = out / f"mode-{mode}"
    idle_scope = out / f"idle-{mode}"
    active, words = checkpoint(active_scope / "gate.vcd", False)
    idle, _ = checkpoint(idle_scope / "gate.vcd", True)
    if active != idle:
        raise ValueError(f"active and idle leaf checkpoint states differ for mode {mode}")
    ap, ip = [json.loads((sample / "openroad/receipt.json").read_text())["power_w"]["total"] for sample in (active_scope, idle_scope)]
    results.append({"mode": mode, "same_checkpoint_signals": len(active), "same_sram_words": words,
                    "idle_first_cycle_drain_ps": 10000, "window_ps": 20480000,
                    "active_total_w": ap, "idle_total_w": ip, "incremental_window_j": (ap - ip) * 20.48e-6})
text = json.dumps(results, indent=2) + "\n"
(out / "paired.json").write_text(text)
print(text, end="")
PY
sha256sum "$work/"{idle-source.sha256,gate-results.sha256,paired-power.sh} \
  "$bundle/power-$job/"{power-results.sha256,paired.json} > "$work/idle-results.sha256"
sha256sum -c "$work/idle-results.sha256"
printf '%s\n' C380_SAME_CHECKPOINT_IDLE_PASS
