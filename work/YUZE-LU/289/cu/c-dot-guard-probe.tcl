read_db /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/runs/C-v20-native-clock4/global-candidate.odb
source /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/geometry.tcl
geometry_snapshot /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/dot-guard-before.tsv
source /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/c-dot-actual-cut-guard-v1.tcl
source /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/c-dot-actual-cut-guard-v1.tcl
geometry_snapshot /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/dot-guard-after.tsv
exec cmp /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/dot-guard-before.tsv /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/dot-guard-after.tsv
puts DOT_GUARD_IDEMPOTENT_GEOMETRY_PASS