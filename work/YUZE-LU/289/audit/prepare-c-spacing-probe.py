from pathlib import Path
import json,hashlib
r=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117');p=r/'audit/C-upper-spacing-guard-v4';v=json.loads((p/'receipt.json').read_text());assert v['rectangles']>0
(p/'binding.tcl').write_text('set kg_expected_count '+str(v['rectangles'])+'\nset kg_hashes {'+' '.join(n+' '+hashlib.sha256((p/n).read_bytes()).hexdigest() for n in ['master-geometry.tsv','keepout.tsv'])+'}\n')
(p/'probe.tcl').write_text('''read_db /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/runs/C-v20-native-clock4/flow/results/nangate45/c-overlay-current/base/6_final.odb
source /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-final-v1/geometry-all.tcl
set before [geometry_snapshot before-geometry.tsv]
write_verilog before.v
source hook.tcl
if {$kg_added!=$kg_expected_count} {error "Unexpected first append count"}
source hook.tcl
if {$kg_added!=0} {error "Not idempotent"}
if {[geometry_snapshot after-geometry.tsv] ne $before} {error "Interface geometry changed"}
write_verilog after.v
exec cmp before.v after.v
puts C_SPACING_KEEPOUT_GEOMETRY_LOGIC_IDEMPOTENCE_PASS
''')
s=(p/'run.sbatch').read_text().replace('openroad -no_init -exit export.tcl > export.log 2>&1; klayout -b -r derive.py > derive.log 2>&1','openroad -no_init -exit probe.tcl > probe.log 2>&1');(p/'probe.sbatch').write_text(s)
print(v['rectangles'],v['stats'])
