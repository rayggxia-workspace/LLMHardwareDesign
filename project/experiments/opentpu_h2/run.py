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
    if SPEC['mode']=='api':
        with (ROOT/'native-stack-symbols.txt').open('w') as log:
            subprocess.run(['addr2line','-f','-C','-e',shutil.which('openroad'),'0x5F46056','0x4100B48','0x3F60AB7','0x3F7C2FE','0x22AA150','0x22B271D'],stdout=log,stderr=subprocess.STDOUT,check=True)
        script='read_db {'+str(odb)+'}\n'
        script+='foreach cmd {drt::check_drc drt::step_dr} {puts "PROC $cmd ARGS [info args $cmd] BODY [info body $cmd]"}\n'
        script+='help extract_parasitics\nhelp check_antennas\nhelp write_verilog\n'
        script+='puts "CONNECTIVITY_API [info commands odb::*is*onnect*]"\ncatch {odb::orderWires} msg;puts "ORDERWIRES_USAGE $msg"\n'
        if SPEC.get('geometry_checks',True):
            script+='drt::check_drc -output_file baseline-drc.rpt\ncheck_antennas -report_file baseline-antenna.rpt\n'
        path=ROOT/'native-api.tcl';path.write_text(script)
        with (ROOT/'native-api.log').open('w') as log:
            subprocess.run(['openroad','-threads','1','-exit',str(path)],stdout=log,stderr=subprocess.STDOUT,check=True)
        snippets={}
        for name in ['scripts/final_report.tcl','scripts/final_connect.tcl','scripts/final_outputs.tcl','scripts/extract_parasitics.tcl','scripts/extract.tcl','scripts/rcx.tcl','scripts/rcx_helpers.tcl','scripts/fillcell.tcl','scripts/final.tcl','platforms/nangate45/config.mk']:
            p=Path('/OpenROAD-flow-scripts/flow')/name
            if p.exists():snippets[name]=p.read_text()
        (ROOT/'native-flow-snippets.json').write_text(json.dumps(snippets,indent=2)+'\n')
    if SPEC['mode']=='connectivity':
        script='read_db {'+str(odb)+'}\nputs "LOGGER_API [info commands utl::*ogger*] [info commands ord::*ogger*]"\n'
        script+='puts "NET_API [info commands odb::*Net*onnect*]"\n'
        path=ROOT/'connectivity-api.tcl';path.write_text(script)
        with (ROOT/'connectivity-api.log').open('w') as log:
            subprocess.run(['openroad','-threads','1','-exit',str(path)],stdout=log,stderr=subprocess.STDOUT,check=True)
    if SPEC['mode']=='debug':
        source=Path(SPEC['source'])
        proxy=sealed(source,'proxy-initial.odb')
        guide=sealed(source,'restricted.guide')
        path=ROOT/'debug-route.tcl'
        path.write_text('read_db {'+str(proxy)+'}\nset_routing_layers -signal metal8-metal10\nread_guides {'+str(guide)+'}\ndetailed_route -output_drc debug-drc.rpt\n')
        observations={}
        exe=shutil.which('openroad')
        for tool,args in [('readelf',['-h','-l',exe]),('addr2line',['-f','-C','-e',exe,'0x6147056','0x4301B48','0x4161AB7','0x417D2FE','0x24AB150','0x24B371D','0x227F22A']),('gdb',['-batch','-ex','run','-ex','bt','--args',exe,'-threads',str(SPEC['cores']),'-exit',str(path)])]:
            executable=shutil.which(tool)
            if executable:
                with (ROOT/('debug-'+tool+'.log')).open('w') as log:
                    outcome=subprocess.run([executable]+args,stdout=log,stderr=subprocess.STDOUT)
                observations[tool]=dict(executable=executable,exit_code=outcome.returncode)
            else:observations[tool]=dict(available=False)
        for candidate in ['/OpenROAD-flow-scripts/tools/OpenROAD/src/drt/src/io/io.cpp','/OpenROAD-flow-scripts/tools/OpenROAD/src/odb/src/db/dbNet.cpp']:
            path=Path(candidate)
            if path.is_file():
                (ROOT/('source-'+path.name)).write_text(path.read_text())
        (ROOT/'debug-tools.json').write_text(json.dumps(observations,indent=2)+'\n')
    if SPEC['mode'] in ('partition','route'):
        from def_routes import partition
        contract=partition(ROOT/'physical.def',ROOT/'frozen-lower.def',SPEC['bottom'])
        (ROOT/'partition.json').write_text(json.dumps(contract,indent=2)+'\n')
        script='read_db {'+str(odb)+'}\nhelp read_def\nhelp detailed_route\nhelp global_route\n'
        script+='odb::dbChip_destroy [[ord::get_db] getChip]\n'
        script+='read_def {'+str(ROOT/'frozen-lower.def')+'}\n'
        script+='write_def {'+str(ROOT/'frozen-roundtrip.def')+'}\nwrite_db {'+str(ROOT/'frozen.odb')+'}\n'
        path=ROOT/'partition.tcl';path.write_text(script)
        with (ROOT/'partition.log').open('w') as log:
            subprocess.run(['openroad','-threads',str(SPEC['cores']),'-exit',str(path)],stdout=log,stderr=subprocess.STDOUT,check=True)
        from freeze_audit import audit
        audit(ROOT/'physical.def',ROOT/'frozen-roundtrip.def',SPEC['bottom'],ROOT/'freeze-audit.json')
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
        if not SPEC.get('proxy'):
            script+='read_sdc {'+str(sealed(SOURCE,Path(meta['result_relative'])/'6_final.sdc'))+'}\n'
        if SPEC['mode']=='budget':
            script+='read_spef {'+str(sealed(SOURCE,Path(meta['result_relative'])/'6_final.spef'))+'}\nset_propagated_clock [all_clocks]\n'
            script+='report_worst_slack -max -digits 9\nreport_worst_slack -min -digits 9\n'
            script+='help report_net\nhelp report_clock_skew\nreport_clock_properties\nreport_clock_skew -digits 9 -include_internal_latency\n'
            script+='report_check_types -max_capacitance -max_slew -max_count 100000 -digits 9 -no_line_splits > electrical-budget.rpt\n'
            script+='set f [open macro-nets.txt w]\nset nets {}\nforeach i {u_act u_mxu} {foreach p [[[ord::get_db_block] findInst $i] getITerms] {set n [$p getNet];if {$n ne "NULL" && [$n getSigType] ni {POWER GROUND}} {lappend nets [$n getName]}}}\n'
            script+='foreach n [[ord::get_db_block] getNets] {if {[$n getSigType] eq "CLOCK"} {lappend nets [$n getName]}}\n'
            script+='foreach n [lsort -unique $nets] {puts $f $n;report_net -digits 9 $n >> interface-nets.rpt}\nclose $f\n'
        else:
            script+='puts "DRT_API [info commands drt::*]"\n'
            if SPEC.get('proxy'):
                # The router needs terminals at prepaid access landings, not
                # original M1/M3/M5 pins behind frozen lower conductors. This
                # is an isolated routing proxy; original pin connections are
                # restored by construction when upper wires are integrated.
                script+='set b [ord::get_db_block]\nforeach n [$b getNets] {if {[$n getSigType] ni {POWER GROUND}} {foreach p [$n getITerms] {$p disconnect};foreach p [$n getBTerms] {odb::dbBTerm_destroy $p}}}\n'
                script+='foreach n [$b getNets] {if {[$n getSigType] ni {POWER GROUND}} {set w [$n getWire];if {$w ne "NULL"} {odb::dbWire_destroy $w}}}\n'
                affected={row['net'] for row in contract['affected_nets']}
                for serial,landing in enumerate(contract['access_landings']):
                    if landing['net'] not in affected:continue
                    name=landing['net']
                    # Actual DB net names retain the native bus escaping.
                    script+='set n [$b findNet {'+name+'}]\nif {$n eq "NULL"} {error {Missing proxy source net}}\n'
                    script+='set p [odb::dbBTerm_create $n h2_landing_'+str(serial)+']\n$p setIoType INOUT\nset bp [odb::dbBPin_create $p]\n$bp setPlacementStatus FIRM\n'
                    script+='set v [[ord::get_db_tech] findVia {'+landing['via']+'}]\nif {$v eq "NULL"} {error {Missing native landing via}}\n'
                    script+='foreach box [$v getBoxes] {set l [$box getTechLayer];if {[$l getName] eq "metal8"} {odb::dbBox_create $bp $l [expr {'+str(landing['x'])+'+[$box xMin]}] [expr {'+str(landing['y'])+'+[$box yMin]}] [expr {'+str(landing['x'])+'+[$box xMax]}] [expr {'+str(landing['y'])+'+[$box yMax]}]}}\n'
                script+='set empty {}\nforeach n [$b getNets] {if {[$n getSigType] ni {POWER GROUND} && [llength [$n getBTerms]]==0} {lappend empty $n}}\nforeach n $empty {odb::dbNet_destroy $n}\n'
                # Upper routing has no active instances. Preserve actual
                # detailed-macro OBS as absolute physical obstacles; NG45
                # standard-cell geometry lies below the custom surface.
                script+='foreach name {u_act u_mxu} {set i [$b findInst $name];if {[$i getOrient] ne "R0"} {error {Unsupported macro transform}};lassign [$i getLocation] dx dy;foreach box [[$i getMaster] getObstructions] {set l [$box getTechLayer];if {[$l getName] in {metal8 metal9 metal10}} {odb::dbObstruction_create $b $l [expr {$dx+[$box xMin]}] [expr {$dy+[$box yMin]}] [expr {$dx+[$box xMax]}] [expr {$dy+[$box yMax]}]}}}\n'
                script+='set allinsts [$b getInsts]\nforeach i $allinsts {odb::dbInst_destroy $i}\n'
                script+='write_db proxy-initial.odb\nwrite_def proxy-initial.def\n'
                script+='# H2_PROXY_FRESH_PROCESS\n'
            guide=''
            for row in contract['affected_nets']:
                boxes=contract['custom_guides'][row['net']]
                if SPEC.get('bbox_guides'):
                    boxes=[[min(b[0] for b in boxes),min(b[1] for b in boxes),
                        max(b[2] for b in boxes),max(b[3] for b in boxes),layer] for layer in range(8,11)]
                guide+=row['net']+'\n(\n'+''.join(' '.join(map(str,box[:4]))+' metal'+str(box[4])+'\n' for box in boxes)+')\n'
            (ROOT/'restricted.guide').write_text(guide)
            script+='puts "GUIDE_API [info commands odb::*Guide*]"\n'
            script+='foreach n [[ord::get_db_block] getNets] {foreach g [$n getGuides] {odb::dbGuide_destroy $g}}\n'
            script+='set_routing_layers -signal metal8-metal10 -clock metal4-metal10\n'
            script+='read_guides {'+str(ROOT/'restricted.guide')+'}\n'
            script+='detailed_route -output_drc restricted-drc.rpt -output_maze restricted-maze.log\n'
            script+='write_def restricted-final.def\nwrite_db restricted-final.odb\n'
        path=ROOT/(SPEC['mode']+'.tcl');path.write_text(script)
        if SPEC.get('proxy'):
            build,route=script.split('# H2_PROXY_FRESH_PROCESS\n')
            buildpath=ROOT/'proxy-build.tcl';buildpath.write_text(build)
            with (ROOT/'proxy-build.log').open('w') as log:
                subprocess.run(['openroad','-threads',str(SPEC['cores']),'-exit',str(buildpath)],stdout=log,stderr=subprocess.STDOUT,check=True)
            tech=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lef/NangateOpenCellLibrary.tech.lef')
            INPUTS[str(tech)]=digest(tech)
            path.write_text('read_lef {'+str(tech)+'}\nread_def {'+str(ROOT/'proxy-initial.def')+'}\n'+route)
        with (ROOT/(SPEC['mode']+'.log')).open('w') as log:
            subprocess.run(['openroad','-threads',str(SPEC['cores']),'-exit',str(path)],stdout=log,stderr=subprocess.STDOUT,check=True)
finally:
    (ROOT/'input-sha256.json').write_text(json.dumps(INPUTS,indent=2)+'\n')
