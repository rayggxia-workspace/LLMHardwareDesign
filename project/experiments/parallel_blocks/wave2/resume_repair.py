"""Copy verified CTS inputs into a new attempt and reroute explicit drive upgrades."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

root = Path.cwd()
spec = json.loads(Path('task.json').read_text())
assert spec['kind'] == 'route-repair'
source = Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-7/parallel-blocks-wave2-06')/spec['source_task']
assert spec['source_task'] in ('act-cap10', 'merged-cap20')
assert not (root/'flow').exists()
nickname = 'parallel_'+spec['case'].replace('-', '_')
suffix = Path('flow/results/nangate45')/nickname/'base'
old_results = source/suffix
results = root/suffix
results.mkdir(parents=True)


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(8*1024*1024),b''):
            h.update(chunk)
    return h.hexdigest()


manifest = dict((line[66:], line[:64]) for line in (source/'output-files.sha256').read_text().splitlines())
inputs = []


def copy_verified(relative):
    old = source/relative
    expected = manifest[relative]
    actual = digest(old)
    assert actual == expected, relative
    destination = root/relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(str(old), str(destination))
    assert digest(destination) == expected, relative
    inputs.append(dict(source=str(old), destination=str(destination), sha256=expected))


for name in ('4_cts.odb', '4_cts.sdc'):
    copy_verified((suffix/name).as_posix())
for name in ('boundary.sdc', 'boundary.sv', 'elab.v', 'elab.json'):
    copy_verified(name)
for path in sorted((source/'memory-model').rglob('*')):
    if path.is_file():
        copy_verified(path.relative_to(source).as_posix())
copy_verified('config.mk')
copy_verified('experiment.json')

script = '''set llhd_block [ord::get_db_block]
set llhd_changes [open [file join $::env(WORK_HOME) .. applied-replacements.txt] w]
proc llhd_find_net {block name} {
  set net [$block findNet $name]
  if {$net ne "NULL"} {return $net}
  set matches {}
  foreach candidate [$block getNets] {
    set normalized [string map [list [format %c 92] {}] [$candidate getName]]
    if {$normalized eq $name} {lappend matches $candidate}
  }
  if {[llength $matches] != 1} {error "Output net has no unique escaped-name match: $name"}
  return [lindex $matches 0]
}
'''
for replacement in spec['replacements']:
    name, before, after = replacement[:3]
    assert all(not any(c in value for c in '{}\n\r') for value in (name,before,after))
    if len(replacement) == 4:
        net = replacement[3]
        assert not any(c in net for c in '{}\n\r')
        script += '''set llhd_net [llhd_find_net $llhd_block {%s}]
set llhd_drivers {}
foreach llhd_iterm [$llhd_net getITerms] {
  if {[$llhd_iterm getIoType] eq "OUTPUT"} {lappend llhd_drivers [$llhd_iterm getInst]}
}
if {[llength $llhd_drivers] != 1} {error {Repair net must have exactly one instance driver}}
set llhd_inst [lindex $llhd_drivers 0]
''' % net
    else:
        script += '''set llhd_inst [$llhd_block findInst {%s}]
if {$llhd_inst eq "NULL"} {error {Missing repair instance: %s}}
''' % (name,name)
    script += '''set llhd_name [$llhd_inst getName]
set llhd_sta_inst [sta::find_instance $llhd_name]
if {$llhd_sta_inst eq "NULL"} {
  set llhd_name [string map [list [format %c 92] {}] $llhd_name]
  set llhd_sta_inst [sta::find_instance $llhd_name]
}
if {$llhd_sta_inst eq "NULL"} {error "Resolved ODB driver has no STA instance: $llhd_name"}
set llhd_before [[$llhd_inst getMaster] getName]
if {$llhd_before ne {%s}} {error "Repair instance master mismatch: $llhd_before"}
if {![replace_cell $llhd_name {%s}]} {error {Equivalent port replacement rejected}}
set_dont_touch [list $llhd_sta_inst]
puts $llhd_changes "$llhd_name $llhd_before -> %s"
''' % (before,after,after)
script += '''close $llhd_changes
detailed_placement_helper
check_placement -verbose
'''
hook = root/'targeted-repair.tcl'
hook.write_text(script)
config = (root/'config.mk').read_text().replace(str(source), str(root))
config += 'export PRE_GLOBAL_ROUTE_TCL = '+str(hook)+'\n'
(root/'config.mk').write_text(config)
meta = json.loads((root/'experiment.json').read_text())
meta.update(repair=dict(source_attempt=str(source), checkpoint='4_cts.odb', replacements=spec['replacements'],
    placement_and_cts_reused=True, synthesis_repeated=False, changes='Equivalent port-list cell drive variants; no RTL, IO budget, register or cycle changes'),
    scope='Targeted CTS-checkpoint physical reroute; no full formal equivalence, hard macro qualification or signoff')
(root/'experiment.json').write_text(json.dumps(meta,indent=2)+'\n')
Path('checkpoint-inputs.json').write_text(json.dumps(inputs,indent=2)+'\n')
Path('checkpoint-inputs.sha256').write_text(''.join(i['sha256']+'  '+i['source']+'\n' for i in inputs))
Path('physical-temporary-policy.txt').write_text('Tool-default temporary directory; no long TMPDIR override\n')

command = ['make','-C','/OpenROAD-flow-scripts/flow','DESIGN_CONFIG='+str(root/'config.mk'),
    'WORK_HOME='+str(root/'flow'),'NUM_CORES='+os.environ['NUM_CORES']]
for target, logname in [('do-route','flow.log'),('do-finish','finish.log'),('do-generate_abstract','abstract.log')]:
    with Path(logname).open('w') as log:
        subprocess.run(command+[target],stdout=log,stderr=subprocess.STDOUT,check=True)
subprocess.run(['python3',str(Path(os.environ['LLHD_BATCH'])/'runner/wave2/export_detail.py')],check=True)
if not (results/'6_final.v').is_file():
    Path('export-netlist.tcl').write_text('read_db {'+str(results/'6_final.odb')+'}\nwrite_verilog {'+str(results/'6_final.v')+'}\n')
    with Path('export-netlist.log').open('w') as log:
        subprocess.run(['openroad','-exit','export-netlist.tcl'],stdout=log,stderr=subprocess.STDOUT,check=True)
