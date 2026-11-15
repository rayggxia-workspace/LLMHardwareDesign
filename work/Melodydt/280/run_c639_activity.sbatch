#!/usr/bin/env bash
#SBATCH --job-name=mdt-280c639
#SBATCH --partition=c64,c96
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=12
#SBATCH --time=01:10:00
#SBATCH --output=slurm-%j.log
set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?}"
bundle=$PWD
base=/public/home/yuzelu
project=$base/project-circuit
archive=$base/Melodydt/runs/issue-274/pr272-ffn-native-01
old=$archive/run-115347/replay-115347
work=$bundle/c639-$SLURM_JOB_ID
fixture=project/experiments/block_local_native
sha256sum -c bundle.sha256
(cd "$archive" && sha256sum -c run-115347/source.sha256)
(cd "$old" && sha256sum -c ffn-wait.sha256)
mkdir "$work"
cp -a "$archive/run-115347/source" "$archive/run-115347/source.tar" "$work/"
cp "$bundle/c639_activity_driver.cpp" "$work/source/$fixture/"
python3 -B - "$work" "$old" <<'PY'
from pathlib import Path
import sys

work, baseline = map(Path, sys.argv[1:])
for mode in (0, 1):
    calls = {0: {}, 58: {}}
    events = (baseline / ("ffn-wait-%d.log" % mode)).open()
    with events:
        for line in events:
            fields = line.split()
            if fields[:2] == ["FFN_SCOPE", "call"] and fields[2].startswith("00000005"):
                group = int(fields[4])
                if group in calls:
                    target = int(fields[3])
                    if target in calls[group]:
                        raise ValueError("duplicate scope call in archived C639")
                    calls[group][target] = int(fields[5])
    rows = []
    for group, name in ((0, "gate-up"), (58, "down")):
        if set(calls[group]) != {0, 1, 2}:
            raise ValueError("C639 sample must start at a complete three-target wave")
        start = min(calls[group].values()) * 1000
        rows.append("{} {} {}\n".format(name, start, start + 81920000))
    (work / ("activity-%d.txt" % mode)).write_text("".join(rows))

runner = work / "source/project/experiments/block_local_native/run_decode638_q_tile_replay.sh"
text = runner.read_text()
for old,new in (
    ("--binary --timing", "--cc --exe --build --trace-fst --trace-depth 4 --timing"),
    ('"$PWD/$EXP/ddr_read_bridge.cpp" --Mdir', '"$PWD/$EXP/ddr_read_bridge.cpp" "$PWD/$EXP/c639_activity_driver.cpp" --Mdir'),
    ('"+DDR_CONFIG=$basis/DDR4-single-channel.ini" "+DDR_OUTPUT=$case_dir/DDR-$mode" "${runtime[@]}"',
     '"+DDR_CONFIG=$basis/DDR4-single-channel.ini" "+DDR_OUTPUT=$case_dir/DDR-$mode" "+CAPTURE_SCHEDULE=$run/activity-$mode.txt" "${runtime[@]}"'),
):
    if text.count(old) != 1:
        raise ValueError("ambiguous C639 trace anchor: " + old)
    text = text.replace(old,new)
runner.write_text(text)
PY
runner="$work/source/$fixture/run_decode638_q_tile_replay.sh"
bash -n "$runner"
sha256sum "$runner" "$work/source/$fixture/c639_activity_driver.cpp" "$work"/activity-*.txt > "$work/activity-source.sha256"
srun --exact -N1 -n1 -c "$SLURM_CPUS_PER_TASK" --cpu-bind=cores \
    /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind "$base" \
    --env "SLURM_JOB_ID=$SLURM_JOB_ID,SLURM_CPUS_PER_TASK=$SLURM_CPUS_PER_TASK,FORCE_SECOND_FFN_REARM=1" \
    "$base/opt/eda/containers/orfs-current-repacked.sif" bash "$runner" "$work" \
    "$project/issue260-token-decode638-live-qkv-xWSJhdWQ/linked-103952" history-final-product-ffn-repeat 636 2
out=$work/replay-$SLURM_JOB_ID
(cd "$out" && sha256sum --quiet -c proof.sha256)
for mode in 0 1; do
    grep -E '^(M_WEIGHT|FFN_LC|FFN_EXEC|FFN_SCOPE|FFN_WAIT) ' "$out/replay-$mode.log" > "$out/ffn-wait-$mode.log"
    cmp "$old/ffn-wait-$mode.log" "$out/ffn-wait-$mode.log"
    diff <(grep '^PASS q projection ' "$old/replay-$mode.log") <(grep '^PASS q projection ' "$out/replay-$mode.log")
    for f in transactions.tsv write-transactions.tsv activation-transactions.tsv committed-kv.bin; do
        cmp "$old/DDR-$mode/$f" "$out/DDR-$mode/$f"
    done
    grep '^C639_ACTIVITY ' "$out/replay-$mode.log"
    test -s "$out/DDR-$mode/ffn-gate-up.fst"
    test -s "$out/DDR-$mode/ffn-down.fst"
done
sha256sum "$work/activity-source.sha256" "$out/proof.sha256" "$out"/DDR-*/ffn-*.fst "$out"/ffn-wait-*.log > "$work/activity-results.sha256"
sha256sum -c "$work/activity-results.sha256"
