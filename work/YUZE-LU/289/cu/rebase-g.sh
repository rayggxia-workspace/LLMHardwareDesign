#!/bin/bash
# Container + compute node only; called before first routing step.
set -euo pipefail
run=$1
export CU_REBASE_SOURCE=$2
export CU_REBASE_TARGET=$3
export CU_REBASE_DIR=$run/rebase-g
mkdir -p "$CU_REBASE_DIR"
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu
newg=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/gs/candidate-G-hold03-v3
export NEW_G_LIB=$newg/qualification-v2/block_v2_g.lib
export NEW_G_LEF=$newg/abstract-detailed/block_v2_g.lef
export NEW_G_GDS=$newg/flow/results/nangate45/bv1_block_v2_g/base/6_final.gds
for file in "$NEW_G_LIB" "$NEW_G_LEF" "$NEW_G_GDS"; do test -s "$file"; done
python3 - "$run/config.mk" <<'PY'
from pathlib import Path
import sys,os
p=Path(sys.argv[1]);s=p.read_text();lines=[];seen=set()
for line in s.splitlines():
 if line.startswith('export ADDITIONAL_'):
  words=line.split()
  for i,w in enumerate(words):
   if w.endswith('/block_v2_g.lef'):words[i]=os.environ['NEW_G_LEF'];seen.add('lef')
   elif w.endswith('/block_v2_g.lib'):words[i]=os.environ['NEW_G_LIB'];seen.add('lib')
   elif '/release/g/' in w and w.endswith('/6_final.gds'):words[i]=os.environ['NEW_G_GDS'];seen.add('gds')
  line=' '.join(words)
 lines.append(line)
assert seen=={'lef','lib','gds'},seen
p.write_text('\n'.join(lines)+'\n')
PY
export CU_REBASE_LEFS=$(sed -n 's/^export ADDITIONAL_LEFS = //p' "$run/config.mk" | tail -1)
sha256sum "$CU_REBASE_SOURCE" "$NEW_G_LIB" "$NEW_G_LEF" "$NEW_G_GDS" > "$CU_REBASE_DIR/source-sha256.txt"
openroad -no_init -exit "$root/export-rebase.tcl" > "$CU_REBASE_DIR/export.log" 2>&1
openroad -no_init -exit "$root/import-rebase.tcl" > "$CU_REBASE_DIR/import.log" 2>&1
sha256sum "$CU_REBASE_TARGET" > "$CU_REBASE_DIR/rebuilt-sha256.txt"
