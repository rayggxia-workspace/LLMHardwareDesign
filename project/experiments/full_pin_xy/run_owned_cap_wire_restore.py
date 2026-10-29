"""Restore measured old-pin metal with one real M5 wire extension.

All 10261 new internal access points remain. Full-source guide control must
first reproduce the original two findings with exact physical equality.
"""
from pathlib import Path
from collections import Counter
import csv,datetime,gzip,json,os,re,subprocess,sys,traceback
from run_exports import ROOT,IMAGE,BIN,sha
from run_parent_trial import tcl
from run_escape_fixture import execute
from run_llsys_actual_tips import pin_contract
from compare_native_route_representations import routing_box_hashes
from check_access import check

DRIVER=Path(__file__).resolve().parent


def run(revision):
    source=ROOT/'llsys_owned_cap_access/r01';sp=source/'execution.json';sq=json.loads(sp.read_text())
    assert sq.get('completed_utc') and sq['fresh_DRC_count']==2 and sq['all_closed_sources_unchanged'] and sq['whole_signal_geometry']['pass']
    control=ROOT/'guide_free_leaf_DRC/r01';cp=control/'execution.json';cq=json.loads(cp.read_text())
    assert cq.get('completed_utc') and cq['profile']=='owned_cap_stage' and cq['all_closed_sources_unchanged']
    assert cq['guide_free_native_DRC_count']==cq['original_guided_fresh_native_DRC_count']==2 and cq['original_guided_completed_markers_byteexact']
    assert cq['all_source_native_WIRE_VIA_terminal_exports_byteexact'] and all(cq['all_native_physical_fingerprints_unchanged'].values())
    odb=control/'guide_metadata_removed_NOT_QUALIFIED.odb';assert sha(odb)==cq['files'][odb.name]['sha256']
    diag=ROOT/'owned_cap_spacing_diagnosis/r01';dp=diag/'execution.json';dq=json.loads(dp.read_text())
    assert dq.get('completed_utc') and dq['all_closed_sources_unchanged'] and dq['actual_failed_nets']==['bit_433'] and dq['actual_old_pin_metal_removed_DBU2']==19600
    assert len(dq['proposed_exact_wire_extensions_NOT_IMPLEMENTED'])==1
    extension=dq['proposed_exact_wire_extensions_NOT_IMPLEMENTED'][0]
    assert extension['union_equals_original_wire_plus_old_pin'] and extension['layer']=='metal5'
    rows=list(csv.DictReader((diag/'after_failed_nets.tsv').open(),delimiter='\t'))
    assert sum(r['kind']=='WIRE' for r in rows)==28
    trial=ROOT/'trials/llsys-pg-r03/llaccel_aux-C/execution.json';old=json.loads(trial.read_text());sdc=Path(old['source_sdc'])
    assert sha(sdc)==old['input_sha256'][str(sdc)]
    geometry=source/'whole_access.tsv.gz';assert sha(geometry)==sq['files'][geometry.name]['sha256']
    inputs={str(p):sha(p) for p in [sp,cp,odb,dp,diag/'after_failed_nets.tsv',geometry,trial,sdc]}
    out=ROOT/'owned_cap_wire_restore'/revision;out.mkdir(parents=True,exist_ok=False)
    rec={'scope':'ACTUAL_ONE_M5_WIRE_RESTORE_10261_INTERNAL_POINTS_RETAINED_NOT_FULL_QUALIFICATION',
         'full_qualification':False,'source_SHA':inputs,'scheduler_job':os.environ['SLURM_JOB_ID'],
         'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),'native_returncodes':{},
         'source_native_DRC_count':2,'new_cells_or_sizes':0,'new_or_moved_vias_requested':0,
         'pin_changes_requested':0,'original_internal_access_changes_retained':10261,
         'actual_old_pin_metal_to_restore_DBU2':19600,'requested_extension':extension,
         'parent_AP_complete_GDS_RTL':'NOT_EXECUTED','historical_parent_target_layers':'PARTIAL_OR_UNKNOWN_UNCHANGED',
         'metadata_policy':'Guide-free copy is admitted only after full-source actual physical export/native findings equality; original with-guides result retained'}
    save=lambda:(out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n');save()
    common=['singularity','exec','--cleanenv','--bind',str(ROOT/'tmp')+':/tmp',
            '--bind','/public/home/yuzelu/project-circuit:/public/home/yuzelu/project-circuit:ro',
            '--bind','/public/home/yuzelu/PingyangHuang/issue-55:/public/home/yuzelu/PingyangHuang/issue-55:ro',
            '--home',str(ROOT/'home'),'--pwd',str(out)]
    try:
        rec['actual_OpenROAD_binary_SHA256']=subprocess.check_output(common+[IMAGE,'sha256sum',BIN]).decode().split()[0]
        assert rec['actual_OpenROAD_binary_SHA256']==sq['actual_OpenROAD_binary_SHA256']==cq['actual_OpenROAD_binary_SHA256']
        helper=(DRIVER/'physical_trial.tcl').read_text().split('if {![stage load {',1)[0]
        contracts=(DRIVER/'output_chain_placement.tcl').read_text().split('read_db $::env(PINXY_CHAIN_SOURCE)',1)[0]
        body='''set b [ord::get_db_block];set n [$b findNet bit_433]
if {$n eq "NULL" || [llength [$n getBTerms]]!=1 || [llength [$n getITerms]]!=1} {error "Actual failed-net endpoint contract changed"}
set it [lindex [$n getITerms] 0]
if {[[$it getInst] getName] ne "place86173" || [[$it getMTerm] getName] ne "Z"} {error "Original peer changed"}
set itr [odb::dbWirePathItr];set path [odb::dbWirePath];set ps [odb::dbWirePathShape]
set records {};set changed 0;set nw 0;$itr begin [$n getWire]
while {[$itr getNextPath $path]} {while {[$itr getNextShape $ps]} {
 set s [odb::dbWirePathShape_shape_get $ps]
 if {[$s isVia]} {
  set kind TECH;set via [$s getTechVia];if {$via eq "NULL"} {set kind BLOCK;set via [$s getVia]}
  set bottom {};set level 1000
  foreach box [$via getBoxes] {set ly [$box getTechLayer];set lev [$ly getRoutingLevel];if {$lev>0 && $lev<$level} {set level $lev;set bottom $ly}}
  if {$bottom eq ""} {error "No real via bottom"};lassign [$s getViaXY] x y
  lappend records [list VIA $bottom $kind $via $x $y]
 } else {
  incr nw;set ly [$s getTechLayer];set layer [$ly getName];set z [list [$s xMin] [$s yMin] [$s xMax] [$s yMax]]
  if {$layer eq "metal5" && $z eq OLDRECT} {set z NEWRECT;incr changed}
  lassign $z x0 y0 x1 y1;set width [$ly getWidth];set dx [expr {$x1-$x0}];set dy [expr {$y1-$y0}]
  if {min($dx,$dy)!=$width || $dx==$dy || $width%2} {error "Non-default/square source wire requires distinct implementation"}
  if {$dx>$dy} {set xy [list [expr {$x0+$width/2}] [expr {($y0+$y1)/2}] [expr {$x1-$width/2}] [expr {($y0+$y1)/2}]]} else {set xy [list [expr {($x0+$x1)/2}] [expr {$y0+$width/2}] [expr {($x0+$x1)/2}] [expr {$y1-$width/2}]]}
  lappend records [list WIRE $ly {*}$xy]
 }
}}
if {$nw!=28 || $changed!=1} {error "Exact one-wire preflight failed"}
odb::dbWire_destroy [$n getWire];set wire [odb::dbWire_create $n];set enc [odb::dbWireEncoder];$enc begin $wire
foreach rec $records {
 set kind [lindex $rec 0];$enc newPath [lindex $rec 1] ROUTED
 if {$kind eq "WIRE"} {lassign [lrange $rec 2 end] x y xx yy;$enc addPoint $x $y;$enc addPoint $xx $yy} else {
  lassign [lrange $rec 2 end] kind via x y;$enc addPoint $x $y
  if {$kind eq "TECH"} {$enc addTechVia $via} else {$enc addVia $via}
 }
};$enc end
puts EXACT_ONE_REAL_M5_WIRE_EXTENDED_NO_PIN_OR_VIA_MOVED
'''.replace('OLDRECT',tcl(' '.join(map(str,extension['actual_old_WIRE_box_DBU'])))).replace('NEWRECT',tcl(' '.join(map(str,extension['proposed_new_WIRE_box_DBU']))))
        (out/'extend_one_actual_wire.tcl').write_text(body)
        lines=[helper,contracts]+['read_liberty '+tcl(p) for p in old['libs']]
        lines+=['read_db '+tcl(odb),'read_sdc '+tcl(sdc),'source /OpenROAD-flow-scripts/flow/platforms/nangate45/setRC.tcl',
          'set_routing_layers -signal metal2-metal8 -clock metal4-metal8','fingerprint '+tcl(out/'before'),'set old_obs [obs_snapshot]',
          'if {![stage one_actual_wire_restore {source '+tcl(out/'extend_one_actual_wire.tcl')+'}]} {catch {write_db '+tcl(out/'failed_edit.odb')+'};close $stages;exit 1}',
          'if {[obs_snapshot] ne $old_obs} {error "Original OBS changed"}','fingerprint '+tcl(out/'after'),
          'write_db '+tcl(out/'routed.odb'),'write_def '+tcl(out/'routed.def'),'write_verilog '+tcl(out/'mapped.v'),
          'stage VDD {check_power_grid -net VDD -error_file '+tcl(out/'VDD.rpt')+'}',
          'stage VSS {check_power_grid -net VSS -error_file '+tcl(out/'VSS.rpt')+'}',
          'stage whole_signal_geometry {source '+tcl(DRIVER/'export_access.tcl')+'}',
          'stage rcx {define_process_corner -ext_model_index 0 X;set_extraction_rules_file /OpenROAD-flow-scripts/flow/platforms/nangate45/rcx_patterns.rules;extract_parasitics;write_spef '+tcl(out/'extracted.spef')+';read_spef '+tcl(out/'extracted.spef')+'}',
          'stage sta {report_worst_slack -max -digits 6 > '+tcl(out/'setup.txt')+';report_worst_slack -min -digits 6 > '+tcl(out/'hold.txt')+';report_check_types -violators -max_delay -min_delay -max_slew -max_capacitance -max_fanout -recovery -removal -max_count 1000000 -digits 6 > '+tcl(out/'checks.txt')+';check_setup -verbose > '+tcl(out/'constraint_coverage.txt')+';report_parasitic_annotation -report_unannotated > '+tcl(out/'parasitic_coverage.txt')+'}','close $stages']
        script=out/'edit_and_analyze.tcl';script.write_text('\n'.join(lines)+'\n')
        rec['native_returncodes']['actual_edit_and_analysis']=execute(common,script,out/'native.log','PINXY_OUTPUT='+str(out)+',PINXY_ACCESS_ALL=1,PINXY_ACCESS_OUT='+str(out/'whole_access.tsv.gz'),threads=4);save()
        assert rec['native_returncodes']['actual_edit_and_analysis']==0
        rec['complete_pin_contract']=pin_contract(out,{},13507)
        rec['all_10261_current_internal_points_retained']=True
        rec['all_cells_signal_connections_PG_die_unchanged']={k:sha(out/('before.'+k+'.tsv'))==sha(out/('after.'+k+'.tsv')) for k in ['cells','pdn','die']}
        assert all(rec['all_cells_signal_connections_PG_die_unchanged'].values())
        script=out/'fresh.tcl';script.write_text('read_db '+tcl(out/'routed.odb')+'\nset_routing_layers -signal metal2-metal8 -clock metal4-metal8\ndrt::check_drc -output_file '+tcl(out/'independent.drc')+'\n')
        rec['native_returncodes']['fresh_DRC']=execute(common,script,out/'independent.log',threads=1)
        if rec['native_returncodes']['fresh_DRC']==0:rec['fresh_DRC_count']=len(re.findall(r'^violation type:',(out/'independent.drc').read_text(),re.M))
        rec['whole_signal_geometry']=check(out/'whole_access.tsv.gz',True)
        a,_=routing_box_hashes(geometry,725253);b,_=routing_box_hashes(out/'whole_access.tsv.gz',725253)
        assert set(a)==set(b) and {n for n in a if a[n]!=b[n]}=={'bit_433'}
        rec['all_other_725252_multiterminal_WIRE_VIA_multisets_exact']=True
        with gzip.open(str(out/'whole_access.tsv.gz'),'rt') as f:
            new_rows=[r for r in csv.DictReader(f,delimiter='\t') if r['net']=='bit_433']
        key=lambda r:tuple(r[k] for k in ['kind','layer','x0','y0','x1','y1'])
        mat=lambda rr:Counter(key(r) for r in rr if r['kind'] in ['WIRE','VIA'])
        removed=mat(rows)-mat(new_rows);added=mat(new_rows)-mat(rows)
        want=lambda b:('WIRE','metal5')+tuple(map(str,b))
        assert removed==Counter([want(extension['actual_old_WIRE_box_DBU'])]) and added==Counter([want(extension['proposed_new_WIRE_box_DBU'])])
        rec['exactly_one_M5_WIRE_extended_all_vias_exact']=True
        for kind in ['setup','hold']:
            p=out/(kind+'.txt')
            if p.exists():rec[kind+'_ns']=float(re.search(r'worst slack (?:max|min)\s+([-\d.]+)',p.read_text())[1])
        if (out/'checks.txt').exists():rec['literal_VIOLATED_markers_not_complete_failure_count']=(out/'checks.txt').read_text().count('(VIOLATED)')
    except Exception:rec['actual_failure']=traceback.format_exc()
    if (out/'stages.tsv').exists():
        with (out/'stages.tsv').open() as f:rec['native_stage_status']={r['stage']:r['status'] for r in csv.DictReader(f,delimiter='\t')}
    rec['all_closed_sources_unchanged']=all(sha(Path(p))==s for p,s in inputs.items())
    rec['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    rec['files']={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in out.iterdir() if p.is_file() and p.name!='execution.json'};save()
    passed=not rec.get('actual_failure') and rec.get('fresh_DRC_count')==0 and rec.get('whole_signal_geometry',{}).get('pass') and rec.get('setup_ns',-1)>=0 and rec.get('hold_ns',-1)>=0 and rec.get('literal_VIOLATED_markers_not_complete_failure_count')==0
    passed=passed and all(rec.get('native_stage_status',{}).get(k)=='EXECUTED' for k in ['one_actual_wire_restore','VDD','VSS','whole_signal_geometry','rcx','sta'])
    return 0 if passed and rec['all_closed_sources_unchanged'] else 1


if __name__=='__main__':sys.exit(run(sys.argv[1]))
