"""Read sealed H1 artifacts; create all new outputs in issue-31 only."""
import hashlib
import json
from pathlib import Path
import subprocess
import shutil

ROOT = Path.cwd()
SPEC = json.loads((ROOT/'spec.json').read_text())
SOURCE = Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-15/top-split-reuse-20-01')
INPUTS = {}
def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(8*1024*1024),b''):
            h.update(chunk)
    return h.hexdigest()
def sealed(source,relative):
    manifest = {n[2:]:h for h,n in (line.split(None,1) for line in (source/'output.sha256').read_text().splitlines())}
    path = source/relative
    assert digest(path) == manifest[str(relative)], 'Changed sealed input '+str(path)
    INPUTS[str(path)] = digest(path)
    INPUTS[str(source/'output.sha256')] = digest(source/'output.sha256')
    return path
try:
    meta = json.loads(sealed(SOURCE,'experiment.json').read_text())
    odb = sealed(SOURCE,Path(meta['result_relative'])/'6_final.odb')
    args = dict(source=str(SOURCE),odb=str(odb),meta=meta)
    (ROOT/'inputs.json').write_text(json.dumps(args,indent=2)+'\n')
    script = 'read_db {'+str(odb)+'}\n'
    script += 'set b [ord::get_db_block]\nset f [open active-inventory.tsv w]\n'
    script += 'foreach i [$b getInsts] {puts $f "[$i getName]\\t[[$i getMaster] getName]\\t[$i getLocation]\\t[$i getOrient]\\t[$i getPlacementStatus]"}\nclose $f\n'
    script += 'set f [open connectivity.tsv w]\nforeach n [$b getNets] {foreach p [$n getITerms] {puts $f "[$n getName]\\t[$n getSigType]\\t[[$p getInst] getName]\\t[[$p getMTerm] getName]"}}\nclose $f\n'
    script += 'puts "WIRE_APIS [info commands odb::*Wire*]"\n'
    script += 'write_def physical.def\n'
    (ROOT/'physical.tcl').write_text(script)
    with (ROOT/'physical-inventory.log').open('w') as log:
        subprocess.run(['openroad','-threads',str(SPEC['cores']),'-exit',str(ROOT/'physical.tcl')],stdout=log,stderr=subprocess.STDOUT,check=True)
    if SPEC['mode'] in ('partition','route'):
        from def_routes import partition
        contract=partition(ROOT/'physical.def',ROOT/'frozen-lower.def',SPEC['bottom'])
        (ROOT/'partition.json').write_text(json.dumps(contract,indent=2)+'\n')
        script='read_db {'+str(odb)+'}\nhelp read_def\nhelp detailed_route\nhelp global_route\n'
        script+='foreach n [[ord::get_db_block] getNets] {if {[$n getSigType] ni {POWER GROUND}} {set w [$n getWire];if {$w ne "NULL"} {odb::dbWire_destroy $w}}}\n'
        script+='read_def -incremental {'+str(ROOT/'frozen-lower.def')+'}\n'
        script+='write_def {'+str(ROOT/'frozen-roundtrip.def')+'}\nwrite_db {'+str(ROOT/'frozen.odb')+'}\n'
        path=ROOT/'partition.tcl';path.write_text(script)
        with (ROOT/'partition.log').open('w') as log:
            subprocess.run(['openroad','-threads',str(SPEC['cores']),'-exit',str(path)],stdout=log,stderr=subprocess.STDOUT,check=True)
    if SPEC['mode'] in ('budget','route'):
        libs=[Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib')]
        previous=json.loads(sealed(SOURCE,'input-sha256.json').read_text())
        for kind in ('act','mxu'):
            view=meta['views'][kind]
            lib=Path(view['view'])/(view['name']+'.lib')
            assert digest(lib)==previous[str(lib)]
            INPUTS[str(lib)]=digest(lib)
            libs.append(lib)
        script=''.join('read_liberty {'+str(lib)+'}\n' for lib in libs)
        for lib in libs: INPUTS[str(lib)]=digest(lib)
        script+='read_db {'+str(odb if SPEC['mode']=='budget' else ROOT/'frozen.odb')+'}\n'
        script+='read_sdc {'+str(sealed(SOURCE,Path(meta['result_relative'])/'6_final.sdc'))+'}\n'
        if SPEC['mode']=='budget':
            script+='read_spef {'+str(sealed(SOURCE,Path(meta['result_relative'])/'6_final.spef'))+'}\nset_propagated_clock [all_clocks]\n'
            script+='report_worst_slack -max -digits 9\nreport_worst_slack -min -digits 9\n'
            script+='help report_net\nhelp report_clock_skew\nreport_clock_properties\nreport_clock_skew\n'
            script+='report_check_types -max_capacitance -max_slew -max_count 100000 -digits 9 -no_line_splits > electrical-budget.rpt\n'
            script+='set f [open macro-nets.txt w]\nset nets {}\nforeach i {u_act u_mxu} {foreach p [[[ord::get_db_block] findInst $i] getITerms] {set n [$p getNet];if {$n ne "NULL" && [$n getSigType] ni {POWER GROUND}} {lappend nets [$n getName]}}}\n'
            script+='foreach n [lsort -unique $nets] {puts $f $n;report_net -connections -verbose $n >> interface-nets.rpt}\nclose $f\n'
        else:
            script+='set_routing_layers -signal metal8-metal10 -clock metal4-metal10\n'
            script+='detailed_route -bottom_routing_layer metal8 -top_routing_layer metal10 -output_drc restricted-drc.rpt -output_maze restricted-maze.log\n'
            script+='write_def restricted-final.def\nwrite_db restricted-final.odb\n'
        path=ROOT/(SPEC['mode']+'.tcl');path.write_text(script)
        with (ROOT/(SPEC['mode']+'.log')).open('w') as log:
            subprocess.run(['openroad','-threads',str(SPEC['cores']),'-exit',str(path)],stdout=log,stderr=subprocess.STDOUT,check=True)
finally:
    (ROOT/'input-sha256.json').write_text(json.dumps(INPUTS,indent=2)+'\n')
