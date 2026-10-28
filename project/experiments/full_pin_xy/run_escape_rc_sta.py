"""Actual RC/STA on accepted ACT access fixtures, with explicit equal I/O policy.

This new research interface benchmark is separate from original leaf STA.
Identical original SDC/clocks, 0.2T/0.05T max/min I/O delays, BUF_X4 drive and
2/10/50 native-fF output loads are used in both variants. Full constraints,
annotation/violations and missing leaf minimum-period qualification remain.
No post-RCX database is saved or promoted as physical geometry.
"""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import datetime,json,os,re,sys,traceback
from run_exports import ROOT,sha
from run_parent_trial import tcl
from run_escape_fixture import execute

DRIVER=Path(__file__).resolve().parent


def one(variant,revision):
    if variant=='Aopt':source=ROOT/'escape_fixtures/r03/act-Aopt';model_dir=ROOT/'leaf_timing_models/r03/act-Aopt';geometry='routed.odb'
    else:source=ROOT/'escape_landing/r01/act-C';model_dir=ROOT/'leaf_timing_models/r04/act-C';geometry='routed.odb'
    physical=json.loads((source/'execution.json').read_text())
    assert physical.get('independent_DRC_count',physical.get('fresh_DRC_count'))==0 and physical['whole_signal_geometry']['pass']
    route_log=(source/'route.log').read_text();assert all('All shapes on net '+n+' are connected.' in route_log for n in ['VDD','VSS'])
    model=json.loads((model_dir/'execution.json').read_text());assert model['status']=='NATIVE_EXTRACTED_MODEL_EXPORTED_NOT_QUALIFIED' and model['exact_all_signal_pin_direction_match']
    leaf_fixture=source if variant=='Aopt' else ROOT/'escape_fixtures/r04/act-C'
    embedded=json.loads((leaf_fixture/'execution.json').read_text())
    assert embedded['source_clean_ODB_SHA']==model['clean_odb_sha256'] and embedded['matching_research_model_SHA']==sha(model_dir/'timing.lib')==model['generated_library_sha256']
    trial=Path(model['source_trial_receipt']);old=json.loads(trial.read_text());sdc=Path(old['source_sdc']);assert sha(sdc)==model['source_SDC_sha256']
    odb=source/geometry;out=ROOT/'escape_rc_sta'/revision/('act-'+variant);out.mkdir(parents=True,exist_ok=False)
    inputs={str(p):sha(p) for p in [odb,source/'execution.json',model_dir/'execution.json',model_dir/'timing.lib',sdc]}
    lines=['read_liberty /OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib',
           'read_liberty '+tcl(model_dir/'timing.lib'),'read_db '+tcl(odb),'read_sdc '+tcl(sdc),
           'source /OpenROAD-flow-scripts/flow/platforms/nangate45/setRC.tcl',
           'report_units','set clocks [all_clocks];if {[llength $clocks]!=1} {error "Expected exact single original clock"}',
           'set clk [lindex $clocks 0];set period [get_property $clk period]',
           'set in [remove_from_collection [all_inputs] [get_ports clk]]',
           'set_input_delay -clock $clk -max [expr {.2*$period}] $in',
           'set_input_delay -clock $clk -min [expr {.05*$period}] $in',
           'set_output_delay -clock $clk -max [expr {.2*$period}] [all_outputs]',
           'set_output_delay -clock $clk -min [expr {.05*$period}] [all_outputs]',
           'set_driving_cell -lib_cell BUF_X4 -pin Z $in','set_input_transition .05 [get_ports clk]',
           'write_sdc '+tcl(out/'research_interface.sdc'),
           'define_process_corner -ext_model_index 0 X','set_extraction_rules_file /OpenROAD-flow-scripts/flow/platforms/nangate45/rcx_patterns.rules',
           'extract_parasitics','write_spef '+tcl(out/'extracted.spef'),'read_spef '+tcl(out/'extracted.spef'),
           'report_wire_length -detailed_route -summary -file '+tcl(out/'wire_length.csv')]
    for load in [2,10,50]:
        prefix=out/('load'+str(load));lines+=['set_load '+str(load)+' [all_outputs]',
            'report_worst_slack -max -digits 6 > '+tcl(str(prefix)+'.setup.txt'),
            'report_worst_slack -min -digits 6 > '+tcl(str(prefix)+'.hold.txt'),
            'report_tns -max -digits 6 > '+tcl(str(prefix)+'.setup_tns.txt'),
            'report_tns -min -digits 6 > '+tcl(str(prefix)+'.hold_tns.txt'),
            'report_check_types -violators -max_delay -min_delay -max_slew -max_capacitance -max_fanout -recovery -removal -max_count 1000000 -digits 6 > '+tcl(str(prefix)+'.checks.txt'),
            'report_checks -path_delay min_max -group_path_count 12 -endpoint_path_count 1 -fields {capacitance slew fanout} -format full_clock_expanded -digits 6 > '+tcl(str(prefix)+'.critical.txt'),
            'check_setup -verbose > '+tcl(str(prefix)+'.constraint_coverage.txt'),
            'report_parasitic_annotation -report_unannotated > '+tcl(str(prefix)+'.parasitic_coverage.txt')]
    (out/'run.tcl').write_text('\n'.join(lines)+'\n')
    rec={'scope':'ACT_ACCESS_FIXTURE_RC_STA_UNDER_EXPLICIT_EQUAL_RESEARCH_IO_POLICY_NOT_FULL_SYSTEM_QUALIFICATION','variant':variant,
         'source_inputs_SHA':inputs,'source_original_SDC_SHA':sha(sdc),'original_clock_unchanged':True,'native_output_loads_intended_fF':[2,10,50],
         'new_IO_policy_not_original_leaf_PPA':['max I/O delay0.2T','min I/O delay0.05T','BUF_X4 input drive','clock transition0.05ns','output load sensitivity2/10/50fF; native report_units must be inspected'],
         'leaf_internal_failures_not_replaced':True,'leaf_minimum_period_present':model['minimum_period_present'],'full_qualification':False,
         'post_RCX_ODB_saved_or_promoted':False,'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),'scheduler_job':os.environ['SLURM_JOB_ID']}
    (out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n')
    common=['singularity','exec','--cleanenv','--bind',str(ROOT/'tmp')+':/tmp','--bind','/public/home/yuzelu/project-circuit:/public/home/yuzelu/project-circuit:ro',
            '--bind','/public/home/yuzelu/PingyangHuang/issue-55:/public/home/yuzelu/PingyangHuang/issue-55:ro','--home',str(ROOT/'home'),'--pwd',str(out)]
    rec['native_returncode']=execute(common,out/'run.tcl',out/'native.log')
    rec['observations']={}
    for load in [2,10,50]:
        row={}
        for kind in ['setup','hold']:
            p=out/('load'+str(load)+'.'+kind+'.txt');m=re.search(r'worst slack (?:max|min)\s+([-\d.]+)',p.read_text()) if p.exists() else None
            row[kind+'_ns']=float(m[1]) if m else None
        p=out/('load'+str(load)+'.checks.txt');row['violation_rows']=sum('(VIOLATED)' in s for s in p.read_text().splitlines()) if p.exists() else None
        rec['observations'][str(load)]=row
    rec['all_source_files_unchanged']=all(sha(Path(p))==h for p,h in inputs.items())
    rec['status']='RC_STA_REPORTS_EXECUTED_REVIEW_FAILURES_AND_COVERAGE_NOT_QUALIFIED' if rec['native_returncode']==0 else 'ACTUAL_FIXTURE_RC_STA_FAILED_OR_INCOMPLETE'
    rec['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();rec['files']={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in out.iterdir() if p.is_file()}
    (out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n');print(variant,rec['status'],flush=True)
    return rec['native_returncode']==0 and rec['all_source_files_unchanged']


def safe(args):
    try:return one(*args)
    except Exception:traceback.print_exc();return False


if __name__=='__main__':
    assert int(os.environ['SLURM_CPUS_PER_TASK'])>=8
    a=json.loads((ROOT/'leaf_timing_models/r03/act-Aopt/execution.json').read_text())
    c=json.loads((ROOT/'leaf_timing_models/r04/act-C/execution.json').read_text())
    assert a['source_SDC_sha256']==c['source_SDC_sha256'],'The two original clock/constraint sources must be identical'
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(safe,[(v,sys.argv[1]) for v in ['Aopt','C']]))
    sys.exit(0 if all(results) else 1)
