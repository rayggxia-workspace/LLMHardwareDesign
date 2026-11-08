#!/usr/bin/env bash
set -euo pipefail
source_root=$1
candidate=$2
cpus=${SLURM_CPUS_PER_TASK:?}
root=$(dirname "$candidate")
tmp=$root/audit-tmp-$SLURM_JOB_ID
mkdir -p "$tmp"
exec srun --exact --ntasks=1 --cpus-per-task="$cpus" --cpu-bind=cores \
    /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv \
    --bind /public/home/yuzelu --pwd "$source_root" \
    --env "TMPDIR=$tmp,OMP_NUM_THREADS=$cpus,QT_QPA_PLATFORM=offscreen" \
    /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif \
    bash -c '
        set -euo pipefail
        source /OpenROAD-flow-scripts/env.sh
        export PU_CANDIDATE="$1"
        top=$(find "$PU_CANDIDATE/flow/results" -name 6_final.odb)
        test -f "$top"
        export PU_FINAL_ODB="$top" PU_FINAL_SDC="${top%.odb}.sdc" PU_FINAL_SPEF="${top%.odb}.spef"
        export PU_STD_LIB=/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib
        openroad -no_init -threads "$2" -exit project/experiments/pu_leaf_base/audit_native.tcl \
            > "$PU_CANDIDATE/audit-native.log" 2>&1
        export PU_OVERLAY="$PU_CANDIDATE"
        gds="${top%.odb}.gds"
        upper=0
        klayout -b -r project/experiments/pu_leaf_base/overlay.py \
            > "$PU_CANDIDATE/audit-overlay.log" 2>&1 || upper=$?
        klayout -b -r /OpenROAD-flow-scripts/flow/platforms/nangate45/drc/FreePDK45.lydrc \
            -rd "in_gds=$gds" -rd "report_file=$PU_CANDIDATE/native-drc.lyrdb" \
            > "$PU_CANDIDATE/audit-drc.log" 2>&1
        python3 -B project/experiments/pu_leaf_base/check_native.py "$PU_CANDIDATE"
        exit "$upper"
        ' bash "$candidate" "$cpus"
