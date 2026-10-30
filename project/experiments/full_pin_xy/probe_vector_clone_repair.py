"""Actual native combinational gate-cloning ECO probe under original VECTOR SDC.

Original placement-based repair explicitly disabled gate cloning. This new
probe enables it on the current routed source. It exports a real checkpoint,
costs and graphs. It does NOT claim legality, RC/STA closure or equivalence of
new clones. Those must be checked separately before promoting the checkpoint.
"""
from pathlib import Path
from collections import Counter
import csv,datetime,json,os,subprocess,sys,traceback
from run_exports import ROOT,IMAGE,sha
from run_parent_trial import tcl
from run_escape_fixture import execute
from run_vector_resume import COST_PROC
from verify_mapped_eco import export_graph,load
from cell_semantics import contract,groups

DRIVER=Path(__file__).resolve().parent


def run(revision):
    assert revision in ['r01','r02','r03']
    source=ROOT/'vector_resume/r01';rp=source/'execution.json';prior=json.loads(rp.read_text())
    assert prior.get('completed_utc') and prior['native_returncodes']['route']==0 and prior['fresh_DRC_count']==0
    assert prior['whole_signal_geometry']['pass'] and prior['all_sources_unchanged'] and all(prior['source_pin_PG_die_unchanged'].values())
    odb=source/'routed.odb';spef=source/'extracted.spef'
    for p in [odb,spef]:assert sha(p)==prior['files'][p.name]['sha256']
    oldpath=ROOT/'trials/access-r03/vector-C/execution.json';old=json.loads(oldpath.read_text());sdc=Path(old['source_sdc'])
    assert sha(sdc)==old['input_sha256'][str(sdc)]
    replay=ROOT/'actual_path_audit/r01/vector/execution.json';proof=json.loads(replay.read_text())
    assert proof['native_returncode']==0 and proof['all_sources_unchanged'] and all(proof['source_worst_slacks_exactly_replayed'].values())
    assert proof['source_SHA'][str(odb)]==sha(odb) and proof['source_SHA'][str(spef)]==sha(spef)
    out=ROOT/'vector_clone_probe'/revision;out.mkdir(parents=True,exist_ok=False)
    inputs={str(p):sha(p) for p in [rp,odb,spef,oldpath,sdc,replay]}
    guide=source/'route.guide'
    if revision=='r02':
        assert sha(guide)==prior['files'][guide.name]['sha256'];inputs[str(guide)]=sha(guide)
    rec={'scope':'ACTUAL_GATE_CLONING_HEURISTIC_ECO_PROBE_NOT_LEGAL_ROUTED_EQUIVALENT_OR_TIMING_CLOSED',
      'source_SHA':inputs,'source_actual_extracted_setup_ns':prior['setup_ns'],'source_actual_extracted_hold_ns':prior['hold_ns'],
      'source_SPEF_replay_reused_without_repetition':str(replay),
      'repair_model':'Placement heuristic only, after remove_fillers; no SPEF/GRT state mixed into this repair process',
      'change':'Enable native combinational gate cloning previously explicitly disabled; original clocks, SDC, pipeline, cache, lane resources and block pins retained',
      'new_clone_full_digital_relation':'NOT_EXECUTED','final_legalization_route_RC_STA':'NOT_EXECUTED','full_qualification':False,
      'native_returncodes':{},'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),'scheduler_job':os.environ['SLURM_JOB_ID'],
      'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    if revision=='r02':
        rec['repair_model']='Placement heuristic after remove_fillers with original native guide/GRT incremental context; no extracted SPEF loaded. Guide reconstruction may be incomplete and is not new real extracted STA.'
        rec['new_single_context_change']='Initialize original native guide/GRT incremental context before the same placement heuristic and setup sequence. Candidate address mapping suggested GlobalRouter/SizeUp calls but entrypoint alignment remains unresolved; this is a controlled context capability trial, not a diagnosed root-cause fix.'
    if revision=='r03':
        api=ROOT/'vector_clone_crash/r02';ap=api/'execution.json';a=json.loads(ap.read_text())
        body=api/'repair_timing.body.tcl';assert sha(body)==a['files'][body.name]['sha256']
        assert 'if { [design_is_routed] }' in body.read_text() and 'est::set_parasitics_src "detailed_routing"' in body.read_text()
        inputs.update({str(p):sha(p) for p in [ap,body]})
        rec['repair_model']='Placement heuristic only after removing original signal/clock dbWire objects from the in-memory copy and remove_fillers; no SPEF or original guides loaded. All original file inputs immutable. Full detailed reroute/RC/STA required separately.'
        rec['new_single_context_change']='Installed repair_timing forces detailed_routing parasitics when design_is_routed is true. Remove only SIGNAL/CLOCK dbWire geometry in memory, assert the same native routed predicate is false, then run the same placement repair. This tests an observed script mechanism, not a proven crash root cause or timing fix.'
    def save():(out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n')
    save()
    common=['singularity','exec','--cleanenv','--bind',str(ROOT/'tmp')+':/tmp',
      '--bind','/public/home/yuzelu/project-circuit:/public/home/yuzelu/project-circuit:ro',
      '--bind','/public/home/yuzelu/PingyangHuang/issue-55:/public/home/yuzelu/PingyangHuang/issue-55:ro',
      '--home',str(ROOT/'home'),'--pwd',str(out)]
    for p in old['libs']:
        if Path(p).is_file():common+=['--bind',p+':'+p+':ro']
    try:
        helper=(DRIVER/'physical_trial.tcl').read_text().split('if {![stage load {',1)[0]
        lines=[helper,COST_PROC]+['read_liberty '+tcl(p) for p in old['libs']]
        lines+=['read_db '+tcl(odb),'read_sdc '+tcl(sdc),
          'source /OpenROAD-flow-scripts/flow/platforms/nangate45/setRC.tcl',
          'set_routing_layers -signal metal2-metal10 -clock metal4-metal10',
          'fingerprint '+tcl(out/'before'),'cell_cost '+tcl(out/'before.cell_cost.tsv'),
          'if {![stage remove_only_fillers_before_estimation {remove_fillers}]} {close $stages;exit 1}',
          'if {![stage placement_estimator {estimate_parasitics -placement}]} {close $stages;exit 1}',
          'report_worst_slack -max -digits 6 > '+tcl(out/'HEURISTIC_before.setup.txt'),
          'report_worst_slack -min -digits 6 > '+tcl(out/'HEURISTIC_before.hold.txt'),
          'if {![stage setup_with_gate_cloning {repair_timing -setup -skip_pin_swap -skip_buffer_removal -skip_buffer_to_inverters -max_passes 20 -max_iterations 10000 -max_utilization 85 -verbose;write_db '+tcl(out/'gate_repaired_NOT_LEGALIZED_OR_ROUTED.odb')+'}]} {close $stages;exit 1}',
          'fingerprint '+tcl(out/'after'),'cell_cost '+tcl(out/'after.cell_cost.tsv'),
          'report_worst_slack -max -digits 6 > '+tcl(out/'HEURISTIC_after.setup.txt'),
          'report_worst_slack -min -digits 6 > '+tcl(out/'HEURISTIC_after.hold.txt'),
          'write_verilog '+tcl(out/'gate_repaired_NOT_QUALIFIED.v'),'close $stages']
        if revision=='r02':
            index=next(i for i,line in enumerate(lines) if line.startswith('if {![stage placement_estimator '))
            lines[index:index]=['if {![stage initialize_original_GRT_context {read_guides '+tcl(guide)+';global_route -start_incremental;set f [open '+tcl(out/'actual_GRT_context.txt')+' w];puts $f [list HAVE_ROUTES [grt::have_routes]];close $f;if {![grt::have_routes]} {error "Original guides did not establish a native GRT route context; stop before repeating setup crash"}}]} {close $stages;exit 1}']
        if revision=='r03':
            index=next(i for i,line in enumerate(lines) if line.startswith('if {![stage remove_only_fillers_before_estimation '))
            code='''set current [info body repair_timing];set f [open '''+tcl(out/'actual_repair_timing.body.tcl')+''' w];puts -nonewline $f $current;close $f
set f [open '''+tcl(out/'actual_context_transition.txt')+''' w]
puts $f [exec sha256sum [info nameofexecutable]]
set original [open '''+tcl(body)+''' r];set recorded [read $original];close $original
if {$current ne $recorded} {error "Installed repair_timing differs from source-bound capability body"}
set predicate [namespace qualifiers [namespace origin repair_timing]]::design_is_routed
if {![llength [info commands $predicate]]} {set predicate design_is_routed}
if {![llength [info commands $predicate]]} {error "Cannot resolve native routed predicate; stop before repair"}
puts $f [list NATIVE_PREDICATE $predicate BEFORE [$predicate]]
set removed 0;set b [ord::get_db_block]
foreach n [$b getNets] {
 if {[$n getSigType] ni {SIGNAL CLOCK}} {continue}
 set w [$n getWire];if {$w ne "NULL"} {odb::dbWire_destroy $w;incr removed}
}
puts $f [list REMOVED_ONLY_SIGNAL_CLOCK_DBWIRES $removed AFTER [$predicate]];close $f
if {$removed<=0 || [$predicate]} {error "Native design still routed; refuse the same unintended detailed estimator path"}
'''
            lines[index:index]=['if {![stage strip_only_signal_clock_routes_in_memory_before_placement {'+code+'}]} {close $stages;exit 1}']
        script=out/'probe.tcl';script.write_text('\n'.join(lines)+'\n')
        rec['native_returncodes']['clone_heuristic_probe']=execute(common,script,out/'native.log','PINXY_OUTPUT='+str(out),threads=4);save()
        rec['pin_PG_die_unchanged']={k:(out/('after.'+k+'.tsv')).exists() and sha(out/('before.'+k+'.tsv'))==sha(out/('after.'+k+'.tsv')) for k in ['pins','pdn','die']}
        if (out/'after.cell_cost.tsv').exists():
            tables=[]
            for prefix in ['before','after']:
                with (out/(prefix+'.cell_cost.tsv')).open() as f:tables.append({r['instance']:r for r in csv.DictReader(f,delimiter='\t')})
            a,b=tables;shared=set(a)&set(b);added=[b[n] for n in set(b)-set(a) if b[n]['type']!='CORE_SPACER']
            rec['separate_ECO_cost']={'added_functional_instances':len(added),'added_masters':dict(Counter(r['master'] for r in added)),
              'removed_original_functional_instances':sum(a[n]['type']!='CORE_SPACER' for n in set(a)-set(b)),
              'resized_original_instances':sum(a[n]['master']!=b[n]['master'] for n in shared),
              'moved_original_instances':sum((a[n]['x_dbu'],a[n]['y_dbu'])!=(b[n]['x_dbu'],b[n]['y_dbu']) for n in shared),
              'standard_cell_master_area_delta_um2':sum(float(r['area_um2']) for r in b.values() if r['type'] not in ['BLOCK','CORE_SPACER'])-sum(float(r['area_um2']) for r in a.values() if r['type'] not in ['BLOCK','CORE_SPACER']),
              'not_block_area_or_pure_XY_benefit':True}
        checkpoint=out/'gate_repaired_NOT_LEGALIZED_OR_ROUTED.odb'
        if checkpoint.exists():
            rec['native_returncodes']['source_graph']=export_graph(common,odb,out,'source')
            rec['native_returncodes']['repaired_graph']=export_graph(common,checkpoint,out,'repaired')
            assert rec['native_returncodes']['source_graph']==rec['native_returncodes']['repaired_graph']==0
            a,at,ap=load(out/'source.tsv.gz');b,bt,bp=load(out/'repaired.tsv.gz');assert set(a)<=set(b) and ap==bp
            raw=subprocess.check_output(common+[IMAGE,'cat','/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib'])
            bodies=dict(groups(raw.decode(),'cell'))
            physical_only={n for table in [a,b] for n,m in table.items() if m[1]=='CORE_WELLTAP'}
            assert not physical_only.intersection(k[0] for k in at) and not physical_only.intersection(k[0] for k in bt)
            used={m[0] for table in [a,b] for n,m in table.items() if n not in physical_only};assert used<=set(bodies)
            models={n:contract('cell ('+n+') {'+bodies[n]+'}',n) for n in used}
            state_a={n:models[m[0]] for n,m in a.items() if n not in physical_only and models[m[0]]['state']}
            state_b={n:models[m[0]] for n,m in b.items() if n not in physical_only and models[m[0]]['state']}
            assert state_a==state_b
            rec['all_original_stateful_instances_and_Liberty_logic_state_contracts_preserved']=True
            rec['stateful_instances']=len(state_a)
            rec['all_original_top_port_net_names_and_directions_unchanged']=True
            rec['actual_typical_Liberty_SHA256']=__import__('hashlib').sha256(raw).hexdigest()
        rec['all_closed_sources_unchanged']=all(sha(Path(p))==v for p,v in inputs.items())
    except Exception:rec['actual_failure']=traceback.format_exc()
    rec['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    rec['files']={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in out.iterdir() if p.is_file() and p.name!='execution.json'};save()
    return 0 if 'actual_failure' not in rec and rec['native_returncodes'].get('clone_heuristic_probe')==0 and rec.get('all_closed_sources_unchanged') and all(rec.get('pin_PG_die_unchanged',{}).values()) and rec.get('all_original_stateful_instances_and_Liberty_logic_state_contracts_preserved') else 1


if __name__=='__main__':sys.exit(run(sys.argv[1]))
