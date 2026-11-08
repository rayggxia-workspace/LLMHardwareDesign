#!/usr/bin/env bash
set -euo pipefail
export PATH="/OpenROAD-flow-scripts/tools/install/OpenROAD/bin:/usr/local/bin/wrapped-cc:$PATH"
src="$PWD/project/experiments/m11_m12_rcx"
stage=$1
shift
case "$stage" in
  build)
    python3 -B "$src/build_native_field.py" "$COUPLING_OUT/build" "$@"
    python3 -B "$src/native_controls.py" "$COUPLING_OUT/build/native_field" "$COUPLING_OUT/controls" \
      /public/home/yuzelu/PingyangHuang/issue-222-field-tUoIruxn/job-100108/controls \
      /public/home/yuzelu/PingyangHuang/issue-222-field-KYcdk1xs/job-100130/build/native_field
    ;;
  export)
    export COUPLING_TOPOLOGIES="${1:?topology manifest}"
    export COUPLING_MIN_LAYER="${2:?lowest native metal}"
    klayout -b -r "$src/native_context.py"
    ;;
  solve)
    python3 -B "$src/native_run.py" "$@"
    ;;
  flux-check)
    export COUPLING_FLUX_SOLVER="${1:?solver}"
    python3 -B "$src/native_flux_check.py"
    ;;
  flux-refine)
    export COUPLING_FLUX_SOLVER="${1:?solver}" COUPLING_FLUX_REFERENCE="${2:?reference}"
    python3 -B "$src/native_flux_refine.py"
    ;;
  compare)
    python3 -B "$src/native_compare.py" "$@"
    ;;
  drivers)
    python3 -B "$src/native_drivers.py"
    ;;
  assess)
    python3 -B "$src/native_assess.py" "$@"
    ;;
  shared-reference)
    python3 -B "$src/native_shared_reference.py" "$@"
    ;;
  shared-controls)
    export COUPLING_SHARED_SOLVER="${1:?solver}"
    python3 -B "$src/native_shared_controls.py"
    ;;
  reciprocity)
    python3 -B "$src/native_reciprocity.py" "$@"
    ;;
  macro-boundary)
    python3 -B "$src/native_macro_boundary.py" "$@"
    ;;
  contacts)
    python3 -B "$src/native_contact_check.py" "$@"
    ;;
  baseline-check)
    python3 -B "$src/native_baseline_check.py" "$@"
    ;;
  *) echo "Unknown native stage: $stage" >&2; exit 2 ;;
esac
