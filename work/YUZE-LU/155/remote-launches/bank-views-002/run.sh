set -euo pipefail
source /OpenROAD-flow-scripts/env.sh
python3 source/project/experiments/s_sram/assemble_eco_views.py --generation /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-155/generate-008/generation --eco /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-155/bank-eco-002 --model-test /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-155/actual-model-008/test/receipt.json --out "$PWD/generation"
