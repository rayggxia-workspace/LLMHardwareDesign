set -euo pipefail
source /OpenROAD-flow-scripts/env.sh
python3 source/project/experiments/s_sram/physical.py --generation /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-155/bank-views-003/generation --out "$PWD/implementation"
