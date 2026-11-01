set -euo pipefail
source /OpenROAD-flow-scripts/env.sh
export PATH=/public/home/yuzelu/opt/eda/issue155-sram/bin:$PATH
export PYTHONPATH=/public/home/yuzelu/opt/eda/issue155-sram/overlays/generate-008:/public/home/yuzelu/opt/eda/issue155-sram/python
export OPENRAM_HOME=/public/home/yuzelu/opt/eda/issue155-sram/overlays/generate-008/openram/compiler
export OMP_NUM_THREADS=8
python3 -u run_cases.py
