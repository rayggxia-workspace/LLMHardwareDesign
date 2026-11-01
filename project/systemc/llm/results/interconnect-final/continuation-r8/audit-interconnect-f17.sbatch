#!/bin/bash
#SBATCH --job-name=yzl-sc153-flowaudit
#SBATCH --partition=c64
#SBATCH --nodelist=node4
#SBATCH --cpus-per-task=6
#SBATCH --time=00:30:00
set -euo pipefail
ROOT=/public/home/yuzelu/project-circuit/LLMHardwareDesign/systemc-llm-issue153
export PYTHONDONTWRITEBYTECODE=1
python3 "$ROOT/continuation-r8/audit-interconnect-f17.py" "$ROOT" "$ROOT/continuation-r8/interconnect-cases-f17.json" "$ROOT/continuation-r8/interconnect-audit-f17.json"
