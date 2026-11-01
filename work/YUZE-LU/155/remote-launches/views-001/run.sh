set -euo pipefail
source /OpenROAD-flow-scripts/env.sh
python3 source/project/experiments/s_sram/simulator_overlay.py --source /public/home/yuzelu/opt/eda/issue155-sram/overlays/generate-007/openram --out /public/home/yuzelu/opt/eda/issue155-sram/overlays/views-001/openram --receipt "$PWD/simulator-overlay.json"
export PYTHONPATH=/public/home/yuzelu/opt/eda/issue155-sram/overlays/views-001:/public/home/yuzelu/opt/eda/issue155-sram/python
export OPENRAM_HOME=/public/home/yuzelu/opt/eda/issue155-sram/overlays/views-001/openram/compiler
export PATH=/public/home/yuzelu/opt/eda/issue155-sram/bin:$PATH
export OPENRAM_TMP="$PWD/openram-temp"
export TMPDIR="$PWD/tmp"
mkdir -p "$OPENRAM_TMP" "$TMPDIR"
python3 source/project/experiments/s_sram/views_from_routed.py --routed-lvs /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-155/macro-lvs-001 --original-generation /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-155/generate-007/generation --out "$PWD/generation"
