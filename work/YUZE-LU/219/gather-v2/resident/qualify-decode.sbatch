#!/usr/bin/env bash
set -euo pipefail
cd "$1"
g="$2"; base="$3"; stored="$4"; place="$5"; dma="$6"
r=/public/home/yuzelu/project-circuit/issue250-u-n32-stored-link-20261112-01/staged/project
router=/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search/framework-20261114-akeox2em/router-current/project/experiments/upper_router
py=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python
export PYTHONPATH="$PWD:$g:$r/control_image_v0_1:$r/control_isa_v0_1:$router"
sha256sum -c "$place/artifacts.sha256"
"$py" -B qualify_decode_links.py "$base" "$stored" "$place" "$dma" request-110369/local-sidecars.json "geometry-$SLURM_JOB_ID"
sha256sum "geometry-$SLURM_JOB_ID/"{summary.json,geometry-requirements.json}
