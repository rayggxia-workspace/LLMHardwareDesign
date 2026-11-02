set -euo pipefail
source /OpenROAD-flow-scripts/env.sh
python3 source/project/experiments/s_sram/formal_banks.py --physical /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-155/physical-014/implementation --out "$PWD/proof"
