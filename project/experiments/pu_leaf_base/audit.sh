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
        python3 -c "import sys,xml.etree.ElementTree as e; n=len(e.parse(sys.argv[1]).findall(\".//items/item\")); print(\"Native GDS DRC items:\",n); sys.exit(bool(n))" \
            "$PU_CANDIDATE/native-drc.lyrdb"
        python3 -c "import re,sys; s=open(sys.argv[1]).read(); slacks=re.findall(r"worst slack (?:max|min) (-?\d+\.\d+)",s); print("Setup/hold ns:",slacks); sys.exit(len(slacks)!=2 or any(float(x)<0 for x in slacks) or "(VIOLATED)" in s.split("=== ELECTRICAL VIOLATIONS ===")[1].split("=== CONSTRAINT AUDIT ===")[0])" \
            "$PU_CANDIDATE/audit-native.log"
        exit "$upper"
        ' bash "$candidate" "$cpus"
