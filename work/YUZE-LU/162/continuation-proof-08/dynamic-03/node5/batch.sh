#!/usr/bin/env bash
set -euo pipefail
python3 /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/dynamic-03/node5/queue-race-control.py
exec bash /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/source-83/project/experiments/control_v1/dynamic_queue.sh /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/source-83 /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/dynamic-03/node5
