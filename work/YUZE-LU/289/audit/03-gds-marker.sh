#!/bin/bash
set -euo pipefail
/public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif klayout -b -r /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/f_marker_gds.py
