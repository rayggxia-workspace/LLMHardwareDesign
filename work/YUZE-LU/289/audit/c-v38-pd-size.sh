set -euo pipefail
source /OpenROAD-flow-scripts/env.sh
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117
out=$root/audit/C-v38-pd-size-v1
mkdir "$out";cd "$out"
run=$root/cu/runs/C-v38-close-y640-h50
src=$run/flow/results/nangate45/c-overlay-current/base
echo "8e64222ad9eeab2266455e4f8a3023ca0eb622f5028e37a48efab8e0db2a66a7  $src/6_final.odb" | sha256sum -c -
cp "$src/6_final.odb" input.odb
cp "$root/audit/c-v38-pd-size.tcl" greedy.tcl
cp "$root/audit/c-v38-pd-models.py" models.py
cp "$root/audit/c-v38-pd-verify.py" verify.py
cp "$root/audit/c-liberty-truth.py" truth.py
cp "$run/diagnose-fresh-v1/pd94.rpt" source-pd94.rpt
export CU_LIBS=$(sed -n 's/^export ADDITIONAL_LIBS = //p' "$run/config.mk" | tail -1)
sha256sum "$src/6_final.odb" "$src/6_final.sdc" "$src/6_final.spef" "$run/config.mk" "$root/cu/geometry.tcl" "$root/cu/c-freeze-outputs-v1.tcl" $CU_LIBS > inputs-before.sha256
python3 models.py
python3 - <<'PY'
from pathlib import Path
import re
text=Path('source-pd94.rpt').read_text();rows=[]
for line in text.splitlines():
 m=re.search(r'([-+\d.]+)\s+([-+\d.]+)\s+[v^]\s+(\S+)/\S+\s+\((\w+)\)',line)
 if m and not m[4].startswith(('DFF','SDFF')):rows.append((float(m[1]),m[3]))
names=[]
for delay,n in sorted(rows,reverse=True):
 if n not in names:names.append(n)
Path('priority.tcl').write_text('set priority [list '+' '.join('{'+n+'}' for n in names)+']\n')
PY
openroad -no_init -exit greedy.tcl > openroad.log 2>&1
sha256sum -c inputs-before.sha256 > inputs-unchanged.log
python3 verify.py
