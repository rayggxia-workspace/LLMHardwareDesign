"""Read sealed H1 artifacts; create all new outputs in issue-31 only."""
import hashlib
import json
from pathlib import Path
import subprocess
import shutil
import re

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
    if SPEC['mode']=='annotation':
        import sys
        sys.path.insert(0,str(ROOT/'runner/h1'))
        from annotation_audit import execute
        source=Path(SPEC['source'])
        previous=json.loads(sealed(source,'h1-qualification-input-sha256.json').read_text())
        manifest={n[2:]:h for h,n in (line.split(None,1) for line in (source/'output.sha256').read_text().splitlines())}
        def track(path):
            path=Path(path)
            expected=previous.get(str(path))
            if path.is_relative_to(source):expected=manifest.get(path.relative_to(source).as_posix())
            assert expected and digest(path)==expected,'Changed hierarchical annotation input '+str(path)
            INPUTS[str(path)]=expected
            return path
        def run_tcl(name,text):
            path=ROOT/(name+'.tcl');path.write_text(text)
            with (ROOT/(name+'.log')).open('w') as log:
                subprocess.run(['openroad','-threads',str(SPEC['cores']),'-exit',str(path)],stdout=log,stderr=subprocess.STDOUT,check=True)
        execute(ROOT,{'h2':source},run_tcl,track)
    if SPEC['mode']=='checks':
        source=Path(SPEC['source'])
        m=json.loads(sealed(source,'experiment.json').read_text())
        target=sealed(source,Path(m['result_relative'])/'6_final.odb')
        script='read_db {'+str(target)+'}\n'
        control=SPEC.get('short_control',False)
        if control:
            assert source==SOURCE and SPEC.get('box_dbu'), 'Only isolated H1 local calibration is supported'
            text=(ROOT/'physical.def').read_text()
            for name in ('a_addr[0]','a_addr[1]'):
                token='    - '+name+' '
                start=text.index(token,text.index('NETS 11954'))
                end=text.index(';',start)
                text=text[:end]+'\n + ROUTED metal8 ( 883640 2786000 ) ( 923640 * )\n'+text[end:]
            (ROOT/'deliberate-short.def').write_text(text)
            script+='odb::dbChip_destroy [[ord::get_db] getChip]\nread_def {'+str(ROOT/'deliberate-short.def')+'}\n'
        # DRC is geometric. Cached global-route guides are unnecessary and
        # can invoke expensive guide topology reconstruction on the H1 DB.
        script+='foreach n [[ord::get_db_block] getNets] {$n clearGuides}\nset_routing_layers -signal metal1-metal10 -clock metal1-metal10\n'
        box=SPEC.get('box_dbu')
        if box:
            assert len(box)==4 and all(type(v) is int for v in box)
            assert 0<=box[0]<box[2]<=3340000 and 0<=box[1]<box[3]<=3340000
        option=' -box {'+' '.join(map(str,box))+'}' if box else ''
        script+='write_def check-before.def\ndrt::check_drc -output_file integrated-drc.rpt'+option+'\nwrite_def check-after.def\nputs {NATIVE_READONLY_DRC_FINISHED}\n'
        path=ROOT/'readonly-drc.tcl';path.write_text(script)
        with (ROOT/'readonly-drc.log').open('w') as log:
            subprocess.run(['openroad','-threads',str(SPEC['cores']),'-exit',str(path)],stdout=log,stderr=subprocess.STDOUT,check=True)
        from freeze_audit import audit
        audit(ROOT/'check-before.def',ROOT/'check-after.def',11,ROOT/'readonly-drc-freeze-audit.json')
        report=(ROOT/'integrated-drc.rpt').read_text()
        passed=report.strip()==''
        detected=not passed and 'short' in report.lower() and all(n in report for n in ('a_addr[0]','a_addr[1]'))
        (ROOT/'readonly-drc-quality.json').write_text(json.dumps(dict(passed=passed,source=str(source),
            full_die=not bool(box),box_dbu=box,deliberate_short_control=control,expected_short_detected=detected if control else None,
            qualification_eligible=not control,
            scope=('Local diagnostic only; does not qualify full-parent DRC. ' if box else 'Standalone native full-parent geometric DRC. ')+
            ('Two intentionally overlapping M8 conductors in a separate copied DEF. ' if control else '')+
            'Cached guides removed only in memory; all manufacturing geometry unchanged before/after checker.'),indent=2)+'\n')
        assert detected if control else passed,'Native DRC short control not detected' if control else 'Integrated native DRC markers remain'
    if SPEC['mode']=='composite':
        source=Path(SPEC['source'])
        assert sealed(source,'exit-code.txt').read_text().strip()=='0'
        route=sealed(source,'route.log').read_text()
        assert re.findall(r'Number of violations = (\d+)',route)[-1]=='0'
        from integrate import integrate
        aliases=None
        if (source/'forest-plan.json').exists():
            plan=json.loads(sealed(source,'forest-plan.json').read_text())
            aliases={f['proxy']:f['original_net'] for f in plan['forests']}
            parts=json.loads(sealed(source,'partition.json').read_text())
            proxyodb=sealed(source,'restricted-final.odb')
            native='read_db {'+str(proxyodb)+'}\nset f [open routing-tech-shapes.tsv w]\nset tech [ord::get_db_tech]\nforeach l [$tech getLayers] {if {[$l getRoutingLevel]>0} {puts $f [list LAYER [$l getName] [$l getWidth]]}}\nforeach v [$tech getVias] {foreach box [$v getBoxes] {set l [$box getTechLayer];puts $f [list VIA [$v getName] [$l getName] [$box xMin] [$box yMin] [$box xMax] [$box yMax]]}}\nclose $f\n'
            (ROOT/'upper-tech.tcl').write_text(native)
            with (ROOT/'upper-tech.log').open('w') as log:
                subprocess.run(['openroad','-threads','1','-exit',str(ROOT/'upper-tech.tcl')],stdout=log,stderr=subprocess.STDOUT,check=True)
            from upper_connectivity import verify
            proof=verify(sealed(source,'restricted-final.def').read_text(),plan,parts['access_landings'],(ROOT/'routing-tech-shapes.tsv').read_text())
            (ROOT/'upper-connectivity.json').write_text(json.dumps(proof,indent=2)+'\n')
            assert proof['passed'],'Routed upper forest disconnected'
            boundary=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-31/boundary-01')
            pinrows=sealed(boundary,'signal-pin-layers.tsv').read_text().splitlines()
            assert pinrows and all(0<int(row.split()[-1])<8 for row in pinrows),'Actual signal terminal outside prepaid lower surface'
            (ROOT/'boundary-proof.json').write_text(json.dumps(dict(passed=True,signal_pin_shape_rows=len(pinrows),
                max_signal_pin_layer=max(int(row.split()[-1]) for row in pinrows),upper_forests=proof['forest_count'],
                original_logical_nets=len(plan['proofs']),all_access_graphs_connected=plan['passed']),indent=2)+'\n')
        integrate(sealed(source,'frozen-roundtrip.def'),sealed(source,'restricted-final.def'),ROOT/'composite.def',aliases)
        relative=Path(meta['result_relative']);dest=ROOT/relative;dest.mkdir(parents=True)
        shutil.copy2(sealed(SOURCE,'boundary.sdc'),ROOT/'boundary.sdc')
        for ext in ('v','sdc'):
            shutil.copy2(sealed(SOURCE,relative/('6_final.'+ext)),dest/('6_final.'+ext))
        (ROOT/'experiment.json').write_text(json.dumps(meta,indent=2)+'\n')
        previous=json.loads(sealed(SOURCE,'input-sha256.json').read_text())
        platform=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45')
        lefs=[platform/'lef/NangateOpenCellLibrary.tech.lef',platform/'lef/NangateOpenCellLibrary.macro.mod.lef']
        libs=[platform/'lib/NangateOpenCellLibrary_typical.lib']
        for kind in ('act','mxu'):
            view=meta['views'][kind]
            for ext,group in [('.lef',lefs),('.lib',libs)]:
                path=Path(view['view'])/(view['name']+ext)
                assert digest(path)==previous[str(path)],'Changed frozen macro view'
                group.append(path)
            child=Path(view['source'])
            childmeta=json.loads(sealed(child,'experiment.json').read_text())
            childrel=Path(childmeta['result_relative'])
            for ext in ('v','sdc','spef','odb'):sealed(child,childrel/('6_final.'+ext))
        for path in lefs+libs+[platform/'rcx_patterns.rules']:INPUTS[str(path)]=digest(path)
        script=''.join('read_lef {'+str(path)+'}\n' for path in lefs)
        script+=''.join('read_liberty {'+str(path)+'}\n' for path in libs)
        script+='read_def {'+str(ROOT/'composite.def')+'}\nread_sdc {'+str(dest/'6_final.sdc')+'}\n'
        script+='write_db {'+str(dest/'6_final.odb')+'}\nwrite_def composite-roundtrip.def\n'
        script+='define_process_corner -ext_model_index 0 X\nset_extraction_rules_file {'+str(platform/'rcx_patterns.rules')+'}\nextract_parasitics\n'
        script+='write_spef {'+str(dest/'6_final.spef')+'}\nread_spef {'+str(dest/'6_final.spef')+'}\nset_propagated_clock [all_clocks]\n'
        script+='report_worst_slack -max -digits 9\nreport_worst_slack -min -digits 9\nreport_tns -digits 9\n'
        script+='report_parasitic_annotation -report_unannotated > parent-annotation.rpt\n'
        script+='report_check_types -max_capacitance -max_slew -max_count 100000 -digits 9 -no_line_splits > parent-electrical.rpt\n'
        script+='report_check_types -violators -max_slew -max_capacitance -max_fanout -max_delay -min_delay -recovery -removal -min_period -digits 9 -no_line_splits\n'
        script+='set f [open rc-connectivity.tsv w]\nforeach n [[ord::get_db_block] getNets] {if {[$n getSigType] ni {POWER GROUND}} {puts $f "[$n getName]\\t[$n isRCDisconnected]"}}\nclose $f\n'
        script+='check_antennas -report_file composite-antenna.rpt\n'
        path=ROOT/'composite-extract.tcl';path.write_text(script)
        with (ROOT/'composite-extract.log').open('w') as log:
            subprocess.run(['openroad','-threads',str(SPEC['cores']),'-exit',str(path)],stdout=log,stderr=subprocess.STDOUT,check=True)
        from freeze_audit import audit
        audit(ROOT/'physical.def',ROOT/'composite-roundtrip.def',8,ROOT/'composite-native-freeze-audit.json',True)
        with (ROOT/'strict-qualification.log').open('w') as log:
            subprocess.run(['python3',str(ROOT/'runner/qualify.py')],stdout=log,stderr=subprocess.STDOUT,check=True)
        log=(ROOT/'composite-extract.log').read_text()
        electrical=(ROOT/'parent-electrical.rpt').read_text()
        checks=dict(parent_setup_nonnegative=float(re.search(r'worst slack max\s+([-+\d.eE]+)',log)[1])>=0,
            parent_hold_nonnegative=float(re.search(r'worst slack min\s+([-+\d.eE]+)',log)[1])>=0,
            parent_tns_zero=float(re.search(r'tns max\s+([-+\d.eE]+)',log)[1])==0,
            no_parent_electrical_violations='(VIOLATED)' not in electrical and '(VIOLATED)' not in log,
            antenna_zero='Found 0 net violations.' in log and 'Found 0 pin violations.' in log,
            rc_not_disconnected=all(row.split()[-1]=='0' for row in (ROOT/'rc-connectivity.tsv').read_text().splitlines()))
        (ROOT/'composite-quality.json').write_text(json.dumps(dict(passed=all(checks.values()),checks=checks,
            scope='Full resource/geometry freeze, actual RC extraction, parent and real hierarchical STA/PG. Integrated full-chip standalone DRC remains a separate check; upper native DRC and original frozen lower/block DRC are compositional evidence.'),indent=2)+'\n')
        assert all(checks.values()),'Composite physical/electrical constraints failed'
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
    if SPEC['mode']=='boundary':
        script='read_db {'+str(odb)+'}\nset b [ord::get_db_block]\n'
        script+='set f [open signal-pin-layers.tsv w]\nset seen {}\nforeach i [$b getInsts] {set m [$i getMaster];set name [$m getName];if {[dict exists $seen $name]} {continue};dict set seen $name 1;foreach t [$m getMTerms] {if {[$t getSigType] in {POWER GROUND}} {continue};foreach p [$t getMPins] {foreach box [$p getGeometry] {set l [$box getTechLayer];if {$l ne "NULL"} {puts $f [list $name [$t getName] [$l getName] [$l getRoutingLevel]]}}}}}\n'
        script+='foreach t [$b getBTerms] {if {[$t getSigType] in {POWER GROUND}} {continue};foreach p [$t getBPins] {foreach box [$p getBoxes] {set l [$box getTechLayer];puts $f [list TOP [$t getName] [$l getName] [$l getRoutingLevel]]}}}\nclose $f\n'
        script+='set f [open routing-tech-shapes.tsv w]\nset tech [ord::get_db_tech]\nforeach l [$tech getLayers] {if {[$l getRoutingLevel]>0} {puts $f [list LAYER [$l getName] [$l getWidth]]}}\nforeach v [$tech getVias] {foreach box [$v getBoxes] {set l [$box getTechLayer];puts $f [list VIA [$v getName] [$l getName] [$box xMin] [$box yMin] [$box xMax] [$box yMax]]}}\nclose $f\n'
        path=ROOT/'boundary.tcl';path.write_text(script)
        with (ROOT/'boundary.log').open('w') as log:
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
        selected=set(range(len(contract['access_landings'])))
        if SPEC.get('collapse_components'):
            from access_components import select_accesses
            plan=select_accesses(ROOT/'frozen-lower.def',contract['access_landings'])
            (ROOT/'access-plan.json').write_text(json.dumps(plan,indent=2)+'\n')
            selected=set(plan['selected'])
        active_names={p['net'] for i,p in enumerate(contract['access_landings']) if i in selected}
        routing_landings=contract['access_landings']
        if SPEC.get('forest'):
            from routing_forest import plan_forest
            forest=plan_forest(ROOT/'physical.def',ROOT/'frozen-lower.def',contract['access_landings'])
            (ROOT/'forest-plan.json').write_text(json.dumps(forest,indent=2)+'\n')
            byindex={i:tree['proxy'] for tree in forest['forests'] for i in tree['landings']}
            selected=set(byindex)
            active_names=set(byindex.values())
            routing_landings=[dict(p,net=byindex.get(i,p['net'])) for i,p in enumerate(contract['access_landings'])]
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
                if SPEC.get('forest'):
                    affected=active_names
                    for name in sorted(active_names):script+='odb::dbNet_create $b {'+name+'}\n'
                for serial,landing in enumerate(routing_landings):
                    if landing['net'] not in affected:continue
                    name=landing['net']
                    # Actual DB net names retain the native bus escaping.
                    script+='set n [$b findNet {'+name+'}]\nif {$n eq "NULL"} {error {Missing proxy source net}}\n'
                    if serial in selected:
                        script+='set p [odb::dbBTerm_create $n h2_landing_'+str(serial)+']\n$p setIoType INOUT\nset bp [odb::dbBPin_create $p]\n$bp setPlacementStatus FIRM\n'
                    script+='set v [[ord::get_db_tech] findVia {'+landing['via']+'}]\nif {$v eq "NULL"} {error {Missing native landing via}}\n'
                    action='odb::dbBox_create $bp' if serial in selected else 'odb::dbObstruction_create $b'
                    script+='foreach box [$v getBoxes] {set l [$box getTechLayer];if {[$l getName] eq "metal8"} {'+action+' $l [expr {'+str(landing['x'])+'+[$box xMin]}] [expr {'+str(landing['y'])+'+[$box yMin]}] [expr {'+str(landing['x'])+'+[$box xMax]}] [expr {'+str(landing['y'])+'+[$box yMax]}]}}\n'
                script+='set empty {}\nforeach n [$b getNets] {if {[$n getSigType] ni {POWER GROUND} && [llength [$n getBTerms]]==0} {lappend empty $n}}\nforeach n $empty {odb::dbNet_destroy $n}\n'
                # Upper routing has no active instances. Preserve actual
                # detailed-macro OBS as absolute physical obstacles; NG45
                # standard-cell geometry lies below the custom surface.
                script+='foreach name {u_act u_mxu} {set i [$b findInst $name];if {[$i getOrient] ne "R0"} {error {Unsupported macro transform}};lassign [$i getLocation] dx dy;foreach box [[$i getMaster] getObstructions] {set l [$box getTechLayer];if {[$l getName] in {metal8 metal9 metal10}} {odb::dbObstruction_create $b $l [expr {$dx+[$box xMin]}] [expr {$dy+[$box yMin]}] [expr {$dx+[$box xMax]}] [expr {$dy+[$box yMax]}]}}}\n'
                script+='set allinsts [$b getInsts]\nforeach i $allinsts {odb::dbInst_destroy $i}\n'
                script+='write_db proxy-initial.odb\nwrite_def proxy-initial.def\n'
                script+='# H2_PROXY_FRESH_PROCESS\n'
            guide=''
            guide_rows=contract['affected_nets']
            if SPEC.get('forest'):guide_rows=[dict(net=f['proxy'],box=f['guide_box']) for f in forest['forests']]
            for row in guide_rows:
                if row['net'] not in active_names:continue
                boxes=[row['box']+[layer] for layer in range(8,11)] if SPEC.get('forest') else contract['custom_guides'][row['net']]
                if SPEC.get('bbox_guides') and not SPEC.get('forest'):
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
