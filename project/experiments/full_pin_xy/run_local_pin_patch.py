"""Actual incremental reroute of three LL pins; retain original cells/PG/rules.

Start from the full PG-revision's real routed view with exactly four known
markers. No buffers, filler removal, rule changes, original OBS deletion or
clock constraint relaxation. Source/failure evidence remains immutable.
"""
from pathlib import Path
import csv,datetime,json,os,re,sys
from run_exports import ROOT,IMAGE,BIN,sha
from run_parent_trial import tcl
from run_escape_fixture import execute

DRIVER=Path(__file__).resolve().parent


def run(input_set,revision):
    inputs=ROOT/'inputs'/input_set;proposal=json.loads((inputs/'revision.json').read_text());assert proposal['changed_from_previous_full_C']==3
    source=ROOT/'finalized/llsys-pg-r03/llaccel_aux-C';proof=json.loads((source/'execution.json').read_text())
    assert proof['independent_DRC_count']==4 and proof['whole_access']['pass'] and proof['clean_byte_identical_to_pre_RCX_source']
    original=Path(proof['legacy_RC_STA_receipt']);old=json.loads(original.read_text());odb=source/'clean.odb';assert sha(odb)==proof['clean_odb_sha256']
    guide=original.parent/'route.guide';assert sha(guide)==old['outputs']['route.guide']['sha256']
    report=(source/'independent.drc').read_text();assert report.count('violation type:')==4
    assert all('net:'+q['pin'] in report for q in proposal['changes'])
    out=ROOT/'trials'/revision/'llaccel_aux-C';out.mkdir(parents=True,exist_ok=False)
    sdc=Path(old['source_sdc']);libs=old['libs'];assert sha(sdc)==old['input_sha256'][str(sdc)]
    helpers=(DRIVER/'physical_trial.tcl').read_text().split('if {![stage load {',1)[0]
    lines=[helpers]+['read_liberty '+tcl(p) for p in libs]
    lines+=['read_db '+tcl(odb),'read_sdc '+tcl(sdc),'source /OpenROAD-flow-scripts/flow/platforms/nangate45/setRC.tcl',
            '''proc ndr_snapshot {path} {set f [open $path w];foreach n [[ord::get_db_block] getNets] {set r [$n getNonDefaultRule];if {$r ne "NULL"} {puts $f [list [$n getName] [$r getName]]}};close $f}''',
            'fingerprint '+tcl(out/'before'),'ndr_snapshot '+tcl(out/'before.ndr.tsv'),
            'set_routing_layers -signal metal2-metal8 -clock metal4-metal8','read_guides '+tcl(guide),
            'set relocations {};source '+tcl(inputs/'llaccel_aux-C.tcl'),
            'set b [ord::get_db_block];set selected {};foreach row $relocations {lappend selected [[$b findBTerm [lindex $row 0]] getNet]}',
            'set nets {};foreach n $selected {lappend nets [$n getName]};set_nets_to_route $nets',
            'if {![stage begin_incremental {global_route -start_incremental}]} {close $stages;exit 1}',
            'if {![stage move {foreach row $relocations {lassign $row pin ly x y w h;place_pin -pin_name $pin -layer $ly -location [list $x $y] -pin_size [list $w $h]};fingerprint '+tcl(out/'moved')+';foreach n $selected {set w [$n getWire];if {$w ne "NULL"} {odb::dbWire_destroy $w}}}]} {close $stages;exit 1}',
            'if {![stage global_route {global_route -end_incremental -guide_file '+tcl(out/'route.guide')+' -congestion_report_file '+tcl(out/'congestion.rpt')+'}]} {close $stages;exit 1}',
            'if {![stage detailed_route {detailed_route -output_drc '+tcl(out/'route.drc')+' -verbose 1;write_db '+tcl(out/'routed.odb')+'}]} {close $stages;exit 1}',
            'fingerprint '+tcl(out/'after'),'ndr_snapshot '+tcl(out/'after.ndr.tsv'),
            'stage pdn_VDD {check_power_grid -net VDD -error_file '+tcl(out/'VDD.pdn.rpt')+'}',
            'stage pdn_VSS {check_power_grid -net VSS -error_file '+tcl(out/'VSS.pdn.rpt')+'}',
            'stage rcx {define_process_corner -ext_model_index 0 X;set_extraction_rules_file /OpenROAD-flow-scripts/flow/platforms/nangate45/rcx_patterns.rules;extract_parasitics;write_spef '+tcl(out/'extracted.spef')+';read_spef '+tcl(out/'extracted.spef')+'}',
            'stage sta {report_worst_slack -max -digits 6 > '+tcl(out/'timing.setup.txt')+';report_worst_slack -min -digits 6 > '+tcl(out/'timing.hold.txt')+';report_check_types -violators -max_delay -min_delay -max_slew -max_capacitance -max_fanout -recovery -removal -max_count 1000000 -digits 6 > '+tcl(out/'timing.checks.txt')+';check_setup -verbose > '+tcl(out/'timing.constraint_coverage.txt')+';report_parasitic_annotation -report_unannotated > '+tcl(out/'timing.parasitic_coverage.txt')+'}',
            'close $stages']
    script=out/'run.tcl';script.write_text('\n'.join(lines)+'\n')
    inp=[odb,source/'execution.json',source/'independent.drc',original,guide,sdc,inputs/'revision.json',inputs/'llaccel_aux-C.tcl']
    rec={'case':'llaccel_aux','plan':'C','revision':revision,'scope':'THREE_PIN_INCREMENTAL_REPAIR_OF_FULL_INTERNAL_C_NOT_YET_QUALIFIED',
         'selected_pin_count':3,'full_signal_pin_count':13507,'moved_from_original_boundary':13184,
         'source_odb':str(odb),'source_sha256':sha(odb),'source_config':old['source_config'],'source_sdc':str(sdc),'libs':libs,
         'original_baseline_odb':old['source_odb'],'input_sha256':{str(p):sha(p) for p in inp},
         'scheduler_job':os.environ['SLURM_JOB_ID'],'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),
         'full_qualification':False,'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    env='PINXY_OUTPUT={},PINXY_RELOCATIONS={},PINXY_DRIVER={}'.format(out,inputs/'llaccel_aux-C.tcl',DRIVER)
    common=['singularity','exec','--cleanenv','--bind',str(ROOT/'tmp')+':/tmp','--bind','/public/home/yuzelu/project-circuit:/public/home/yuzelu/project-circuit:ro',
            '--bind','/public/home/yuzelu/PingyangHuang/issue-55:/public/home/yuzelu/PingyangHuang/issue-55:ro','--home',str(ROOT/'home'),'--pwd',str(out)]
    rec['command']=common+['--env',env,IMAGE,BIN,'-threads','4','-no_init','-exit',str(script)]
    (out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n')
    rec['returncode']=execute(common,script,out/'openroad.log',env)
    rec['source_unchanged']=all(sha(Path(p))==h for p,h in rec['input_sha256'].items())
    rec['fingerprint_checks']={}
    for key in ['cells','pdn','die','ndr']:
        a,b=out/('before.'+key+'.tsv'),out/('after.'+key+'.tsv')
        rec['fingerprint_checks'][key]={'before_sha256':sha(a) if a.exists() else None,'after_sha256':sha(b) if b.exists() else None,
                                        'exact_equal':a.exists() and b.exists() and sha(a)==sha(b)}
    rec['status']='LOCAL_PATCH_COMMANDS_EXECUTED_CHECK_INDEPENDENT_RESULTS' if rec['returncode']==0 else 'ACTUAL_LOCAL_PATCH_FAILED'
    rec['finished_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    rec['outputs']={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in out.iterdir() if p.is_file()}
    (out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n');print(rec['status'],flush=True)
    return rec['returncode']


if __name__=='__main__':sys.exit(run(*sys.argv[1:3]))
