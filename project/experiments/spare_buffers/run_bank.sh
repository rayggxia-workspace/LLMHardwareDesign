#!/usr/bin/env bash
set -euo pipefail
source /OpenROAD-flow-scripts/env.sh
export PLATFORM_DIR=/OpenROAD-flow-scripts/flow/platforms/nangate45
export QT_QPA_PLATFORM=offscreen
script=$(cd "$(dirname "$0")" && pwd -P)
cp "$script/bank.v" .
export PIN_RANK
PIN_RANK=${1:-0}
openroad -no_init -exit "$script/route_bank.tcl" > bank-openroad.log 2>&1
grep -qx BANK_ROUTE_OK bank-openroad.log
p=$PLATFORM_DIR
util=/OpenROAD-flow-scripts/flow/util
sed "s@\./NangateOpenCellLibrary.mod.lef@$p/lef/NangateOpenCellLibrary.tech.lef</lef-files><lef-files>$p/lef/NangateOpenCellLibrary.macro.mod.lef@" \
    "$p/FreePDK45.lyt" > bank.lyt
klayout -b -r "$util/def2stream.py" -rd tech_file=bank.lyt -rd layer_map= \
    -rd in_def=bank.def -rd design_name=spare_bank -rd in_files="$p/gds/NangateOpenCellLibrary.gds" \
    -rd seal_file= -rd out_file=bank.gds > bank-stream.log 2>&1
klayout -b -r "$p/drc/FreePDK45.lydrc" -rd in_gds=bank.gds \
    -rd report_file=bank.lyrdb > bank-drc.log 2>&1
klayout -b -r "$script/verify_bank.py" -rd input_gds=bank.gds -rd ports_tsv=bank-ports.tsv \
    -rd cells_tsv=bank-cells.tsv -rd receipt_file=bank-connectivity.json > bank-connectivity.log 2>&1
python3 -B - bank.lyrdb <<'PY'
import sys
from collections import Counter
from xml.etree import ElementTree as ET

items = ET.parse(sys.argv[1]).findall('./items/item')
print(dict(Counter(item.findtext('category') for item in items)))
raise SystemExit(bool(items))
PY
