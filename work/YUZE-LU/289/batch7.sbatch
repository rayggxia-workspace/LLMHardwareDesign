#!/bin/bash
#SBATCH --job-name=yzl-i289-x8
#SBATCH --partition=c96,c64
#SBATCH --nodes=1
#SBATCH --exclusive
#SBATCH --ntasks=6
#SBATCH --cpus-per-task=8
#SBATCH --time=12:00:00
#SBATCH --output=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/batch7-%j.log
set -euo pipefail
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117
python3 -c 'import pathlib; m=dict(line.split(":",1) for line in pathlib.Path("/proc/meminfo").read_text().splitlines()); a=int(m["MemAvailable"].split()[0]); print("MemAvailable_kB",a); assert a>=96*1024*1024, "Insufficient available memory for eight candidates"'
exec python3 "$root/dispatch.py" "$root/batch7.json" --slots 6 --cpus 8
