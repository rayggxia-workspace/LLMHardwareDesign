set -euo pipefail
source /OpenROAD-flow-scripts/env.sh
python3 source/project/experiments/s_sram/assemble_eco_views.py --generation /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-155/generate-009/generation --eco /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-155/bank-eco-004 --model-test /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-155/actual-model-009/test/receipt.json --refined-lef /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-155/lef-refinement-003 --out "$PWD/generation"
