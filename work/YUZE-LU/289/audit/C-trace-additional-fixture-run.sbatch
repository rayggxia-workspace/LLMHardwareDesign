#!/bin/bash
#SBATCH --job-name=yzl-C-cellpreflight
#SBATCH --partition=debug
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --time=00:30:00
#SBATCH --output=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-trace-additional-fixture-%j.log
set -euo pipefail
out=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-trace-additional-fixture
/public/software/singularity-ce-4.3.4/bin/singularity exec --bind /public/home/yuzelu --pwd "$out" /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash -c 'set -euo pipefail; klayout -b -r export.py > export.log 2>&1; deck=/OpenROAD-flow-scripts/flow/platforms/nangate45/drc/FreePDK45.lydrc; echo "4e35cad6786f21c6e233fb606bea59bb44e1a12713008cf7367d65a1a3de2147  $deck" | sha256sum -c - > deck-identity.txt; sha256sum fixture.gds "$deck" export.py > inputs-before.sha256; klayout -b -r "$deck" -rd "in_gds=$PWD/fixture.gds" -rd "report_file=$PWD/full.lyrdb" > full.log 2>&1; sha256sum -c inputs-before.sha256 > inputs-after-check.txt; python3 receipt.py'
