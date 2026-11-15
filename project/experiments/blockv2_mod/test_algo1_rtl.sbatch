#!/bin/bash
set -euo pipefail
f=$1
py=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python
export PYTHONPATH="$PWD/algo1:$f"
export PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
"$py" -B -m unittest test_publish_event_handoff test_event_loop_memory
