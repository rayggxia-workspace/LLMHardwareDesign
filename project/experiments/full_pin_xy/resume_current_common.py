"""Continue CLOSED current six-resource PG/prewire checkpoint, never a freeze.

Keep all parent M10 ports/conductors/topology/placement. Replace LL by its
matched c494 view. Conservatively aggregate M1-M3 OBS only after checking
existing parent PG against every added obstruction. No actual metal removed.
"""
from pathlib import Path
import csv,datetime,json,os,re,sys,traceback
from run_exports import ROOT,IMAGE,sha
from run_parent_trial import tcl
from run_escape_fixture import execute
from run_common_integration import CASES,SHARED_SNAPSHOT,alias_stream,verify_graph
from coarsen_parent_low_obs import coarsen
from check_access import check
DRIVER=Path(__file__).resolve().parent

def run(revision):
    source=ROOT/'common_integration/deadline-current-r01/C';q=json.loads((source/'execution.json').read_text())
    assert q.get('completed_utc') and q['all_sources_unchanged'] and q['placement_PG_returncode']==0
    assert q['native_final_stage_status']['lower_global_route']=='EXECUTED' and q['native_final_stage_status']['lower_detailed_route']=='FAIL'
    assert 'No access point for u_llaccel_aux/bit_1011' in (source/'lower_route.log').read_text()
    odb=source/'fixed_prewires_NOT_FROZEN.odb';assert sha(odb)==q['files'][odb.name]['sha256']
    views=ROOT/'llsys_wire_retention_views/r01/llaccel_aux-C';v=json.loads((views/'execution.json').read_text())
    assert v.get('completed_utc') and v['native_export_returncode']==v['fresh_model_read_returncode']==0
    assert v['matching_all_signal_model_pins']==13507 and v['SPEF_replay_matches_source'] and v['source_native_DRC']==0
    assert v['source_geometry_sha256']=='c4947012b2396735c69f395446dede19472fbc9ba1329eb4b68407dd66c5c1ad'
    inputs={str(p):sha(p) for p in [source/'execution.json',source/'lower_route.log',odb,source/'actual_shared_conductors.json',views/'execution.json']}
    out=ROOT/'common_current_resume'/revision;out.mkdir(parents=True,exist_ok=False)
    rec={'scope':'ACTUAL_CURRENT_SIX_RESOURCE_CHECKPOINT_CONTINUATION_NOT_QUALIFIED_OR_FROZEN',
         'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),'scheduler_job':os.environ['SLURM_JOB_ID'],
         'source_SHA':inputs,'full_qualification':False,'frozen':False,'cases':{},
         'old_failure':'DRT-0073 u_llaccel_aux/bit_1011; c494 leaves that pin unchanged; no assumed repair',
         'same_parent_M10_targets_placement_PDN_fixed256_and_topology':True,
         'allowed_layers':'original parent signal M2-M10, clock M4-M10; original leaf layers unchanged',
         'historical_target_mapping':'UNKNOWN_OR_PARTIAL; these are existing controlled M10 construction landings',
         'function_RC_STA':'NOT_EXECUTED_ROUTING_STAGE; inherited leaf negative STA/electrical remains'}
    save=lambda:(out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n')
    save();common=['singularity','exec','--cleanenv','--bind',str(ROOT/'tmp')+':/tmp','--home',str(ROOT/'home'),'--pwd',str(out)]
    try:
        reads=[];swaps=[];bounds=[]
        for case in CASES:
            old='p126_'+case;alias='p126resume_'+case
            lef=source/(old+'.lef');lib=source/(old+'.lib');odbsha=q['views'][case]['source_ODB_SHA']
            if case=='llaccel_aux':
                lef=views/'detailed.lef';lib=views/'timing.lib';odbsha=v['source_geometry_sha256']
                assert sha(lef)==v['files'][lef.name]['sha256'] and sha(lib)==v['files'][lib.name]['sha256']
            inputs.update({str(p):sha(p) for p in [lef,lib]})
            master=next(line.split()[1] for line in lef.open() if line.startswith('MACRO '))
            copied=out/(alias+'.original.lef');alias_stream(lef,copied,master,alias)
            dest=out/(alias+'.lef');proof=coarsen(copied,dest,requested=('metal1','metal2','metal3'))
            text,n=re.subn(r'cell\s*\(\s*"?'+re.escape(master)+r'"?\s*\)', 'cell ("'+alias+'")',lib.read_text());assert n==1
            model=out/(alias+'.lib');model.write_text(text)
            reads.extend(['read_lef '+tcl(dest),'read_liberty '+tcl(model)])
            swaps.append('set i [$b findInst '+tcl('u_'+case)+'];if {$i eq "NULL" || [[$i getMaster] getName] ne '+tcl(old)+' || [$i getOrient] ne "R0"} {error "Unexpected original instance"};set new [[ord::get_db] findMaster '+tcl(alias)+'];if {$new eq "NULL" || ![$i swapMaster $new]} {error "Cannot preserve instance through master swap"}')
            for layer,box in proof['original_OBS_envelope_DBU'].items():bounds.append(['u_'+case,layer]+box)
            rec['cases'][case]={'selected_leaf_ODB_SHA256':odbsha,'new_master':alias,'OBS_abstraction':proof,'alias_LEF_SHA256':sha(dest),'model_SHA256':sha(model)}
        shared=json.loads((source/'actual_shared_conductors.json').read_text());assert len(shared)==256
        helper=(DRIVER/'parent_trial.tcl').read_text().split('if {![stage load {',1)[0]
        lines=[helper,SHARED_SNAPSHOT,'set common_shared_pads {'+' '.join(w['construction_pad'] for w in shared)+'}',
          'read_liberty /OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib',
          'read_db '+tcl(odb),'set b [ord::get_db_block]',
          'parent_contract '+tcl(out/'original'),'common_shared_snapshot '+tcl(out/'original.shared.tsv')]
        # Check actual parent PG rectangles, including via landing geometry,
        # before expanding forbidden low-layer OBS. This cannot mask a PG clash.
        envelopes=' '.join('{'+tcl(z[0])+' '+tcl(z[1])+' '+' '.join(map(str,z[2:]))+'}' for z in bounds)
        lines+=['set added_obstruction_envelopes {'+envelopes+'}',r'''
if {![stage conservative_OBS_existing_PG_clear {
 set tested 0
 foreach n [$b getNets] {
  if {[$n getSigType] ni {POWER GROUND}} {continue}
  foreach sw [$n getSWires] {foreach r [$sw getWires] {
   set shapes {}
   if {[$r isVia]} {
    set via [$r getTechVia];if {$via eq "NULL"} {set via [$r getBlockVia]};lassign [$r getViaXY] vx vy
    foreach z [$via getBoxes] {lappend shapes [list [[$z getTechLayer] getName] [expr {$vx+[$z xMin]}] [expr {$vy+[$z yMin]}] [expr {$vx+[$z xMax]}] [expr {$vy+[$z yMax]}]]}
   } else {lappend shapes [list [[$r getTechLayer] getName] [$r xMin] [$r yMin] [$r xMax] [$r yMax]]}
   foreach z $shapes {
    lassign $z layer x0 y0 x1 y1
    if {$layer ni {metal1 metal2 metal3}} {continue}
    foreach e $added_obstruction_envelopes {
     lassign $e name ly a c d f;if {$layer ne $ly} {continue}
     set i [$b findInst $name];if {[$i getOrient] ne "R0"} {error "Unsupported PG envelope transform"};lassign [$i getLocation] ix iy
     if {$x0<$ix+$d && $ix+$a<$x1 && $y0<$iy+$f && $iy+$c<$y1} {error "Conservative abstract would overlap existing parent PG: $name $ly $z"}
     incr tested
    }
   }
  }}
 };puts "ACTUAL_PG_VERSUS_ADDED_OBS_TESTS $tested"
}]} {close $stages;exit 1}
''']+reads+['if {![stage current_master_swaps {'+';\n'.join(swaps)+'}]} {close $stages;exit 1}',
          'parent_contract '+tcl(out/'before'),'common_shared_snapshot '+tcl(out/'before.shared.tsv'),
          'write_db '+tcl(out/'current_placed_PG_fixed_NOT_FROZEN.odb'),
          'if {![stage inherited_PG_VDD {check_power_grid -net VDD -error_file '+tcl(out/'VDD.rpt')+'}]} {close $stages;exit 1}',
          'if {![stage inherited_PG_VSS {check_power_grid -net VSS -error_file '+tcl(out/'VSS.rpt')+'}]} {close $stages;exit 1}',
          'set_routing_layers -signal metal2-metal10 -clock metal4-metal10',
          'if {![stage current_global_route {global_route -use_cugr -verbose -guide_file '+tcl(out/'route.guide')+' -congestion_report_file '+tcl(out/'congestion.rpt')+'}]} {close $stages;exit 1}',
          'write_db '+tcl(out/'global.odb'),
          'if {![stage current_detailed_route {detailed_route -output_drc '+tcl(out/'route.drc')+' -verbose 1;write_db '+tcl(out/'routed_NOT_FROZEN.odb')+';write_def '+tcl(out/'routed.def')+'}]} {close $stages;exit 1}',
          'parent_contract '+tcl(out/'after'),'common_shared_snapshot '+tcl(out/'after.shared.tsv'),
          'source '+tcl(DRIVER/'export_access.tcl'),
          'stage final_VDD {check_power_grid -net VDD -error_file '+tcl(out/'final_VDD.rpt')+'}',
          'stage final_VSS {check_power_grid -net VSS -error_file '+tcl(out/'final_VSS.rpt')+'}','close $stages']
        script=out/'route.tcl';script.write_text('\n'.join(lines)+'\n')
        env='PINXY_PARENT_OUT='+str(out)+',PINXY_OUTPUT='+str(out)+',PINXY_ACCESS_ALL=1,PINXY_ACCESS_OUT='+str(out/'whole_access.tsv.gz')
        rec['native_route_returncode']=execute(common,script,out/'native.log',env,threads=16);save()
        for phase in ['before','after']:
            if not (out/(phase+'.pins.tsv')).exists():continue
            rec[phase+'_parent_preserved']={name:sha(out/('original.'+name+'.tsv'))==sha(out/(phase+'.'+name+'.tsv')) for name in ['pins','pdn','endpoints']}
            assert all(rec[phase+'_parent_preserved'].values()),'Parent ports, PG or full graph changed'
            assert sha(out/'original.shared.tsv')==sha(out/(phase+'.shared.tsv'))
            verify_graph(ROOT/'inputs/common-topology-r02',out/(phase+'.endpoints.tsv'),out/(phase+'.graph_check.json'))
        if (out/'routed_NOT_FROZEN.odb').exists():
            script=out/'fresh.tcl';script.write_text('read_db '+tcl(out/'routed_NOT_FROZEN.odb')+'\nset_routing_layers -signal metal2-metal10 -clock metal4-metal10\ndrt::check_drc -output_file '+tcl(out/'independent.drc')+'\n')
            rec['fresh_DRC_returncode']=execute(common,script,out/'fresh.log',threads=4)
            if rec['fresh_DRC_returncode']==0:rec['fresh_DRC_count']=len(re.findall(r'^violation type:',(out/'independent.drc').read_text(),re.M))
            assert len(re.findall(r'\+\s+FIXED\s+metal10\b',(out/'routed.def').read_text()))==256
            rec['all256_native_FIXED_preserved']=True
        if (out/'whole_access.tsv.gz').exists():rec['whole_signal_geometry']=check(out/'whole_access.tsv.gz',True)
    except Exception:rec['actual_failure']=traceback.format_exc()
    if (out/'stages.tsv').exists():rec['native_stage_status']={r['stage']:r['status'] for r in csv.DictReader((out/'stages.tsv').open(),delimiter='\t')}
    rec['all_closed_sources_unchanged']=all(sha(Path(p))==s for p,s in inputs.items());rec['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();rec['files']={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in out.iterdir() if p.is_file() and p.name!='execution.json'};save()
    return int(bool(rec.get('actual_failure')) or rec.get('native_route_returncode')!=0 or rec.get('fresh_DRC_count')!=0 or not rec['all_closed_sources_unchanged'])
if __name__=='__main__':sys.exit(run(sys.argv[1]))
