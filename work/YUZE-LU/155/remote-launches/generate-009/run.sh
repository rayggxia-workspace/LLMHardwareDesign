set -euo pipefail
source /OpenROAD-flow-scripts/env.sh
export PATH=/public/home/yuzelu/opt/eda/issue155-sram/bin:$PATH
export PYTHONPATH=/public/home/yuzelu/opt/eda/issue155-sram/overlays/generate-008:/public/home/yuzelu/opt/eda/issue155-sram/python
export OPENRAM_HOME=/public/home/yuzelu/opt/eda/issue155-sram/overlays/generate-008/openram/compiler
export OPENRAM_TMP="$PWD/openram-temp"
export TMPDIR="$PWD/tmp"
export S_SRAM_RUNTIME_OVERLAY_RECEIPT="/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-155/generate-008/runtime-overlay.json"
mkdir -p "$OPENRAM_TMP" "$TMPDIR"
python3 -u source/project/experiments/s_sram/generate_bank.py --compiler /public/home/yuzelu/opt/eda/issue155-sram/overlays/generate-008/openram/sram_compiler.py --out "$PWD/generation" --internal-pins --words-per-row 2 --delay-chain-stages 25 --spice-threads 8
