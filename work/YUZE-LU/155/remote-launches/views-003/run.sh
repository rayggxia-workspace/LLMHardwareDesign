set -euo pipefail
source /OpenROAD-flow-scripts/env.sh
test -f /public/home/yuzelu/opt/eda/issue155-sram/overlays/views-001/openram/compiler/characterizer/stimuli.py
export PYTHONPATH=/public/home/yuzelu/opt/eda/issue155-sram/overlays/views-001:/public/home/yuzelu/opt/eda/issue155-sram/python
export OPENRAM_HOME=/public/home/yuzelu/opt/eda/issue155-sram/overlays/views-001/openram/compiler
export PATH=/public/home/yuzelu/opt/eda/issue155-sram/bin:$PATH
export OPENRAM_TMP="$PWD/openram-temp"
export TMPDIR="$PWD/tmp"
mkdir -p "$OPENRAM_TMP" "$TMPDIR"
python3 -u source/project/experiments/s_sram/views_from_routed.py --routed-lvs /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-155/macro-lvs-001 --original-generation /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-155/generate-007/generation --out "$PWD/generation"
