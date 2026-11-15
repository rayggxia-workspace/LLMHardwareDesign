#!/bin/bash
set -euo pipefail
framework=$1
archive=$2
sidecar=$3
out="$PWD/evidence/archived-stage-diagnostic-$SLURM_JOB_ID"
mkdir "$out"
codecs=/public/home/yuzelu/project-circuit/issue250-u-n32-stored-link-20261112-01/staged/project
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
export PYTHONPATH="$PWD/algo1:$framework:$codecs/control_image_v0_1:$codecs/control_isa_v0_1"
python3.11 -B compile_full_native.py "$archive" "$out/replan"
python3.11 -B audit_full_native.py "$archive" "$sidecar" algo1/blockv2-mod.json "$out/admission"
python3.11 -B package_full_native.py "$archive" "$out/admission" "$out/replan" "$out/package"
python3.11 -B validate_instruction_package.py "$out/package"
