"""Probe bounded same-net corner fills on a copy of a routed ODB."""
from collections import Counter
import json
from pathlib import Path
import re
import subprocess
import sys

repo, source, out = map(Path, sys.argv[1:4])
out.mkdir()
sys.path.insert(0, str(repo / 'project/experiments/block_v1'))
from revision300_v_corner_probe import def_content, violations

check = 'drt::check_drc_cmd {NAME-drc.rpt} 0 0 0 0 native_whole_drc\n'


def run(name, script):
    (out / f'{name}.tcl').write_text(script)
    with (out / f'{name}.log').open('w') as log:
        subprocess.run(['openroad', '-no_init', '-threads', '12', '-exit', f'{name}.tcl'],
                       cwd=out, stdout=log, stderr=subprocess.STDOUT, check=True)


run('before', f'read_db {{{source}}}\nwrite_def before.def\n' + check.replace('NAME', 'before'))
baseline = (out / 'before-drc.rpt').read_text()
pattern = re.compile(
    r'violation type: Metal Spacing\n\s*srcs: net:(\S+)\n'
    r'\s*bbox = \(([^,]+), ([^)]+)\) - \(([^,]+), ([^)]+)\) on Layer (metal[23])')
patches = set()
for name, x0, y0, x1, y1, layer in pattern.findall(baseline):
    x0, y0, x1, y1 = (round(float(coord) * 2000) for coord in (x0, y0, x1, y1))
    if 0 < x1 - x0 <= 200 and 0 < y1 - y0 <= 200:
        patches.add((name.replace(chr(92), ''), layer, x0, y0, x1, y1))
if not patches:
    (out / 'receipt.json').write_text(json.dumps(dict(patches=[], markers=sum(violations(baseline).values())), indent=2))
    sys.exit(0)
script = f'read_db {{{source}}}\n'
script += '''set block [ord::get_db_block]
if {[$block getDbUnitsPerMicron] != 2000} {error "Unexpected wire DBU"}
set tech [ord::get_db_tech]
set exact [dict create]
foreach net [$block getNets] {
    set name [string map [list [format %c 92] {}] [$net getName]]
    dict lappend exact $name $net
}
'''
for name, layer, x0, y0, x1, y1 in sorted(patches):
    token = name.encode().hex()
    script += f'set matches [dict get $exact [encoding convertfrom utf-8 [binary decode hex {{{token}}}]]]\n'
    script += '''if {[llength $matches] != 1} {error "Ambiguous target net"}
set net [lindex $matches 0]
if {[$net getSigType] in {POWER GROUND} || [$net getWire] eq "NULL"} {error "Expected routed signal"}
set enc [odb::new_dbWireEncoder]
odb::dbWireEncoder_append $enc [$net getWire]
'''
    script += f'odb::dbWireEncoder_newPath $enc [$tech findLayer {layer}] ROUTED\n'
    script += f'odb::dbWireEncoder_addPoint $enc {x0} {y0}\n'
    script += f'odb::dbWireEncoder_addRect $enc 0 0 {x1-x0} {y1-y0}\n'
    script += 'odb::dbWireEncoder_end $enc\nodb::delete_dbWireEncoder $enc\n'
script += 'write_db corner.odb\nwrite_def after.def\n' + check.replace('NAME', 'after')
run('after', script)
before_rect, before_route, before_n = def_content(out / 'before.def')
after_rect, after_route, after_n = def_content(out / 'after.def')
exact = after_rect == before_rect + Counter(patches) and before_route == after_route and before_n == after_n
old = violations(baseline)
new = violations((out / 'after-drc.rpt').read_text())
receipt = dict(patches=sorted(patches), original_markers=sum(old.values()),
               final_markers=sum(new.values()), added_markers=sum((new-old).values()),
               removed_markers=sum((old-new).values()), exact_diff=exact)
(out / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
assert exact and not (new - old) and sum(new.values()) < sum(old.values()), receipt
