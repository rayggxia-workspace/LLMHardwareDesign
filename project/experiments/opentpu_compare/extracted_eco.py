"""Recover a sealed, actually routed parent using its extracted violations.

GRT checks remain recorded estimates; this branch deliberately obtains new
detailed-route/extracted evidence even when an estimate is pessimistic. Every
final physical, electrical, timing, PG and full-hierarchy gate remains required.
"""
import json
from pathlib import Path
import re
import shutil
import subprocess
from run import ROOT, track, digest


def execute(spec):
    from implementation import make_stages, qualify_parent_final, validate_parent_pins
    source=Path(spec['extracted_eco_source'])
    assert (source/'exit-code.txt').is_file(), 'Only recover sealed terminal attempts'
    manifest={name[2:]:h for h,name in (line.split(None,1) for line in (source/'output.sha256').read_text().splitlines())}

    def sealed(relative):
        path=source/relative
        assert digest(path)==manifest[str(relative)], 'Changed sealed source '+str(relative)
        track(path)
        return path

    meta=json.loads(sealed('experiment.json').read_text());relative=Path(meta['result_relative'])
    for name in ['strict-pg.json','final-pg/strict-pg.json','pin-placement-quality.json']:
        assert json.loads(sealed(name).read_text())['passed'], 'Invalid source geometry/PG'
    before=json.loads(sealed('input-sha256.json').read_text())
    for view in meta['views'].values():
        for ext in ['.lib','.lef']:
            path=Path(view['view'])/(view['name']+ext)
            assert digest(path)==before[str(path)], 'Changed immutable macro view'
            track(path)
    for name in ['config.mk','top.v','boundary.sdc','external-pin-contract.json','resource-qualification.json',
                 'strict-pg.json','stage-pins.tsv','pin-placement-quality.json','placement.tcl','pdn.tcl','post-pdn.tcl','fixed-pins.tcl']:
        path=sealed(name);destination=ROOT/name
        shutil.copy2(path,destination)
        if destination.suffix=='.tcl':destination.write_text(destination.read_text().replace(str(source),str(ROOT)))
    config=(ROOT/'config.mk').read_text().replace(str(source),str(ROOT))
    config='\n'.join(line for line in config.splitlines() if 'POST_GLOBAL_ROUTE_TCL' not in line)+'\n'
    (ROOT/'config.mk').write_text(config)
    results=ROOT/relative;results.mkdir(parents=True)
    for ext in ['odb','sdc','spef']:
        shutil.copy2(sealed(relative/('6_final.'+ext)),results/('eco-initial.'+ext))
    meta['extracted_eco']=dict(source=str(source),source_exit_code=(source/'exit-code.txt').read_text().strip(),
        approach='Actual extracted violation repair, then complete new signal routing/extraction; unchanged final gates; GRT estimates recorded as diagnostics')
    (ROOT/'experiment.json').write_text(json.dumps(meta,indent=2)+'\n')
    validate_parent_pins(results/'eco-initial.odb')
    command=['make','-C','/OpenROAD-flow-scripts/flow','DESIGN_CONFIG='+str(ROOT/'config.mk'),
             'WORK_HOME='+str(ROOT/'flow'),'NUM_CORES='+str(spec['cores'])]

    def run(name,body):
        script='source $::env(SCRIPTS_DIR)/load.tcl\nload_design eco-initial.odb eco-initial.sdc\n'
        script+='read_spef {'+str(results/'eco-initial.spef')+'}\nset_propagated_clock [all_clocks]\n'+body
        path=ROOT/(name+'.tcl');path.write_text(script)
        with (ROOT/(name+'.log')).open('w') as f:
            subprocess.run(command+['RUN_SCRIPT='+str(path),'RUN_LOG_NAME_STEM='+name,'run'],stdout=f,stderr=subprocess.STDOUT,check=True)

    report=ROOT/'extracted-before.rpt'
    setup_report=ROOT/'extracted-setup-before.rpt'
    run('extracted-inspect','report_worst_slack -max -digits 9 > {'+str(report)+'}\n'
        'report_worst_slack -min -digits 9 >> {'+str(report)+'}\n'
        'report_check_types -max_capacitance -max_slew -max_count 1000 -digits 9 -no_line_splits >> {'+str(report)+'}\n'
        'report_checks -path_delay min -group_path_count 100 -endpoint_path_count 1 -digits 9 -format full_clock_expanded >> {'+str(report)+'}\n'
        'report_checks -path_delay max -group_path_count 100 -endpoint_path_count 1 -digits 9 -format full_clock_expanded -fields {slew cap input_pin net fanout} > {'+str(setup_report)+'}\n')
    metrics=json.loads(sealed(Path(str(relative).replace('/results/','/logs/'))/'6_report.json').read_text())
    observed=[float(re.search(r'worst slack '+delay+r'\s+([-+0-9.eE]+)',report.read_text())[1]) for delay in ['max','min']]
    expected=[metrics['finish__timing__'+kind+'__ws'] for kind in ['setup','hold']]
    reproduced=all(abs(a-b)<1e-6 for a,b in zip(observed,expected))
    (ROOT/'extracted-source-validation.json').write_text(json.dumps(dict(passed=reproduced,
        observed_macro_wns_ns=observed,expected_macro_wns_ns=expected,tolerance_ns=1e-6),indent=2)+'\n')
    assert reproduced, 'Reloaded extracted RC does not reproduce source timing'
    if spec.get('extracted_size_probes'):
        # Compare real cell models on the sealed source's existing RC only.
        # Each probe reloads the same ODB/SPEF in a fresh process. These are
        # sizing estimates, never legalized/routed/qualified physical results.
        probes=spec['extracted_size_probes']
        assert isinstance(probes,list) and 0<len(probes)<=8
        for index,changes in enumerate(probes):
            assert changes and len(changes)<=8
            body=''
            for name,before,after in changes:
                assert re.fullmatch(r'[A-Za-z0-9_]+',name)
                assert re.fullmatch(r'(?:CLKBUF|BUF)_X[0-9]+',before)
                assert re.fullmatch(r'BUF_X(?:1|2|4|8|16|32)',after)
                body+='set inst [[ord::get_db_block] findInst {'+name+'}]\n'
                body+='if {$inst eq "NULL" || [[$inst getMaster] getName] ne {'+before+'}} {error {Sizing probe source master differs}}\n'
                body+='if {![replace_cell {'+name+'} {'+after+'}]} {error {Sizing probe replacement failed}}\n'
            output=ROOT/('sizing-probe-'+str(index)+'.rpt')
            body+='report_worst_slack -max -digits 9 > {'+str(output)+'}\n'
            body+='report_worst_slack -min -digits 9 >> {'+str(output)+'}\n'
            body+='report_checks -path_delay min -group_path_count 1 -digits 9 >> {'+str(output)+'}\n'
            body+='report_check_types -max_capacitance -max_slew -violators -digits 9 -no_line_splits >> {'+str(output)+'}\n'
            run('sizing-probe-'+str(index),body)
        (ROOT/'sizing-probes.json').write_text(json.dumps(dict(changes=probes,
            source=str(source),scope='Sizing estimates on sealed source RC; fresh process per candidate. No legalization, rerouting or physical acceptance.'),indent=2)+'\n')
        return
    paths=re.findall(r'Startpoint:.*?slack \((?:MET|VIOLATED)\)',report.read_text(),re.S)
    hold_guardband=float(spec.get('extracted_hold_guardband_ns',0))
    assert 0<=hold_guardband<=.1, 'Unexpected input hold optimization reserve'
    inputs=sorted({re.search(r'^Startpoint:\s+(\S+)',p)[1] for p in paths
        if '(input port' in p.split('Endpoint:')[0] and
        (p.endswith('(VIOLATED)') or float(re.search(r'([-+0-9.eE]+)\s+slack \((?:MET|VIOLATED)\)$',p)[1])<hold_guardband)})
    (ROOT/'extracted-eco-plan.json').write_text(json.dumps(dict(source=str(source),hold_input_guards=inputs,
        hold_guardband_ns=hold_guardband,
        drive_guardband=bool(spec.get('extracted_drive_guardband')),
        receiver_guardband=bool(spec.get('extracted_receiver_guardband')),
        repeaters=spec.get('extracted_repeaters',[]),replacements=spec.get('extracted_replacements',[])),indent=2)+'\n')
    if spec.get('extracted_inspect_only'):return
    body='remove_fillers\nset llhd_drive_root {'+str(ROOT)+'}\nset llhd_drive_phase extracted\n'
    body+='set llhd_drive_rounds 1\nset llhd_drive_use_extracted_rc 1\nset llhd_drive_checkpoint_only 1\nset llhd_enable_macro_guards 1\n'
    if spec.get('extracted_drive_guardband'):
        # Select from the actual extracted report, including MET pins with
        # little reserve. The existing 35% cap / 20% slew optimization reserve
        # changes physical drivers only; all final acceptance limits are fixed.
        body+='set llhd_drive_guardband 1\n'
    if spec.get('extracted_receiver_guardband'):
        body+='set llhd_drive_receiver_guardband 1\n'
    body+='source {'+str(track(ROOT/'runner/macro_guard.tcl'))+'}\nsource {'+str(track(ROOT/'runner/targeted_drive.tcl'))+'}\n'
    body+='source {'+str(track(ROOT/'runner/extracted_eco.tcl'))+'}\n'
    body+='set audit [open {'+str(ROOT/'extracted-eco-actions.tsv')+'} w]\n'
    for serial,port in enumerate(inputs):body+='puts $audit [llhd_delay_input {'+port+'} '+str(serial)+']\n'
    for serial,action in enumerate(spec.get('extracted_repeaters',[])):
        pin,master=action
        body+='puts $audit [llhd_repeat_driver {'+pin+'} {'+master+'} '+str(serial)+']\n'
    for name,before,after in spec.get('extracted_replacements',[]):
        body+='set inst [[ord::get_db_block] findInst {'+name+'}]\n'
        body+='if {$inst eq "NULL" || [[$inst getMaster] getName] ne {'+before+'}} {error {Unexpected extracted ECO driver}}\n'
        body+='if {![replace_cell {'+name+'} {'+after+'}]} {error {Extracted driver replacement failed}}\n'
        body+='puts $audit {'+name+' '+before+' '+after+'}\n'
    body+='close $audit\nglobal_connect\ndetailed_placement_helper\ncheck_placement -verbose\n'
    # Clear only regular signal dbWire, keeping every special PG shape. No
    # stale extracted RC is analyzed or accepted after this mutation.
    body+='set cleared 0\nforeach net [[ord::get_db_block] getNets] {if {[$net getSigType] in {POWER GROUND}} {continue};set wire [$net getWire];if {$wire ne "NULL"} {odb::dbWire_destroy $wire;incr cleared}}\n'
    body+='puts "CLEARED_SIGNAL_WIRES $cleared"\nwrite_db {'+str(results/'eco-modified.odb')+'}\nwrite_sdc -no_timestamp {'+str(results/'eco-modified.sdc')+'}\n'
    run('extracted-modify',body)
    script='source $::env(SCRIPTS_DIR)/load.tcl\nload_design eco-modified.odb eco-modified.sdc\n'
    script+='set_propagated_clock [all_clocks]\nset_routing_layers -signal metal2-metal10 -clock metal4-metal10\n'
    script+='set_global_routing_random -seed 0\npin_access\nglobal_route -congestion_iterations 30\nestimate_parasitics -global_routing\n'
    script+='report_check_types -max_capacitance -max_slew -max_count 1000 -digits 9 -no_line_splits > {'+str(ROOT/'extracted-eco-grt-estimates.rpt')+'}\n'
    script+='write_guides $::env(RESULTS_DIR)/route.guide\nwrite_db $::env(RESULTS_DIR)/5_1_grt.odb\nwrite_sdc -no_timestamp $::env(RESULTS_DIR)/5_1_grt.sdc\n'
    path=ROOT/'extracted-reroute.tcl';path.write_text(script)
    with (ROOT/'extracted-reroute.log').open('w') as f:
        subprocess.run(command+['RUN_SCRIPT='+str(path),'RUN_LOG_NAME_STEM=extracted-reroute','run'],stdout=f,stderr=subprocess.STDOUT,check=True)
    make_stages(ROOT/'config.mk',spec,['do-5_2_route','do-5_3_fillcell','do-5_route','do-5_route.sdc','do-finish'])
    qualify_parent_final()
