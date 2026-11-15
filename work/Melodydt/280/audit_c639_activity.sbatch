#!/usr/bin/env bash
#SBATCH --job-name=mdt-280c639a
#SBATCH --partition=c64,c96
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --time=00:10:00
#SBATCH --output=slurm-audit-%j.log
set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?}"
capture=${1:?provide completed capture job ID}
[[ $capture =~ ^[0-9]+$ ]]
old=/public/home/yuzelu/Melodydt/runs/issue-274/pr272-ffn-native-01/run-115347/replay-115347
work=$PWD/c639-$capture
out=$work/replay-$capture
audit=$PWD/audit-$capture-$SLURM_JOB_ID
mkdir "$audit"
sha256sum -c audit-input.sha256
sha256sum -c "$work/activity-source.sha256"
(cd "$out" && sha256sum --quiet -c proof.sha256)
(cd "$old" && sha256sum -c ffn-wait.sha256)
for mode in 0 1; do
    raw=$audit/ffn-wait-$mode.log
    grep -E '^(M_WEIGHT|FFN_LC|FFN_EXEC|FFN_SCOPE|FFN_WAIT) ' "$out/replay-$mode.log" > "$raw"
    python3 -B compare_c639_events.py "$old/ffn-wait-$mode.log" "$raw" > "$audit/events-$mode.json"
    diff <(grep '^PASS q projection ' "$old/replay-$mode.log") <(grep '^PASS q projection ' "$out/replay-$mode.log")
    for f in transactions.tsv write-transactions.tsv activation-transactions.tsv committed-kv.bin; do
        cmp "$old/DDR-$mode/$f" "$out/DDR-$mode/$f"
    done
    diff <(sed 's/^/C639_ACTIVITY /' "$work/activity-$mode.txt") <(grep '^C639_ACTIVITY ' "$out/replay-$mode.log")
    test -s "$out/DDR-$mode/ffn-gate-up.fst"
    test -s "$out/DDR-$mode/ffn-down.fst"
    grep -E '^(C639_ACTIVITY|PASS q projection) ' "$out/replay-$mode.log"
done
sha256sum "$work/activity-source.sha256" "$out/proof.sha256" "$out"/DDR-*/ffn-*.fst \
    "$audit"/*.log "$audit"/events-*.json "$PWD/audit-input.sha256" > "$audit/activity-results.sha256"
sha256sum -c "$audit/activity-results.sha256"
