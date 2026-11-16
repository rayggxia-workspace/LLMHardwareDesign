#!/usr/bin/env bash
set -euo pipefail
script=$(cd "$(dirname "$0")" && pwd -P)
if [[ $# -lt 2 || "$1" == --help || "$1" == -h ]]; then
    printf '%s\n' +        'Usage: bash run.sh BASE_MANIFEST.json NEW_OUTPUT_DIR [BANK_LIMIT=0] [PITCH_UM=56,64]' +        '       bash run.sh --pr271 PLACEMENT.json ARCHIVE_BASE.json NEW_OUTPUT_DIR [BANK_LIMIT=0] [PITCH_UM=56,64]'
    exit 0
fi
input_files=()
if [[ "$1" == --pr271 ]]; then
    shift
    placement=$(realpath -e "$1")
    archive=$(realpath -e "$2")
    input_files=("$placement" "$archive")
    shift 2
else
    manifest=$(realpath -e "$1")
    input_files=("$manifest")
    shift
fi
mkdir "$1"
cd "$1"
count=${2:-0}
pitch=${3:-56,64}
mkdir tmp
export TMPDIR="$PWD/tmp" XDG_CACHE_HOME="$PWD/tmp" PYTHONDONTWRITEBYTECODE=1
export QT_QPA_PLATFORM=offscreen
source /OpenROAD-flow-scripts/env.sh
openroad -version > tools.txt
klayout -v >> tools.txt
sha256sum "${input_files[@]}" "$script"/*.{tcl,v,sh,py} > inputs.sha256

bank=""
for rank in 0 1 2; do
    mkdir "bank-$rank"
    if (cd "bank-$rank" && bash "$script/run_bank.sh" "$rank") > "bank-$rank.log" 2>&1; then
        bank="$PWD/bank-$rank"
        break
    fi
done
if [[ -z "$bank" ]]; then
    echo "No bank passed routing and verification. See bank-*.log and bank-*/." >&2
    exit 1
fi
if [[ -v manifest ]]; then
    args=(-rd "manifest_file=$manifest")
else
    mkdir leaves
    (cd leaves && bash "$script/prepare_pr271.sh" "$placement" "$archive") > leaves.log 2>&1
    args=(-rd "placement_file=$placement" -rd "archive_file=$archive" -rd "views_tsv=$PWD/leaves/views.tsv")
fi
mkdir merged
cd merged
klayout -b -r "$script/place_banks.py" "${args[@]}" \
    -rd "bank_gds=$bank/bank.gds" -rd "bank_ports=$bank/bank-ports.tsv" \
    -rd "pitch_um=$pitch" -rd "limit=$count" -rd "output_dir=$PWD" > merge.log 2>&1
klayout -b -r "$script/verify_merged.py" -rd "output_dir=$PWD" -rd "bank_gds=$bank/bank.gds" > verify.log 2>&1
klayout -b -r /OpenROAD-flow-scripts/flow/platforms/nangate45/drc/FreePDK45.lydrc \
    -rd in_gds=spare-overlay.oas -rd report_file=overlay.lyrdb > overlay-drc.log 2>&1
python3 -B - overlay.lyrdb <<'PY'
import sys
from xml.etree import ElementTree as ET

count = len(ET.parse(sys.argv[1]).findall("./items/item"))
print(f"Overlay DRC violations: {count}")
raise SystemExit(bool(count))
PY
sha256sum base-with-spares.oas spare-overlay.oas m10-ports.tsv banks.tsv summary.json \
    stream-verification.json overlay.lyrdb > outputs.sha256
