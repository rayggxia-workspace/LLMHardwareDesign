"""Two actual edges with the full real frame/OBS, solely a routing tool diagnosis.

The full 770-edge jobs and terminal evidence stay untouched. This subset cannot qualify any full
block, shared base or system, even if its routing and native checks pass.
"""
from pathlib import Path
import csv,datetime,hashlib,json,os,re,sys,traceback
from run_exports import ROOT,sha
from run_parent_trial import tcl
from run_escape_fixture import execute
from check_access import check

DRIVER=Path(__file__).resolve().parent


def run(revision):
    out=ROOT/'upper_tool_diagnosis'/revision;out.mkdir(parents=True,exist_ok=False)
    source=ROOT/'upper_adaptation_trial/r02/opentpu';observed=(source/'execution.json').read_bytes();q=json.loads(observed)
    planfile=source.parent/'opentpu_actual_hook_plan.json';plan=json.loads(planfile.read_text())
    assert sha(planfile)==q['source_plan_SHA256'] and plan['edge_count']==770 and q['base_qualified'] is False
    assert q['source_lower_checkpoint_SHA256']==plan['source_lower_checkpoint_SHA256']
    odb=source/'placed_adapter_NOT_SYSTEM.odb';rc=ROOT/'upper_layer_probe/r01/model/research12.setRC.tcl'
    assert odb.exists() and 'STAGE_START global_route' in (source/'native.log').read_text()
    # The original source process may still advance its receipt. The placed
    # native checkpoint was closed before that global-route stage started.
    (out/'observed_full770_execution.json').write_bytes(observed)
    paths=[odb,planfile,rc,source/'route.tcl']
    failed=source/'failed_global.odb'
    if failed.exists() and q.get('completed_utc'):
        assert sha(failed)==q['files'][failed.name]['sha256'];paths.append(failed)
    inputs={str(p):sha(p) for p in paths}
    selected=plan['physical_edges'][:2];assert [e['edge_id'] for e in selected]==[0,1]
    expected={p['helper_pin']:p for e in selected for p in e['endpoints']};assert len(expected)==4
    rec={'scope':'TWO_EDGE_FULL_FRAME_REAL_OBS_TOOL_DIAGNOSIS_NOT_FULL770_BLOCK_OR_SYSTEM',
      'source_SHA':inputs,'observed_full770_receipt_SHA256':hashlib.sha256(observed).hexdigest(),
      'observed_full_receipt_may_advance_not_geometry_mutation':True,'full_qualification':False,
      'full770_job_not_attached_signalled_cancelled_or_modified':True,'subset_edges':2,'original_mode_edges':770,
      'RC_STA':'NOT_EXECUTED_ROUTING_ONLY','native_returncodes':{},
      'scheduler_job':os.environ['SLURM_JOB_ID'],'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),
      'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    (out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n')
    common=['singularity','exec','--cleanenv','--bind',str(ROOT/'tmp')+':/tmp','--home',str(ROOT/'home'),'--pwd',str(out)]
    try:
        if str(failed) in inputs:
            # First inspect the completed failed checkpoint for recoverable real
            # guide objects. Do not blindly repeat its expensive global route.
            audit=out/'failed_checkpoint_guide_audit.tcl'
            audit.write_text('read_db '+tcl(failed)+'\nset b [ord::get_db_block];set f [open '+tcl(out/'failed_checkpoint_guides.tsv')+' w]\nputs $f "net\\tDB_guide_count_or_minus1_unsupported\\thas_native_wire"\nforeach n [$b getNets] {set count -1;if {![catch {$n getGuides} gs]} {set count [llength $gs]};puts $f [join [list [$n getName] $count [expr {[$n getWire] ne "NULL"}]] "\\t"]};close $f\nset f [open '+tcl(out/'guide_native_capabilities.txt')+' w];puts $f [info commands odb::dbGuide_*];catch {puts $f [list HAVE_ROUTES [grt::have_routes]]};close $f\nif {[catch {write_guides '+tcl(out/'recovered_from_failed.guide')+'} message]} {set f [open '+tcl(out/'guide_recovery.error.txt')+' w];puts $f $message;close $f}\n')
            rec['native_returncodes']['failed_checkpoint_guide_inventory']=execute(common,audit,out/'guide_inventory.log',threads=1)
            (out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n')
        helper=(DRIVER/'physical_trial.tcl').read_text().split('if {![stage load {',1)[0]
        lines=[helper,'read_liberty /OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib',
          'read_db '+tcl(odb),'source '+tcl(rc),'set b [ord::get_db_block];if {[llength [$b getInsts]]} {error "Unexpected FEOL instances"}',
          'proc save_obs {file} {set f [open $file w];foreach ob [[ord::get_db_block] getObstructions] {set r [$ob getBBox];puts $f [list [[$r getTechLayer] getName] [$r xMin] [$r yMin] [$r xMax] [$r yMax]]};close $f}',
          'save_obs '+tcl(out/'before.OBS.tsv'),'set keep_ports [list '+' '.join(tcl(n) for n in sorted(expected))+'];set keep_nets {}',
          'foreach name $keep_ports {set p [$b findBTerm $name];if {$p eq "NULL"} {error "Actual selected port missing"};lappend keep_nets [[$p getNet] getName]};set keep_nets [lsort -unique $keep_nets];if {[llength $keep_nets]!=2} {error "Selected ports do not form two original helper nets"}',
          'foreach p [$b getBTerms] {if {[$p getName] ni $keep_ports} {odb::dbBTerm_destroy $p}}',
          'foreach n [$b getNets] {if {[$n getName] ni $keep_nets} {odb::dbNet_destroy $n}}',
          'if {[llength [$b getBTerms]]!=4 || [llength [$b getNets]]!=2} {error "Subset terminal/net count mismatch"}',
          'save_obs '+tcl(out/'after.OBS.tsv'),
          'set f [open '+tcl(out/'actual_selected_ports.tsv')+' w];puts $f "pin\\tlayer\\tx0\\ty0\\tx1\\ty1";foreach p [$b getBTerms] {foreach bp [$p getBPins] {foreach r [$bp getBoxes] {puts $f [join [list [$p getName] [[$r getTechLayer] getName] [$r xMin] [$r yMin] [$r xMax] [$r yMax]] "\\t"]}}};close $f',
          'set_routing_layers -signal metal11-metal12 -clock metal11-metal12','write_db '+tcl(out/'subset_placed_NOT_SYSTEM.odb'),
          'if {![stage global_route_verbose {global_route -verbose -guide_file '+tcl(out/'route.guide')+' -congestion_report_file '+tcl(out/'congestion.rpt')+'}]} {catch {write_db '+tcl(out/'failed_global.odb')+'};close $stages;exit 1}',
          'if {![stage detailed_route {detailed_route -output_drc '+tcl(out/'route.drc')+' -verbose 1;write_db '+tcl(out/'routed_SUBSET_NOT_SYSTEM.odb')+'}]} {close $stages;exit 1}',
          'source '+tcl(DRIVER/'export_access.tcl'),'close $stages']
        script=out/'probe.tcl';script.write_text('\n'.join(lines)+'\n')
        env='PINXY_OUTPUT='+str(out)+',PINXY_ACCESS_ALL=1,PINXY_ACCESS_OUT='+str(out/'whole_access.tsv.gz')
        rec['native_returncodes']['subset_route']=execute(common,script,out/'native.log',env,threads=4)
        if (out/'routed_SUBSET_NOT_SYSTEM.odb').exists():
            fresh=out/'fresh.tcl';fresh.write_text('read_db '+tcl(out/'routed_SUBSET_NOT_SYSTEM.odb')+'\nset_routing_layers -signal metal11-metal12 -clock metal11-metal12\ndrt::check_drc -output_file '+tcl(out/'independent.drc')+'\n')
            rec['native_returncodes']['fresh_DRC']=execute(common,fresh,out/'independent.log',threads=1)
            if rec['native_returncodes']['fresh_DRC']==0:rec['fresh_DRC_count']=len(re.findall(r'^violation type:',(out/'independent.drc').read_text(),re.M))
        assert sha(out/'before.OBS.tsv')==sha(out/'after.OBS.tsv')
        rec['entire_original_overlay_M10_PG_OBS_constraint_set_preserved']=True
        with (out/'actual_selected_ports.tsv').open() as f:ports=list(csv.DictReader(f,delimiter='\t'))
        assert len(ports)==4 and {p['pin'] for p in ports}==set(expected)
        for p in ports:assert p['layer']=='metal10' and [int(p[k]) for k in ['x0','y0','x1','y1']]==expected[p['pin']]['base_pin_box_dbu']
        rec['actual_four_selected_M10_hook_rectangles_unchanged']=True
        if (out/'whole_access.tsv.gz').exists():rec['only_two_selected_edge_geometry']=check(out/'whole_access.tsv.gz',True)
    except Exception:rec['actual_failure']=traceback.format_exc()
    rec['all_closed_source_geometry_files_unchanged']=all(sha(Path(p))==v for p,v in inputs.items())
    rec['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    rec['files']={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in out.iterdir() if p.is_file()}
    (out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n')
    return 0 if 'actual_failure' not in rec and rec.get('native_returncodes',{}).get('subset_route')==0 and rec.get('fresh_DRC_count')==0 and rec.get('only_two_selected_edge_geometry',{}).get('pass') and rec['all_closed_source_geometry_files_unchanged'] else 1


if __name__=='__main__':sys.exit(run(sys.argv[1]))
