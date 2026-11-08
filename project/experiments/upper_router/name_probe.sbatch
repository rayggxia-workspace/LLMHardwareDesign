#!/usr/bin/env bash
#SBATCH --job-name=yzl-name-probe
#SBATCH --partition=c64
#SBATCH --cpus-per-task=10
#SBATCH --time=0
set -euo pipefail
task=$1;prepared=$2
srun --exact --ntasks=1 --cpus-per-task=10 --cpu-bind=cores /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --pwd "$task/source" --env OMP_NUM_THREADS=10 /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash -c '
set -euo pipefail
source /OpenROAD-flow-scripts/env.sh
task=$1;prepared=$2
python3 - "$prepared/sta/sta.tcl" "$task/probe.tcl" <<"PY"
from pathlib import Path
import sys
raw=Path(sys.argv[1]).read_text().split("read_sdc",1)[0]
Path(sys.argv[2]).write_text(raw+"""
puts FIRST_PORT_NAMES
foreach p [lrange [get_ports *] 0 10] {puts [get_full_name $p]}
puts FIND_RAW
puts [get_ports {C0/clk_i}]
puts FIND_ESCAPED
puts [get_ports {C0\\/clk_i}]
puts FIRST_CELL_NAMES
foreach p [lrange [get_cells *] 0 5] {puts [get_full_name $p]}
""")
PY
openroad -no_init -threads 10 -exit "$task/probe.tcl" > "$task/probe.log" 2>&1
' bash "$task" "$prepared"
