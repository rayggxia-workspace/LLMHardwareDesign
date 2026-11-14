#!/usr/bin/env bash
set -euo pipefail
cd "$1"
seal="$2"
sha256sum --check "$seal"
db=$(cut -d ' ' -f 3- "$seal")
python3 -B lane_manifest.py 3 client3.tsv
tool=/public/home/yuzelu/project-circuit/issue185-joint-packet-dma-bound-20261113-01/tool.sh
bash "$tool" env DMA_ODB="$db" DMA_MANIFEST="$PWD/client3.tsv" \
  DMA_AUDIT="$PWD/client3-$SLURM_JOB_ID.tsv" openroad -no_init -exit "$PWD/audit_lane.tcl"
awk -F '\t' 'NR>1 {n++; if ($6==0) { missing++; print $2 } if ($7!=1) shared++} END {print "pins="n,"no_internal_term="missing+0,"multi_boundary="shared+0; if(n!=684) exit 1}' "client3-$SLURM_JOB_ID.tsv"
sha256sum lane_manifest.py audit_lane.tcl "client3-$SLURM_JOB_ID.tsv" > "pin-audit-$SLURM_JOB_ID.sha256"
