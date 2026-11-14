#!/usr/bin/env bash
set -euo pipefail
cd "$1"
g="$2"; d="$3"; admission="$4"
root=/public/home/yuzelu/project-circuit
a="$root/issue250-u-n32-stored-link-20261112-01/staged/project"
mc="$root/issue234-native-fixed-skip-request-H2gY5uiN/source/project/experiments/mother_control_native"
py=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python
m="$d/mother-ingress-sNMsK9"; gather="$m/link-110415/request-link.json"
export PYTHONPATH="$PWD:$m:$d:$g:$a/control_isa_v0_1:$mc"
"$py" -B link_vocabulary_retirement.py "$g/../request-runtime-r2" "$gather" "$admission" "link-$SLURM_JOB_ID"
sha256sum "link-$SLURM_JOB_ID/retirement-link.json" link_vocabulary_retirement.py
