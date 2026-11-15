#!/usr/bin/env bash
#SBATCH --job-name=mdt-280pg639
#SBATCH --partition=c64,c96
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --time=00:20:00
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
      bash "$bundle/run_c639_g32_power.sbatch" container "$SLURM_JOB_ID" "$SLURM_CPUS_PER_TASK" "${G32_PREFLIGHT:-0}"
fi
source /OpenROAD-flow-scripts/env.sh
job=$2
cores=$3
preflight=$4
out=$bundle/power-$job
root=$base/Melodydt/runs/issue-280/c639-g32-gate-01/c639-g32-116937
replay=$root/replay-116937
project=$base/project-circuit/LLMHardwareDesign
delivery=$project/issue-250-g-physical-20261111-08/delivery
analyzer=$project/issue-234-systemc-benchmark/s-activity-002/analyze_activity.py
fst=$base/opt/eda/verilator-5.042/share/verilator/include/gtkwave
scope=TOP/test_native_decode638_product_replay/feed_forward/dut/G
lib=/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib
mkdir -p "$out/physical-100mhz"
if [[ $preflight == 1 ]]; then
    cases=(0:gate-up)
else
    (cd "$root" && sha256sum --quiet -c gate-results.sha256)
    (cd "$replay" && sha256sum --quiet -c proof.sha256)
    cases=(0:gate-up 0:down 1:gate-up 1:down)
fi
printf '%s  %s\n' \
    8d540a4d4cf6d09d27c87ad067857a9c0c2eeb023ab7a56e058cd3113db4e9b1 "$lib" \
    93134a119f0950a684e297e93add809985579553a365feb667aae67e6ce46764 "$delivery/6_final.v" \
    bd2a412c60721453079da42afd232c6b7fb95d73b7cbe27329c7b09aa7e15189 "$delivery/6_final.odb" \
    ef69b74b329a39c75987dc1c292c13321db396e0744fc774ad4272d8edc6cee0 "$delivery/6_final.spef" \
    d817b123b91904f7dd2f6f5a53937dd7dbe058474dcd7acdba5115a9d6e0da65 "$delivery/6_final.sdc" > "$out/physical.sha256"
sha256sum -c "$out/physical.sha256"
for ext in v odb spef; do ln -s "$delivery/6_final.$ext" "$out/physical-100mhz/"; done
grep -Fx 'create_clock -name core -period 3.33333333333 [get_ports clk]' "$delivery/6_final.sdc"
sed '/^create_clock -name core -period /s/3\.33333333333/10.0000/' "$delivery/6_final.sdc" > "$out/physical-100mhz/6_final.sdc"
openroad -version > "$out/openroad-version.txt"
sha256sum "$(command -v openroad)" "$analyzer" "$fst"/{fstapi.c,fstapi.h,fst_config.h,fastlz.c,lz4.c} > "$out/tools.sha256"

cat > "$out/fst_scope_vcd.c" <<'C'
#include "fstapi.h"
#include <stdio.h>
#include <string.h>

int main(int argc, char **argv) {
    if (argc != 4) return 1;
    fstReaderContext *reader = fstReaderOpen(argv[1]);
    if (!reader || fstReaderGetTimescale(reader) != -12 ||
        fstReaderGetEndTime(reader) - fstReaderGetStartTime(reader) != 81920000) return 2;
    FILE *vcd = fopen(argv[2], "w");
    if (!vcd || !fstReaderProcessHier(reader, vcd)) return 3;
    const char *target = argv[3];
    const size_t target_size = strlen(target);
    char current[4096] = {0};
    size_t lengths[128], depth = 0, size = 0, selected = 0;
    fstReaderIterateHierRewind(reader);
    struct fstHier *entry;
    while ((entry = fstReaderIterateHier(reader))) {
        if (entry->htyp == FST_HT_SCOPE) {
            const char *name = entry->u.scope.name;
            const size_t width = strlen(name);
            if (depth == 128 || size + width + 1 >= sizeof(current)) return 4;
            lengths[depth++] = size;
            if (size) current[size++] = '/';
            memcpy(current + size, name, width + 1);
            size += width;
        } else if (entry->htyp == FST_HT_UPSCOPE) {
            if (!depth) return 4;
            size = lengths[--depth];
            current[size] = 0;
        } else if (entry->htyp == FST_HT_VAR && strncmp(current, target, target_size) == 0 &&
                   (current[target_size] == 0 || current[target_size] == '/')) {
            fstReaderSetFacProcessMask(reader, entry->u.var.handle);
            ++selected;
        }
    }
    printf("G32_SCOPE_SIGNALS %zu\n", selected);
    if (selected <= 13) return 5;
    const int ok = fstReaderIterBlocks(reader, NULL, NULL, vcd);
    const int write_failed = ferror(vcd);
    fstReaderClose(reader);
    const int close_failed = fclose(vcd);
    return !ok || write_failed || close_failed;
}
C
gcc -std=gnu11 -O2 -D_GNU_SOURCE -I"$fst" -include "$fst/fst_config.h" \
    "$out/fst_scope_vcd.c" "$fst"/{fstapi,fastlz,lz4}.c -lz -o "$out/fst_scope_vcd"

