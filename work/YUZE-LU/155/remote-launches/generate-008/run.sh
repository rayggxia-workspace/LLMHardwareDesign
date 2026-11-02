set -euo pipefail
source /OpenROAD-flow-scripts/env.sh
export PATH=/public/home/yuzelu/opt/eda/issue155-sram/bin:$PATH
export PYTHONPATH=/public/home/yuzelu/opt/eda/issue155-sram/overlays/views-001:/public/home/yuzelu/opt/eda/issue155-sram/python
python3 source/project/experiments/s_sram/ngspice_runtime_overlay.py --source /public/home/yuzelu/opt/eda/issue155-sram/overlays/views-001/openram --out /public/home/yuzelu/opt/eda/issue155-sram/overlays/generate-008/openram --receipt "$PWD/runtime-overlay.json"
export PYTHONPATH=/public/home/yuzelu/opt/eda/issue155-sram/overlays/generate-008:/public/home/yuzelu/opt/eda/issue155-sram/python
export OPENRAM_HOME=/public/home/yuzelu/opt/eda/issue155-sram/overlays/generate-008/openram/compiler
export OPENRAM_TMP="$PWD/openram-temp"
export TMPDIR="$PWD/tmp"
export S_SRAM_RUNTIME_OVERLAY_RECEIPT="$PWD/runtime-overlay.json"
mkdir -p "$OPENRAM_TMP" "$TMPDIR"
python3 -u source/project/experiments/s_sram/generate_bank.py --compiler /public/home/yuzelu/opt/eda/issue155-sram/overlays/generate-008/openram/sram_compiler.py --out "$PWD/generation" --internal-pins --delay-chain-stages 49 --spice-threads 8
