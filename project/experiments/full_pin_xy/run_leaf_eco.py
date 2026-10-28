"""Separate, costed native cell-sizing/buffering experiment under original SDC.

This is NOT a pure pin-XY result. Original A and the previously independently
validated full C are controls; new access-window runs remain independent. No
clock relaxation, pipeline/protocol/resource redesign, or rule deletion.
"""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import datetime, json, os, re, sys, traceback
from run_exports import ROOT, sha
from run_parent_trial import BASE, C_REVISION, tcl
from run_escape_fixture import execute
from check_access import check

DRIVER=Path(__file__).resolve().parent


def one(case,variant,revision):
    assert case=='vector' and variant in ['A','C']
    physical=BASE[case] if variant=='A' else C_REVISION[case]
    source=ROOT/'finalized'/physical/(case+'-'+variant);proof=json.loads((source/'execution.json').read_text())
    assert proof['independent_DRC_count']==0 and proof['whole_access']['pass'] and proof['clean_byte_identical_to_pre_RCX_source']
    trial=Path(proof['legacy_RC_STA_receipt']);old=json.loads(trial.read_text());odb=source/'clean.odb';spef=trial.parent/'extracted.spef';sdc=Path(old['source_sdc'])
    assert sha(odb)==proof['clean_odb_sha256'] and sha(spef)==old['outputs']['extracted.spef']['sha256'] and sha(sdc)==old['input_sha256'][str(sdc)]
    out=ROOT/'leaf_eco'/revision/(case+'-'+variant);out.mkdir(parents=True,exist_ok=False)
    inputs={str(p):sha(p) for p in [odb,spef,sdc,trial,source/'execution.json']}
    # Reuse the existing exact geometry fingerprint/stage helpers, not the
    # original trial's load/move/route body.
    helpers=(DRIVER/'physical_trial.tcl').read_text().split('if {![stage load {',1)[0]
    assert 'proc fingerprint ' in helpers
    lines=[helpers]+['read_liberty '+tcl(p) for p in old['libs']]
    lines+=['read_db '+tcl(odb),'read_sdc '+tcl(sdc),'source /OpenROAD-flow-scripts/flow/platforms/nangate45/setRC.tcl','read_spef '+tcl(spef),
            'fingerprint '+tcl(out/'before'),
            'report_worst_slack -max -digits 6 > '+tcl(out/'before.setup.txt'),
            'report_worst_slack -min -digits 6 > '+tcl(out/'before.hold.txt'),
            'if {![stage cell_repair {remove_fillers;repair_design -max_utilization 85;repair_timing -setup -skip_pin_swap -skip_gate_cloning -skip_buffer_removal -skip_buffer_to_inverters -max_passes 20 -max_iterations 10000 -max_utilization 85 -verbose}]} {close $stages;exit 1}',
            'if {![stage legalization {detailed_placement;check_placement -verbose}]} {close $stages;exit 1}',
            'if {![stage rip_signal_routes {foreach n [[ord::get_db_block] getNets] {if {[$n getSigType] ni {POWER GROUND}} {set w [$n getWire];if {$w ne "NULL"} {odb::dbWire_destroy $w}}}}]} {close $stages;exit 1}',
            'set_routing_layers -signal metal2-metal10 -clock metal4-metal10',
            'if {![stage global_route {global_route -allow_congestion -guide_file '+tcl(out/'route.guide')+' -congestion_report_file '+tcl(out/'congestion.rpt')+'}]} {close $stages;exit 1}',
            'if {![stage detailed_route {detailed_route -output_drc '+tcl(out/'route.drc')+' -verbose 1;write_db '+tcl(out/'routed.odb')+'}]} {close $stages;exit 1}',
            'fingerprint '+tcl(out/'after'),
            'stage VDD {check_power_grid -net VDD -error_file '+tcl(out/'VDD.rpt')+'}',
            'stage VSS {check_power_grid -net VSS -error_file '+tcl(out/'VSS.rpt')+'}',
            'stage whole_signal_geometry {source '+tcl(DRIVER/'export_access.tcl')+'}',
            'stage rcx {define_process_corner -ext_model_index 0 X;set_extraction_rules_file /OpenROAD-flow-scripts/flow/platforms/nangate45/rcx_patterns.rules;extract_parasitics;write_spef '+tcl(out/'extracted.spef')+';read_spef '+tcl(out/'extracted.spef')+'}',
            'stage sta {report_worst_slack -max -digits 6 > '+tcl(out/'setup.txt')+';report_worst_slack -min -digits 6 > '+tcl(out/'hold.txt')+';report_check_types -violators -max_delay -min_delay -max_slew -max_capacitance -max_fanout -recovery -removal -max_count 1000000 -digits 6 > '+tcl(out/'checks.txt')+';check_setup -verbose > '+tcl(out/'constraint_coverage.txt')+';report_parasitic_annotation -report_unannotated > '+tcl(out/'parasitic_coverage.txt')+'}',
            'close $stages']
    (out/'run.tcl').write_text('\n'.join(lines)+'\n')
    rec={'scope':'COSTED_CELL_ECO_EXPERIMENT_NOT_PURE_XY_OR_FULL_QUALIFICATION','case':case,'variant':variant,'source_physical_revision':physical,
         'source_inputs_SHA':inputs,'original_SDC_and_clocks_unchanged':True,'cell_sizing_buffering_and_placement_changes_separate_cost':True,
         'new_access_window_trial_replaced':False,'equivalence_not_yet_verified':True,'full_qualification':False,
         'GRT_overflow_permitted_for_guides_only_not_pass':True,'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),
         'scheduler_job':os.environ['SLURM_JOB_ID'],'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    (out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n')
    common=['singularity','exec','--cleanenv','--bind',str(ROOT/'tmp')+':/tmp','--bind','/public/home/yuzelu/project-circuit:/public/home/yuzelu/project-circuit:ro',
            '--bind','/public/home/yuzelu/PingyangHuang/issue-55:/public/home/yuzelu/PingyangHuang/issue-55:ro','--home',str(ROOT/'home'),'--pwd',str(out)]
    env='PINXY_OUTPUT={},PINXY_ACCESS_ALL=1,PINXY_ACCESS_OUT={}'.format(out,out/'whole_access.tsv.gz')
    rec['native_returncode']=execute(common,out/'run.tcl',out/'native.log',env)
    if (out/'routed.odb').exists():
        fresh=out/'fresh.tcl';fresh.write_text('read_db '+tcl(out/'routed.odb')+'\nset_routing_layers -signal metal2-metal10 -clock metal4-metal10\ndrt::check_drc -output_file '+tcl(out/'independent.drc')+'\n')
        rec['fresh_DRC_returncode']=execute(common,fresh,out/'independent.log',threads=1)
        p=out/'independent.drc';rec['fresh_DRC_count']=len(re.findall(r'^violation type:',p.read_text(),re.M)) if rec['fresh_DRC_returncode']==0 and p.exists() else None
    if (out/'whole_access.tsv.gz').exists():rec['whole_signal_geometry']=check(out/'whole_access.tsv.gz',True)
    rec['geometry_invariants']={}
    for kind in ['pins','pdn','die']:
        a,b=out/('before.'+kind+'.tsv'),out/('after.'+kind+'.tsv')
        rec['geometry_invariants'][kind+'_byteexact_unchanged']=a.exists() and b.exists() and sha(a)==sha(b)
    rec['source_unchanged']=all(sha(Path(p))==h for p,h in inputs.items())
    rec['status']='ECO_EXECUTED_CHECK_ALL_RESULTS_NOT_QUALIFIED' if rec['native_returncode']==0 else 'ACTUAL_ECO_FAILED_OR_INCOMPLETE'
    rec['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    rec['files']={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in out.iterdir() if p.is_file()}
    (out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n');print('COSTED_ECO',variant,rec['status'],flush=True)
    return rec['native_returncode']==0


def safe(args):
    try:return one(*args)
    except Exception:
        traceback.print_exc();return False


if __name__=='__main__':
    assert int(os.environ['SLURM_CPUS_PER_TASK'])>=8
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(safe,[('vector',v,sys.argv[1]) for v in ['A','C']]))
    sys.exit(0 if all(results) else 1)
