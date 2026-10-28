"""Read-only placement/CTS path diagnosis; never grants final timing acceptance."""
import json
from pathlib import Path


def diagnose(root,out,cpus,run,kind):
    from io_slots import file_sha
    assert cpus==16 and kind in ('v','r')
    base=out.parents[2]
    number,day,checkpoint,sdc,required=(
        ('291','20261029','3_5_place_dp.odb','3_place.sdc','do-place') if kind=='v' else
        ('236','20261028','4_cts.odb','4_cts.sdc','do-cts'))
    source=base/('block-v1-'+day+'-'+number)/('tasks/revision300-route-'+kind)
    flow=json.loads((source/'revision300-native-flow.json').read_text())
    assert required in flow['stages'] and flow['top']=='block_v1_'+kind
    results=source/('flow/results/nangate45/bv1_block_v1_'+kind+'/base')
    platform=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45')
    paths=[results/checkpoint,results/sdc,source/'input.v',source/'config.mk',
           platform/'setRC.tcl',platform/'lib/NangateOpenCellLibrary_typical.lib']
    inputs={str(p):dict(sha256=file_sha(p),bytes=p.stat().st_size) for p in paths}
    script='set_thread_count 16\nread_liberty {'+str(paths[-1])+'}\n'
    script+='read_db {'+str(results/checkpoint)+'}\nread_sdc {'+str(results/sdc)+'}\n'
    script+='source {'+str(platform/'setRC.tcl')+'}\nestimate_parasitics -placement\n'
    if kind=='r':script+='set_propagated_clock [all_clocks]\n'
    script+='sta::find_timing\n'
    script+='report_worst_slack -max -digits 9 > paths.rpt\n'
    script+='report_worst_slack -min -digits 9 >> paths.rpt\n'
    script+='report_checks -path_delay min_max -group_path_count 12 -digits 9 -format full_clock_expanded >> paths.rpt\n'
    script+='report_check_types -max_capacitance -max_slew -max_fanout -max_count 12 -digits 9 -no_line_splits > electrical.rpt\n'
    script+='set f [open summary.tsv w]\n'
    script+='puts $f "setup_violations\\t[sta::endpoint_violation_count max]"\n'
    script+='puts $f "hold_violations\\t[sta::endpoint_violation_count min]"\nclose $f\n'
    (out/'diagnose.tcl').write_text(script)
    run(['openroad','-no_init','-exit',out/'diagnose.tcl'],'diagnose.log')
    assert inputs=={str(p):dict(sha256=file_sha(p),bytes=p.stat().st_size) for p in paths}
    assert (out/'paths.rpt').stat().st_size>100
    report=dict(passed=True,experiment_completed=True,macro=kind.upper(),source_inputs=inputs,
        producer_stage_completed=required,checkpoint=checkpoint,source_original_files_unchanged=True,
        rc_model='Native platform setRC.tcl; placement estimate, not extracted final RC',
        clock_model='propagated CTS'if kind=='r'else'ideal pre-CTS placement clock',
        final_timing_qualified=False,new_physical_implementation=False,
        scope='Read-only critical-path diagnosis on an already completed checkpoint while original native flow continues. No repair, source/layout mutation, false path or final acceptance. Execution success is not timing pass.')
    (out/'revision300-checkpoint-timing.json').write_text(json.dumps(report,indent=2)+'\n')