for name in "${cases[@]}"; do
    mode=${name%:*}
    phase=${name#*:}
    sample=$out/mode-$mode-$phase
    mkdir "$sample"
    wave=$replay/DDR-$mode/ffn-$phase.fst
    sha256sum "$wave" > "$sample/wave.sha256"
    "$out/fst_scope_vcd" "$wave" "$sample/raw.vcd" "$scope" | tee "$sample/scope.txt"
    python3 -B - "$sample" "$root/activity-$mode.txt" "$phase" "$scope" <<'PY'
import json
from pathlib import Path
import sys

sample, schedule = map(Path, sys.argv[1:3])
phase, scope = sys.argv[3], sys.argv[4].split("/")
start, end = next([int(x) for x in line.split()[1:]] for line in schedule.read_text().splitlines() if line.split()[0] == phase)
target_ports = {"clk", "in_valid", "in_ready", "out_valid", "out_ready"}
with (sample / "raw.vcd").open() as src, (sample / "gate.vcd").open("w") as dst:
    paths = []
    selected = []
    ids = {}
    time = None
    last = None
    clock = []
    for line in src:
        fields = line.split()
        command = fields[0] if fields else ""
        if command == "$timescale":
            while fields[-1] != "$end":
                fields.extend(next(src).split())
            if fields != ["$timescale", "1ps", "$end"]:
                raise ValueError(fields)
            line = " ".join(fields) + "\n"
        elif command == "$scope":
            paths.append(fields[2])
            within = paths == scope[:len(paths)] or paths[:len(scope)] == scope
            selected.append(within)
            if not within:
                continue
        elif command == "$upscope":
            paths.pop()
            if not selected.pop():
                continue
        elif command == "$var":
            if paths[:len(scope)] != scope:
                continue
            if paths == scope and fields[4] in target_ports:
                ids[fields[4]] = fields[3]
            if fields[1] in ("logic", "bit", "int"):
                fields[1] = "wire"
                line = " ".join(fields) + "\n"
        elif line.startswith("#"):
            time = int(line[1:])
        elif line[:1] in ("0", "1") and line[1:].strip() == ids.get("clk") and line[0] != last:
            clock.append(time)
            last = line[0]
        dst.write(line)
if set(ids) != target_ports or clock != list(range(start, end + 1, 5000)) or time != end:
    raise ValueError("G32 clock, ports or frozen window did not match")
(sample / "functional.json").write_text(json.dumps({"timing": {"passed": True, "window_ps": end - start,
    "clock_period_ps": 10000, "clock_transitions": len(clock) - 1, "first_ps": start, "last_ps": end}}, indent=2) + "\n")
PY
    python3 -B "$analyzer" "$out/physical-100mhz" "$lib" "$sample/gate.vcd" "$sample/functional.json" \
      "$sample/openroad" --scope "$scope" --cores "$cores" --escape-sta-backslashes --sample-label 'C639 G32 leaf'
done
sha256sum "$out"/{physical.sha256,tools.sha256,openroad-version.txt,fst_scope_vcd.c,physical-100mhz/6_final.sdc} \
    "$out"/mode-*/{scope.txt,functional.json,wave.sha256,openroad/receipt.json,openroad/power.log} > "$out/power-results.sha256"
sha256sum -c "$out/power-results.sha256"
if [[ $preflight == 1 ]]; then printf '%s\n' C639_G32_POWER_PREFLIGHT_PASS; else printf '%s\n' C639_G32_FOUR_WINDOWS_POWER_PASS; fi
