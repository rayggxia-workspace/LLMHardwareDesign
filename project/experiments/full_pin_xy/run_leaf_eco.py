"""Separate, costed native cell-sizing/buffering experiment under original SDC.

This is NOT a pure pin-XY result. Original A and the previously independently
validated full C are controls; new access-window runs remain independent. No
clock relaxation, pipeline/protocol/resource redesign, or rule deletion.
"""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import csv, datetime, json, os, re, subprocess, sys, traceback
from run_exports import ROOT, IMAGE, sha
from run_parent_trial import BASE, C_REVISION, tcl
from run_escape_fixture import execute
from check_access import check

DRIVER=Path(__file__).resolve().parent


def one(case,variant,revision):
    assert case in ['vector','gemm','mxu','opentpu_aux'] and variant in ['A','C']
    physical=BASE[case] if variant=='A' else C_REVISION[case]
    source=ROOT/'finalized'/physical/(case+'-'+variant);proof=json.loads((source/'execution.json').read_text())
    assert proof['independent_DRC_count']==0 and proof['whole_access']['pass'] and proof['clean_byte_identical_to_pre_RCX_source']
    trial=Path(proof['legacy_RC_STA_receipt']);old=json.loads(trial.read_text());odb=source/'clean.odb';spef=trial.parent/'extracted.spef';sdc=Path(old['source_sdc'])
    assert sha(odb)==proof['clean_odb_sha256'] and sha(spef)==old['outputs']['extracted.spef']['sha256'] and sha(sdc)==old['input_sha256'][str(sdc)]
    out=ROOT/'leaf_eco'/revision/(case+'-'+variant);out.mkdir(parents=True,exist_ok=False)
    electrical_only=os.environ.get('PINXY_ECO_ELECTRICAL_ONLY')=='1'
    incremental=os.environ.get('PINXY_ECO_INCREMENTAL')=='1'
    targeted=os.environ.get('PINXY_ECO_TARGETED')=='1'
    rc_heuristic=os.environ.get('PINXY_ECO_PLACEMENT_HEURISTIC')=='1'
    fix_hold=os.environ.get('PINXY_ECO_HOLD')=='1'
    assert not rc_heuristic or (incremental and not targeted)
    assert not targeted or (electrical_only and incremental and case in ['gemm','mxu'] and variant=='C')
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
    if electrical_only:
        lines=[s.replace('repair_timing -setup -skip_pin_swap -skip_gate_cloning -skip_buffer_removal -skip_buffer_to_inverters -max_passes 20 -max_iterations 10000 -max_utilization 85 -verbose','puts "ELECTRICAL_ONLY_NO_SETUP_OPTIMIZATION"') for s in lines]
    if incremental:
        guide=trial.parent/'route.guide';assert guide.exists();inputs[str(guide)]=sha(guide)
        assert sha(guide)==old['outputs']['route.guide']['sha256']
        i=next(i for i,s in enumerate(lines) if s.startswith('if {![stage cell_repair'))
        lines[i:i]=['set_routing_layers -signal metal2-metal10 -clock metal4-metal10','read_guides '+tcl(guide),
                    'if {![stage begin_incremental {global_route -start_incremental}]} {close $stages;exit 1}']
        lines=[s for s in lines if not s.startswith('if {![stage rip_signal_routes')]
        lines=[s.replace('global_route -allow_congestion -guide_file','global_route -end_incremental -allow_congestion -guide_file') for s in lines]
    if rc_heuristic:
        # read_guides/start_incremental invalidated the resizer's estimated-RC
        # state in r01/r02 (EST-0027); do not misdescribe WLM as extracted-RC
        # optimization. Replay exact source SPEF, then explicitly switch to
        # a placement heuristic for repair. The installed resizer rejects
        # SPEF as its active estimator (r06 EST-0104). Only final fresh RCX/STA
        # determines the physical outcome; heuristic slack is separate.
        i=next(i for i,s in enumerate(lines) if s.startswith('if {![stage cell_repair'))
        lines[i:i]=['if {![stage repair_RC_model {estimate_parasitics -placement;read_spef '+tcl(spef)+';report_parasitic_annotation -report_unannotated > '+tcl(out/'repair_RC_coverage.txt')+';report_worst_slack -max -digits 6 > '+tcl(out/'repair_before.setup.txt')+';report_worst_slack -min -digits 6 > '+tcl(out/'repair_before.hold.txt')+'}]} {close $stages;exit 1}']
        lines[i+1:i+1]=['if {![stage exact_source_STA_replayed {foreach kind {setup hold} {set a [open [file join '+tcl(out)+' before.$kind.txt] r];set av [read $a];close $a;set b [open [file join '+tcl(out)+' repair_before.$kind.txt] r];set bv [read $b];close $b;if {$av ne $bv} {error "Exact source SPEF STA changed before cell repair"}}}]} {close $stages;exit 1}']
        lines[i+2:i+2]=['if {![stage declared_repair_heuristic {estimate_parasitics -placement;report_worst_slack -max -digits 6 > '+tcl(out/'heuristic_before.setup.txt')+';report_worst_slack -min -digits 6 > '+tcl(out/'heuristic_before.hold.txt')+'}]} {close $stages;exit 1}']
    if fix_hold:
        assert not electrical_only and not targeted
        lines=[s.replace('-max_utilization 85 -verbose}]}',
                         '-max_utilization 85 -verbose;repair_timing -hold -max_utilization 85 -verbose}]}')
               if s.startswith('if {![stage cell_repair') else s for s in lines]
    if rc_heuristic:
        i=next(i for i,s in enumerate(lines) if s.startswith('if {![stage cell_repair'))
        lines[i]=lines[i].replace('remove_fillers;',
             'set eco_fillers {};foreach fi [[ord::get_db_block] getInsts] {set fm [$fi getMaster];if {[$fm getType] eq "CORE_SPACER"} {lappend eco_fillers [$fm getName]}};set eco_fillers [lsort -unique $eco_fillers];remove_fillers;')
        lines=[s.replace('detailed_placement;check_placement -verbose',
              'detailed_placement;check_placement -verbose;filler_placement -prefix PINXY_RC_FILL_ $eco_fillers;global_connect;check_placement -verbose') for s in lines]
        lines=[s.replace('global_route -end_incremental -allow_congestion','global_route -end_incremental') for s in lines]
    replacements=[]
    if targeted:
        from cell_semantics import check_pair
        # Exact masters and escaping were read from the actual source ODB in
        # constraint_audit/r04, not guessed from report display names.
        replacements=([('place15450','BUF_X1','BUF_X2'),('_328297_','XOR2_X1','XOR2_X2'),
                       (r'rq_m\[341\]$_DFFE_PN0P_','DFFR_X1','DFFR_X2')]
                      if case=='gemm' else [('place10281','BUF_X1','BUF_X2')])
        lib_text={p:Path(p).read_text() if Path(p).is_file() else subprocess.check_output(['singularity','exec','--cleanenv',
                  '--bind','/public/home/yuzelu/project-circuit:/public/home/yuzelu/project-circuit:ro',
                  '--bind','/public/home/yuzelu/PingyangHuang/issue-55:/public/home/yuzelu/PingyangHuang/issue-55:ro',
                  '--home',str(ROOT/'home'),IMAGE,'cat',p]).decode()
                  for p in old['libs']}
        logic_contracts=[check_pair([Path(p) for p in old['libs']],a,b,lambda p:lib_text[str(p)]) for _,a,b in replacements]
        (out/'replacement_logic_contracts.json').write_text(json.dumps(logic_contracts,indent=2)+'\n')
        replacement_tcl=['set b [ord::get_db_block];set filler_masters {};foreach i [$b getInsts] {set m [$i getMaster];if {[$m getType] eq "CORE_SPACER"} {lappend filler_masters [$m getName]}};set filler_masters [lsort -unique $filler_masters];if {![llength $filler_masters]} {error "Original filler master set missing"}',
          'proc terminal_contract {inst} {set result {};foreach it [$inst getITerms] {set n [$it getNet];lappend result [list [[$it getMTerm] getName] [[$it getMTerm] getIoType] [expr {$n eq "NULL" ? "NULL" : [$n getName]}]]};return [lsort $result]}',
          'remove_fillers']
        for inst,old_master,new_master in replacements:
            replacement_tcl+=['set i [$b findInst '+tcl(inst)+'];if {$i eq "NULL" || [[$i getMaster] getName] ne '+tcl(old_master)+'} {error "Exact targeted source master changed"}',
              'set prior [terminal_contract $i];replace_cell '+tcl(inst)+' '+tcl(new_master)+';set i [$b findInst '+tcl(inst)+'];if {[terminal_contract $i] ne $prior || [[$i getMaster] getName] ne '+tcl(new_master)+'} {error "Replacement changed terminal semantics"}']
        i=next(i for i,s in enumerate(lines) if s.startswith('if {![stage cell_repair'))
        lines[i]='if {![stage cell_repair {'+';'.join(replacement_tcl)+'}]} {close $stages;exit 1}'
        lines=[s.replace('detailed_placement;check_placement -verbose',
                         'detailed_placement -incremental;check_placement -verbose;filler_placement -prefix PINXY_CAP_FILL_ $filler_masters;global_connect;check_placement -verbose') for s in lines]
        # No guide overflow waiver in this new targeted implementation. Earlier
        # runs and any real failures remain in their immutable directories.
        lines=[s.replace('global_route -end_incremental -allow_congestion','global_route -end_incremental') for s in lines]
    reservation_keys=[p for p in old['input_sha256'] if p.endswith('/access_reservations.tcl')]
    if reservation_keys:
        assert len(reservation_keys)==1
        reservations=Path(reservation_keys[0]);assert sha(reservations)==old['input_sha256'][str(reservations)]
        inputs[str(reservations)]=sha(reservations)
        setup=['set b [ord::get_db_block];set u [$b getDbUnitsPerMicron];set prior_OBS [lsort [$b getObstructions]];set new_ECO_OBS {}',
               'set access_reservations {};source '+tcl(reservations),
               'foreach row $access_reservations {lassign $row ly x0 y0 x1 y1;set c {};foreach v [list $x0 $y0 $x1 $y1] {lappend c [expr {round($v*$u)}]};lappend new_ECO_OBS [odb::dbObstruction_create $b [[ord::get_db_tech] findLayer $ly] {*}$c]}']
        i=next(i for i,s in enumerate(lines) if s.startswith('fingerprint '));lines[i:i]=setup
        cleanup='foreach ob $new_ECO_OBS {odb::dbObstruction_destroy $ob};if {[lsort [[ord::get_db_block] getObstructions]] ne $prior_OBS} {error "Original OBS changed"};'
        lines=[s.replace('write_db '+tcl(out/'routed.odb'),cleanup+'write_db '+tcl(out/'routed.odb')) for s in lines]
    # Native master dimensions/type distinguish removed filler from functional
    # cell/buffer costs. Never interpret filler removal as block area savings.
    cost_proc='''proc cell_cost {file} {
 set b [ord::get_db_block];set u [$b getDbUnitsPerMicron];set f [open $file w]
 puts $f "instance\\tmaster\\ttype\\tarea_um2\\tx_dbu\\ty_dbu"
 foreach i [$b getInsts] {set m [$i getMaster];lassign [$i getLocation] x y;puts $f [join [list [$i getName] [$m getName] [$m getType] [expr {[$m getWidth]*double([$m getHeight])/($u*$u)}] $x $y] "\\t"]};close $f
}'''
    lines.insert(0,cost_proc)
    lines=[s+'\ncell_cost '+tcl(out/('before.cell_cost.tsv' if '/before}' in s else 'after.cell_cost.tsv')) if s.startswith('fingerprint ') else s for s in lines]
    if case.endswith('_aux'):
        lines=[s.replace('-signal metal2-metal10 -clock metal4-metal10','-signal metal2-metal8 -clock metal4-metal8') for s in lines]
    (out/'run.tcl').write_text('\n'.join(lines)+'\n')
    rec={'scope':'COSTED_CELL_ECO_EXPERIMENT_NOT_PURE_XY_OR_FULL_QUALIFICATION','case':case,'variant':variant,'source_physical_revision':physical,
         'source_inputs_SHA':inputs,'original_SDC_and_clocks_unchanged':True,'cell_sizing_buffering_and_placement_changes_separate_cost':True,
         'new_access_window_trial_replaced':False,'equivalence_not_yet_verified':True,'full_qualification':False,
         'electrical_only_repair':electrical_only,'incremental_route_attempt':incremental,'same_source_access_windows_retained':bool(reservation_keys),
         'targeted_master_changes':replacements,'fillers_restored_with_original_master_set':targeted or rc_heuristic,
         'repair_estimator':'EXACT_SOURCE_SPEF_REPLAY_THEN_DECLARED_PLACEMENT_HEURISTIC' if rc_heuristic else 'LEGACY_OR_TARGETED_NO_ESTIMATOR_FIX',
         'hold_repair_requested':fix_hold,'final_timing_requires_fresh_extraction':True,
         'replacement_logic_state_precheck':'EXACT_LIBERTY_FUNCTION_AND_SEQUENTIAL_STATE_CONTRACT' if targeted else 'NOT_EXECUTED',
         'design_formal_equivalence':'NOT_EXECUTED',
         'GRT_overflow_permitted_for_guides_only_not_pass':not (targeted or rc_heuristic),'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),
         'scheduler_job':os.environ['SLURM_JOB_ID'],'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    (out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n')
    common=['singularity','exec','--cleanenv','--bind',str(ROOT/'tmp')+':/tmp','--bind','/public/home/yuzelu/project-circuit:/public/home/yuzelu/project-circuit:ro',
            '--bind','/public/home/yuzelu/PingyangHuang/issue-55:/public/home/yuzelu/PingyangHuang/issue-55:ro','--home',str(ROOT/'home'),'--pwd',str(out)]
    if targeted or rc_heuristic:
        for p in old['libs']:
            if Path(p).is_file():common+=['--bind',p+':'+p+':ro']
    env='PINXY_OUTPUT={},PINXY_ACCESS_ALL=1,PINXY_ACCESS_OUT={}'.format(out,out/'whole_access.tsv.gz')
    rec['native_returncode']=execute(common,out/'run.tcl',out/'native.log',env)
    if (out/'routed.odb').exists():
        top='8' if case.endswith('_aux') else '10'
        fresh=out/'fresh.tcl';fresh.write_text('read_db '+tcl(out/'routed.odb')+'\nset_routing_layers -signal metal2-metal'+top+' -clock metal4-metal'+top+'\ndrt::check_drc -output_file '+tcl(out/'independent.drc')+'\n')
        rec['fresh_DRC_returncode']=execute(common,fresh,out/'independent.log',threads=1)
        p=out/'independent.drc';rec['fresh_DRC_count']=len(re.findall(r'^violation type:',p.read_text(),re.M)) if rec['fresh_DRC_returncode']==0 and p.exists() else None
    if (out/'whole_access.tsv.gz').exists():rec['whole_signal_geometry']=check(out/'whole_access.tsv.gz',True)
    rec['geometry_invariants']={}
    for kind in ['pins','pdn','die']:
        a,b=out/('before.'+kind+'.tsv'),out/('after.'+kind+'.tsv')
        rec['geometry_invariants'][kind+'_byteexact_unchanged']=a.exists() and b.exists() and sha(a)==sha(b)
    cost_files=[out/(p+'.cell_cost.tsv') for p in ['before','after']]
    if all(p.exists() for p in cost_files):
        tables=[]
        for p in cost_files:
            with p.open() as f:rows=list(csv.DictReader(f,delimiter='\t'))
            table={r['instance']:r for r in rows};assert len(table)==len(rows);tables.append(table)
        a,b=tables;common=set(a)&set(b)
        rec['separate_cell_ECO_cost']={'added_instances':len(set(b)-set(a)),'removed_instances':len(set(a)-set(b)),
            'removed_CORE_SPACER_fillers':sum(a[n]['type']=='CORE_SPACER' for n in set(a)-set(b)),
            'changed_master_original_instances':sum(a[n]['master']!=b[n]['master'] for n in common),
            'moved_original_instances':sum((a[n]['x_dbu'],a[n]['y_dbu'])!=(b[n]['x_dbu'],b[n]['y_dbu']) for n in common),
            'standard_cell_master_bbox_area_before_um2':sum(float(r['area_um2']) for r in a.values() if r['type'] not in ['CORE_SPACER','BLOCK']),
            'standard_cell_master_bbox_area_after_um2':sum(float(r['area_um2']) for r in b.values() if r['type'] not in ['CORE_SPACER','BLOCK']),
            'same_original_macro_resources_and_placement':all(n in b and a[n]==b[n] for n,r in a.items() if r['type']=='BLOCK'),
            'not_block_or_system_area_saving':True,'not_pure_pin_XY_benefit':True}
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
    cases=sys.argv[2:] or ['vector'];assert set(cases)<=set(['vector','gemm','mxu','opentpu_aux'])
    variants=['C'] if os.environ.get('PINXY_ECO_ELECTRICAL_ONLY')=='1' or os.environ.get('PINXY_ECO_C_ONLY')=='1' else ['A','C']
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(safe,[(c,v,sys.argv[1]) for c in cases for v in variants]))
    sys.exit(0 if all(results) else 1)
