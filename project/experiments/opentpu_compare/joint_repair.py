"""Alternate native repairs through real checkpoints, in fresh tool processes."""
import json
from pathlib import Path
import re
import shutil
import subprocess


def execute(root,spec,meta):
    results=root/meta['result_relative']
    command=['make','-C','/OpenROAD-flow-scripts/flow','DESIGN_CONFIG='+str(root/'config.mk'),
             'WORK_HOME='+str(root/'flow'),'NUM_CORES='+str(spec['cores'])]
    for ext in ['odb','sdc']:
        shutil.copy2(results/('5_1_grt.'+ext),results/('joint-initial.'+ext))
    previous='joint-initial'
    guard_state=root/'joint-guard-state.tcl'
    guard_state.write_text('set llhd_guarded [dict create]\n')
    audit=[]

    def run(name,body):
        script='source $::env(SCRIPTS_DIR)/load.tcl\n'
        script+='load_design '+previous+'.odb '+previous+'.sdc\n'
        script+='set_propagated_clock [all_clocks]\n'
        script+='set_routing_layers -signal metal2-metal10 -clock metal4-metal10\n'
        script+='set_placement_padding -global -left $::env(CELL_PAD_IN_SITES_DETAIL_PLACEMENT) -right $::env(CELL_PAD_IN_SITES_DETAIL_PLACEMENT)\n'
        # Reconstruct genuine global routes and RC after every reload. Do not
        # reuse estimates from the previous, mutated in-memory design.
        script+='set_global_routing_random -seed 0\npin_access\nglobal_route -congestion_iterations 30\nestimate_parasitics -global_routing\n'
        script+=body
        script+='orfs_write_db $::env(RESULTS_DIR)/'+name+'.odb\n'
        script+='orfs_write_sdc $::env(RESULTS_DIR)/'+name+'.sdc\n'
        script+='write_guides $::env(RESULTS_DIR)/'+name+'.guide\n'
        path=root/(name+'.tcl');path.write_text(script)
        with (root/(name+'.log')).open('w') as f:
            subprocess.run(command+['RUN_SCRIPT='+str(path),'RUN_LOG_NAME_STEM='+name,'run'],
                           stdout=f,stderr=subprocess.STDOUT,check=True)

    skip=' -skip_gate_cloning -skip_pin_swap -skip_size_down -skip_buffer_removal -skip_buffer_to_inverters -verbose\n'
    for phase in range(int(spec['joint_repair_rounds'])):
        name='joint-'+str(phase)+'-timing'
        body='repair_timing -setup -setup_margin '+str(spec['setup_target_ns'])+' -repair_tns 100'+skip
        body+='estimate_parasitics -global_routing\nrepair_timing -hold -hold_margin '+str(spec.get('hold_target_ns',0.02))+skip
        body+='global_route -start_incremental\ndetailed_placement_helper\ncheck_placement -verbose\nglobal_route -end_incremental\n'
        run(name,body);previous=name
        name='joint-'+str(phase)+'-electrical'
        # Initialize native resizer state after a fresh reload. Buffer
        # insertion itself uses checked ODB edits, not the crashing helper.
        body='if {[llength [info commands rsz::resize_slack_preamble]]!=1} {error {Missing native resizer preamble}}\nrsz::resize_slack_preamble\n'
        if spec.get('joint_native_electrical_repair'):
            body+='repair_design -cap_margin 35 -slew_margin 20 -reroute -verbose\n'
            body+='global_route -start_incremental\ndetailed_placement_helper\ncheck_placement -verbose\nglobal_route -end_incremental\n'
            body+='global_route -congestion_iterations 30\nestimate_parasitics -global_routing\n'
        body+='set llhd_drive_root {'+str(root)+'}\nset llhd_drive_rounds '+str(spec['targeted_drive_rounds'])+'\n'
        if spec.get('full_route_each_drive_round'):body+='set llhd_drive_full_route 1\n'
        body+='set llhd_drive_phase joint'+str(phase)+'\nset llhd_drive_guardband 1\nset llhd_enable_macro_guards 1\n'
        body+='source {'+str(guard_state)+'}\nsource {'+str(root/'runner/macro_guard.tcl')+'}\n'
        body+='source {'+str(root/'runner/targeted_drive.tcl')+'}\n'
        body+='set f [open {'+str(guard_state)+'} w]\nputs $f [list set llhd_guarded $llhd_guarded]\nclose $f\n'
        run(name,body);previous=name
        name='joint-'+str(phase)+'-audit'
        report=root/'joint-final-quality.rpt'
        body='report_worst_slack -max -digits 9 > {'+str(report)+'}\n'
        body+='report_worst_slack -min -digits 9 >> {'+str(report)+'}\n'
        body+='puts {POST_GRT_FINAL_ELECTRICAL_CHECK}\n'
        body+='report_check_types -max_capacitance -max_slew -max_count 1000 -digits 9 -no_line_splits >> {'+str(report)+'}\n'
        run(name,body);previous=name
        text=report.read_text()
        setup=float(re.search(r'worst slack max\s+([-+0-9.eE]+)',text)[1])
        hold=float(re.search(r'worst slack min\s+([-+0-9.eE]+)',text)[1])
        margins=re.findall(r'^\s*\S+\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)\s+\((?:MET|VIOLATED)\)',text,re.M)
        electrical=bool(margins) and all(float(row[2])>=0 for row in margins) and '(VIOLATED)' not in text
        audit.append(dict(phase=phase,setup_ns=setup,hold_ns=hold,electrical_passed=electrical))
        (root/'joint-repair.json').write_text(json.dumps(audit,indent=2)+'\n')
        (root/'joint-repair.tsv').write_text('phase\tsetup_ns\thold_ns\telectrical_passed\n'+
            ''.join('%s\t%s\t%s\t%s\n'%(r['phase'],r['setup_ns'],r['hold_ns'],r['electrical_passed']) for r in audit))
        if setup>=float(spec['setup_accept_ns']) and hold>=float(spec.get('hold_accept_ns',0)) and electrical:
            for ext in ['odb','sdc']:
                shutil.copy2(results/(previous+'.'+ext),results/('5_1_grt.'+ext))
            shutil.copy2(results/(previous+'.guide'),results/'route.guide')
            return
    raise AssertionError('Joint GRT timing/electrical margin insufficient; retained all real checkpoints before DRT')
