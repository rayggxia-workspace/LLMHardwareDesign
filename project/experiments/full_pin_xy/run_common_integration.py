"""Actual six-resource lower-layer integration trial, explicitly NOT a qualified base.

Reuse the compiled full bit graph and finite 256-conductor topology. Matching
real extracted leaf views are required, including the explicitly failed four-
DRC LL SYSTEM diagnostic source. No routing-only capacitance stubs are used.
Construction access ports remain until a separately verified mode lowering;
this trial cannot be frozen or called a complete functional implementation.
"""
from pathlib import Path
import csv,datetime,json,math,os,re,subprocess,sys,traceback
from run_exports import ROOT,sha
from run_parent_trial import tcl
from run_escape_fixture import execute
from lef_view_contract import verify
from verify_common_native import verify as verify_graph
from check_access import check

DRIVER=Path(__file__).resolve().parent
CASES=['act','mxu','opentpu_aux','gemm','vector','llaccel_aux']
SHARED_SNAPSHOT='''proc common_shared_snapshot {file} {
 set f [open $file w];puts $f "pad\\tnet\\tlayer\\tx0\\ty0\\tx1\\ty1"
 set itr [odb::dbWirePathItr];set path [odb::dbWirePath];set ps [odb::dbWirePathShape]
 foreach pad $::common_shared_pads {
  set bt [[ord::get_db_block] findBTerm $pad];set n [$bt getNet];set w [$n getWire]
  if {$w eq "NULL"} {error "Shared physical conductor missing: $pad"}
  $itr begin $w
  while {[$itr getNextPath $path]} {while {[$itr getNextShape $ps]} {
   set s [odb::dbWirePathShape_shape_get $ps];if {[$s isVia]} {error "Unexpected via in fixed M10-only resource"}
   puts $f [join [list $pad [$n getName] [[$s getTechLayer] getName] [$s xMin] [$s yMin] [$s xMax] [$s yMax]] "\\t"]
  }}
 };close $f
}'''


def source_view(case,scheme):
    eco=case in ['gemm','mxu'] or (case=='opentpu_aux' and scheme=='C')
    if eco:
        rev='r04' if scheme=='Aopt' else 'r03' if case=='opentpu_aux' else 'r02'
        folder=ROOT/'eco_views'/rev/(case+'-'+scheme);p=folder/'execution.json';q=json.loads(p.read_text())
        assert q.get('completed_utc') and q['native_export_returncode']==0 and q['fresh_model_read_returncode']==0
        assert q['SPEF_replay_matches_source'] and q['all_original_signal_and_PG_pins_and_size_exactly_preserved']
        odb=folder/'clean.odb';assert sha(odb)==q['source_geometry_sha256']
        model=folder/'timing.lib';assert sha(model)==q['files']['timing.lib']['sha256']
        native=q['source_native_DRC'];physical=folder;model_receipt=p
    else:
        physical_revision='full-controls-r04' if scheme=='Aopt' else {'act':'act-access-r03','vector':'access-r03','llaccel_aux':'llsys-pg-r03'}[case]
        physical=ROOT/'finalized'/physical_revision/(case+'-'+scheme);p=physical/'execution.json';q=json.loads(p.read_text())
        assert q['whole_access']['pass'] and q['clean_byte_identical_to_pre_RCX_source']
        native=q['independent_DRC_count'];odb=physical/'clean.odb';assert sha(odb)==q['clean_odb_sha256']
        model_revision=('r03' if case=='act' else 'r05') if scheme=='Aopt' else 'r04' if case=='act' else 'r07'
        models=ROOT/'leaf_timing_models'/model_revision/(case+'-'+scheme);model_receipt=models/'execution.json';m=json.loads(model_receipt.read_text())
        assert m.get('finished_utc') and m['exact_all_signal_pin_direction_match'] and m['source_odb_and_SPEF_unchanged']
        assert m['SPEF_replay_matches_recorded_trial_1e_minus5_ns']
        assert m['source_clean_receipt_sha256']==sha(p) and m['clean_odb_sha256']==sha(odb)
        model=models/'timing.lib';assert sha(model)==m['generated_library_sha256']
        if native:
            assert scheme=='C' and case=='llaccel_aux' and native==4
            assert m['status']=='UNQUALIFIED_FAILED_DRC_SOURCE_EXTRACTED_MODEL_EXPORTED'
    assert native==0 or (scheme=='C' and case=='llaccel_aux' and native==4)
    return {'directory':physical,'receipt':p,'ODB':odb,'model':model,'model_receipt':model_receipt,
            'native_DRC':native,'complete_rules':'NOT_QUALIFIED','RTL_equivalence':'NOT_EXECUTED'}


def alias_stream(source,dest,master,alias):
    count=[0,0]
    with source.open() as f,dest.open('x') as g:
        for line in f:
            if re.fullmatch(r'MACRO\s+'+re.escape(master)+r'\s*',line):line='MACRO '+alias+'\n';count[0]+=1
            elif re.fullmatch(r'END\s+'+re.escape(master)+r'\s*',line):line='END '+alias+'\n';count[1]+=1
            g.write(line)
    assert count==[1,1],count


def rows(path):
    with path.open() as f:return list(csv.DictReader(f,delimiter='\t'))


def screen_pads(out,preparation,inputs):
    plan=json.loads((preparation/'preparation_contract.json').read_text())
    pads=json.loads((inputs/'access_pads.json').read_text());components=json.loads((inputs/'components.json').read_text())
    native=rows(out/'native_pin_boxes.tsv');byterm={}
    for q in native:byterm.setdefault((q['instance'],q['pin']),[]).append(q)
    obstacles=[]
    for q in rows(out/'actual_M10_obstacles.tsv'):
        obstacles.append([int(q[k])/2000 for k in ['x0','y0','x1','y1']])
    width,height=plan['frame_um'][2:];macro=plan['instances']
    inside=lambda b:any(b[0]<m['x_um']+m['width_um'] and b[2]>m['x_um'] and b[1]<m['y_um']+m['height_um'] and b[3]>m['y_um'] for m in macro)
    clear=lambda b,qs:not any(b[0]-1.5<q[2] and b[2]+1.5>q[0] and b[1]-1.5<q[3] and b[3]+1.5>q[1] for q in qs)
    offsets=sorted((abs(i)+abs(j),i,j) for i in range(-40,41) for j in range(-40,41))
    with (preparation/'shared_prewire_geometry.csv').open() as f:prewires=list(csv.DictReader(f))
    actual=[];commands=[];placed=[]
    for r in prewires:
        px,py=json.loads(r['pad_A_xy_um']),json.loads(r['pad_B_xy_um']);chosen=None
        for _,i,j in offsets:
            x,y=px[0]+i*3.2,px[1]+j*3.2;b=[x-.4,y-.4,x+.4,y+32.4]
            if min(b)<10 or b[2]>width-10 or b[3]>height-10 or inside(b) or not clear(b,obstacles+placed):continue
            chosen=x,y,b;break
        assert chosen,(r['resource'],'No actual PG-screened 32um fixed conductor in common corridor')
        x,y,b=chosen;placed.append(b);pad=pads['SHARED:'+r['resource']]
        commands.append('place_pin -pin_name '+tcl(pad)+' -layer metal10 -location {'+str(x)+' '+str(y)+'} -pin_size {.8 .8}')
        commands.append('set bt [$b findBTerm '+tcl(pad)+'];set net [$bt getNet];if {[$net getWire] ne "NULL"} {error "Unexpected existing shared wire"};set w [odb::dbWire_create $net];set enc [odb::dbWireEncoder];$enc begin $w;$enc newPath $m10 FIXED;$enc addPoint '+str(round(x*2000))+' '+str(round(y*2000))+';$enc addPoint '+str(round(x*2000))+' '+str(round((y+32)*2000))+';$enc end')
        commands.append('set bp [odb::dbBPin_create $bt];$bp setPlacementStatus FIRM;odb::dbBox_create $bp $m10 '+ ' '.join(str(round(v*2000)) for v in [x-.4,y+31.6,x+.4,y+32.4]))
        actual.append({'resource':r['resource'],'component':'SHARED:'+r['resource'],'construction_pad':pad,
          'x0_um':b[0],'y0_um':b[1],'x1_um':b[2],'y1_um':b[3],'length_um':32.,'width_um':.8,
          'proposed_A_xy_um':px,'actual_A_xy_um':[x,y],'actual_B_xy_um':[x,y+32.]})
    # True system I/O stays separate from construction-only adaptation pads.
    topnames=sorted({c.split(':')[0]+'__'+q['pin'] for c,ts in components.items() for q in ts if q['kind']=='TOP_IO'})
    boundary=[];pitch=1.12;inset=16.8
    for y in [inset,height-inset]:
        for i in range(int((width-2*inset)/pitch)):boundary.append((inset+i*pitch,y,'metal6'))
    for x in [inset,width-inset]:
        for i in range(int((height-2*inset)/pitch)):boundary.append((x,inset+i*pitch,'metal5'))
    assert len(boundary)>=len(topnames)
    topxy={}
    top_component={c.split(':')[0]+'__'+q['pin']:ts for c,ts in components.items() for q in ts if q['kind']=='TOP_IO'}
    centers={m['case']:(m['x_um']+m['width_um']/2,m['y_um']+m['height_um']/2) for m in macro}
    for pin in topnames:
        affinities=[centers[q['case']] for q in top_component[pin] if q['kind']=='ITERM']
        cx=sum(p[0] for p in affinities)/len(affinities) if affinities else width/2
        cy=sum(p[1] for p in affinities)/len(affinities) if affinities else inset
        index=min(range(len(boundary)),key=lambda i:abs(boundary[i][0]-cx)+abs(boundary[i][1]-cy))
        x,y,layer=boundary.pop(index)
        commands.append('place_pin -pin_name '+tcl(pin)+' -layer '+layer+' -location {'+str(x)+' '+str(y)+'} -pin_size {.14 .14}')
        topxy[pin]=(x,y)
    pad_records=[]
    for component,pad in sorted(pads.items()):
        if component.startswith('SHARED:'):continue
        ts=components[component];points=[]
        for q in ts:
            if q['kind']=='TOP_IO':points.append(topxy[component.split(':')[0]+'__'+q['pin']])
            else:
                inst='u_'+q['case'] if q['kind']=='ITERM' else q['instance'];pin=q['pin'] if q['kind']=='ITERM' else 'Z'
                boxes=byterm[inst,pin];points.append(((min(int(b['x0']) for b in boxes)+max(int(b['x1']) for b in boxes))/4000,(min(int(b['y0']) for b in boxes)+max(int(b['y1']) for b in boxes))/4000))
        assert points
        cx=sum(p[0] for p in points)/len(points);cy=sum(p[1] for p in points)/len(points)
        sx=.095+round((cx-.095)/3.2)*3.2;sy=.07+round((cy-.07)/3.2)*3.2;chosen=None
        for _,i,j in offsets:
            x,y=sx+i*3.2,sy+j*3.2;b=[x-.4,y-.4,x+.4,y+.4]
            if min(b)<10 or b[2]>width-10 or b[3]>height-10 or not clear(b,obstacles+placed):continue
            chosen=x,y,b;break
        assert chosen,(component,'No actual upper-metal screened adaptation landing')
        x,y,b=chosen;placed.append(b)
        commands.append('place_pin -pin_name '+tcl(pad)+' -layer metal10 -location {'+str(x)+' '+str(y)+'} -pin_size {.8 .8}')
        pad_records.append({'component':component,'pad':pad,'new_parent_layer':'metal10','actual_xy_um':[x,y],
          'source_real_terminal_centroid_um':[cx,cy],'original_leaf_layers_unchanged':True})
    (out/'actual_shared_conductors.json').write_text(json.dumps(actual,indent=2)+'\n')
    (out/'actual_adaptation_landings.json').write_text(json.dumps(pad_records,indent=2)+'\n')
    (out/'new_controlled_external_IO_policy.json').write_text(json.dumps({'scope':'NEW_CONTROLLED_PARENT_TARGET_POLICY_NOT_HISTORICAL_HANDOFF',
      'historical_target_layers':'PARTIAL_OR_UNKNOWN','original_leaf_pin_layers_unchanged':True,
      'external_IO_count':len(topnames),'external_IO_layers':['metal5','metal6'],'pitch_um':pitch,
      'placement_policy':'Nearest available legal-grid perimeter slot to connected resource centers, same topology/centers for Aopt and C; detailed DRC pending',
      'same_policy_for_Aopt_C':True,'construction_ports_must_be_lowered_before_freeze':True},indent=2)+'\n')
    return commands


def run(scheme,revision):
    assert int(os.environ['SLURM_CPUS_PER_TASK'])>=16
    assert scheme in ['Aopt','C'];out=ROOT/'common_integration'/revision/scheme;out.mkdir(parents=True,exist_ok=False)
    inputs=ROOT/'inputs/common-topology-r02';prep=ROOT/'inputs/common-base-preparation-r04'
    assert prep.exists(),str(prep)
    plan=json.loads((prep/'preparation_contract.json').read_text());assert not plan['frozen']
    assert json.loads((inputs/'topology_proof.json').read_text())['all_original_signal_pins']==24767
    assert json.loads((inputs/'topology_proof.json').read_text())['source_preparation_SHA']==sha(prep/'preparation_contract.json')
    common=['singularity','exec','--cleanenv','--bind',str(ROOT/'tmp')+':/tmp','--home',str(ROOT/'home'),'--pwd',str(out)]
    rec={'scope':'UNQUALIFIED_SIX_RESOURCE_ACTUAL_COMMON_INTEGRATION_TRIAL_NOT_FROZEN_BASE',
      'scheme':scheme,'unqualified_integration_trial':True,'full_qualification':False,'frozen':False,
      'two_complete_M11_M12_functions':'NOT_IMPLEMENTED','construction_port_lowering':'NOT_YET_EXECUTED',
      'historical_targets':'PARTIAL_OR_UNKNOWN; new controlled policy separately indexed',
      'views':{},'source_SHA':{},'scheduler_job':os.environ['SLURM_JOB_ID'],
      'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    try:
        tech=ROOT/'upper_layer_probe/r01/model/research12.tech.lef';model=json.loads((tech.parent/'model.json').read_text())
        assert model['original_M1_M10_and_via1_via9_layer_blocks_identical'] and sha(tech)==model['files'][tech.name]['sha256']
        lines=['read_lef '+tcl(tech),'read_lef /OpenROAD-flow-scripts/flow/platforms/nangate45/lef/NangateOpenCellLibrary.macro.mod.lef',
               'read_liberty /OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib'];liblines=lines[-1:]
        for case in CASES:
            v=source_view(case,scheme);folder=v['directory'];detail=folder/'detailed.lef'
            if not detail.exists():
                detail=out/(case+'.actual_detail.lef');script=out/(case+'.export.tcl')
                script.write_text('read_db '+tcl(v['ODB'])+'\nwrite_abstract_lef -bloat_factor 0 '+tcl(detail)+'\n')
                assert execute(common,script,out/(case+'.export.log'),threads=1)==0
            contract=verify(folder/'abstract.lef',detail)
            master=None
            with (folder/'abstract.lef').open() as f:
                for line in f:
                    m=re.match(r'^MACRO\s+(\S+)',line)
                    if m:master=m[1];break
            assert master;alias='p126_'+case;dest=out/(alias+'.lef');alias_stream(detail,dest,master,alias)
            text=v['model'].read_text();text,n=re.subn(r'cell\s*\(\s*"?'+re.escape(master)+r'"?\s*\)','cell ("'+alias+'")',text);assert n==1
            lib=out/(alias+'.lib');lib.write_text(text);lines+=['read_lef '+tcl(dest),'read_liberty '+tcl(lib)];liblines+=['read_liberty '+tcl(lib)]
            rec['views'][case]={'source_physical':str(folder),'receipt_SHA':sha(v['receipt']),'source_ODB_SHA':sha(v['ODB']),
              'model_SHA':sha(v['model']),'model_receipt_SHA':sha(v['model_receipt']),'inherited_native_DRC':v['native_DRC'],
              'alias_LEF_SHA':sha(dest),'alias_model_SHA':sha(lib),'OBS_contract':contract,'full_qualification':False}
            for p in [v['receipt'],v['ODB'],v['model'],v['model_receipt']]:rec['source_SHA'][str(p)]=sha(p)
        rec['source_SHA'].update({str(p):sha(p) for p in [tech,prep/'preparation_contract.json',prep/'shared_prewire_geometry.csv']+list(p for p in inputs.iterdir() if p.is_file())})
        helpers=(DRIVER/'parent_trial.tcl').read_text().split('if {![stage load {',1)[0]
        place_helpers=helpers.replace('$out/stages.tsv','$out/placement_PG_stages.tsv')
        lines=[place_helpers]+lines+['read_verilog '+tcl(inputs/'base_construction.v'),'link_design hpy_common_base_construction',
          'initialize_floorplan -die_area {'+' '.join(map(str,plan['frame_um']))+'} -core_area {10 10 '+str(plan['frame_um'][2]-10)+' '+str(plan['frame_um'][3]-10)+'} -site FreePDK45_38x28_10R_NP_162NW_34O','make_tracks']
        for m in plan['instances']:lines+=['place_macro -macro_name '+tcl(m['instance'])+' -location {'+str(m['x_um'])+' '+str(m['y_um'])+'} -orientation R0 -exact']
        lines+=['cut_rows -halo_width_x 2 -halo_width_y 2',
          'set b [ord::get_db_block];set row [lindex [$b getRows] 0];lassign [$row getOrigin] ix iy;set sw [[$row getSite] getWidth];foreach i [$b getInsts] {if {[[$i getMaster] getType] eq "BLOCK"} {continue};$i setOrient R0;$i setLocation $ix $iy;$i setPlacementStatus FIRM;set ix [expr {$ix+int(ceil(double([[$i getMaster] getWidth])/$sw))*$sw+4*$sw}]}',
          'if {![stage placement {check_placement -verbose;parent_contract '+tcl(out/'placed')+'}]} {close $stages;exit 1}',
          'add_global_connection -net VDD -inst_pattern {.*} -pin_pattern {^VDD$} -power',
          'add_global_connection -net VSS -inst_pattern {.*} -pin_pattern {^VSS$} -ground','global_connect',
          'set_voltage_domain -name CORE -power VDD -ground VSS','define_pdn_grid -name common_grid -voltage_domains CORE -pins metal10',
          'add_pdn_stripe -grid common_grid -layer metal1 -width 0.17 -pitch 2.4 -offset 0 -followpins',
          'add_pdn_stripe -grid common_grid -layer metal4 -width 0.48 -pitch 56 -offset 2',
          'add_pdn_stripe -grid common_grid -layer metal7 -width 1.40 -pitch 30 -offset 2',
          'add_pdn_stripe -grid common_grid -layer metal10 -width 1.40 -pitch 30 -offset 2',
          'add_pdn_connect -grid common_grid -layers {metal1 metal4}','add_pdn_connect -grid common_grid -layers {metal4 metal7}',
          'add_pdn_connect -grid common_grid -layers {metal7 metal10}']
        for i,m in enumerate(plan['instances']):lines+=['define_pdn_grid -name macro_'+str(i)+' -voltage_domains CORE -macro -instances '+tcl(m['instance'])+' -grid_over_pg_pins -halo {2 2 2 2}','add_pdn_connect -grid macro_'+str(i)+' -layers {metal7 metal10}']
        lines+=['if {![stage PDN_build {pdngen -failed_via_report '+tcl(out/'failed_vias.rpt')+';set llhd_macro_instances {'+' '.join(m['instance'] for m in plan['instances'])+'};source '+tcl(DRIVER/'filter_parent_pg.tcl')+'}]} {catch {write_db '+tcl(out/'failed_PDN.odb')+'};close $stages;exit 1}',
          'set f [open '+tcl(out/'actual_M10_obstacles.tsv')+' w];puts $f "kind\\tx0\\ty0\\tx1\\ty1";foreach i [$b getInsts] {if {[[$i getMaster] getType] ne "BLOCK"} {continue};lassign [$i getLocation] dx dy;foreach ob [[$i getMaster] getObstructions] {if {[[$ob getTechLayer] getName] eq "metal10"} {puts $f [join [list OBS [expr {[$ob xMin]+$dx}] [expr {[$ob yMin]+$dy}] [expr {[$ob xMax]+$dx}] [expr {[$ob yMax]+$dy}]] "\\t"]}}}',
          'foreach n [$b getNets] {foreach s [$n getSWires] {foreach r [$s getWires] {if {[$r isVia]} {set v [$r getTechVia];if {$v eq "NULL"} {set v [$r getBlockVia]};lassign [$r getViaXY] x y;foreach a [$v getBoxes] {if {[[$a getTechLayer] getName] eq "metal10"} {puts $f [join [list PGVIA [expr {[$a xMin]+$x}] [expr {[$a yMin]+$y}] [expr {[$a xMax]+$x}] [expr {[$a yMax]+$y}]] "\\t"]}}} elseif {[[$r getTechLayer] getName] eq "metal10"} {puts $f [join [list PG [$r xMin] [$r yMin] [$r xMax] [$r yMax]] "\\t"]}}}};close $f',
          'set f [open '+tcl(out/'native_pin_boxes.tsv')+' w];puts $f "instance\\tpin\\tnet\\tlayer\\tx0\\ty0\\tx1\\ty1";foreach i [$b getInsts] {foreach it [$i getITerms] {if {[$it getSigType] in {POWER GROUND}} {continue};foreach g [$it getGeometries] {set ly [lindex $g 0];set r [lindex $g 1];puts $f [join [list [$i getName] [[$it getMTerm] getName] [[$it getNet] getName] [$ly getName] [$r xMin] [$r yMin] [$r xMax] [$r yMax]] "\\t"]}}};close $f',
          'write_db '+tcl(out/'placed_PG_NOT_FROZEN.odb'),
          'set p [stage PDN_VDD {check_power_grid -net VDD -error_file '+tcl(out/'VDD.rpt')+'}];set q [stage PDN_VSS {check_power_grid -net VSS -error_file '+tcl(out/'VSS.rpt')+'}];close $stages;if {!$p || !$q} {exit 1}']
        script=out/'place_PG.tcl';script.write_text('\n'.join(lines)+'\n')
        env='PINXY_PARENT_OUT='+str(out)
        rec['placement_PG_returncode']=execute(common,script,out/'place_PG.log',env,threads=16)
        if rec['placement_PG_returncode']!=0:raise RuntimeError('Actual placement/PDN failed; checkpoint and original rules retained')
        verify_graph(inputs,out/'placed.endpoints.tsv',out/'placed_graph_check.json')
        padcommands=screen_pads(out,prep,inputs)
        shared=json.loads((out/'actual_shared_conductors.json').read_text())
        routed=[helpers,SHARED_SNAPSHOT,'set common_shared_pads {'+' '.join(q['construction_pad'] for q in shared)+'}']+liblines+['read_db '+tcl(out/'placed_PG_NOT_FROZEN.odb'),'set b [ord::get_db_block];set m10 [[ord::get_db_tech] findLayer metal10]']+padcommands
        routed+=['common_shared_snapshot '+tcl(out/'before.shared.tsv'),
          'parent_contract '+tcl(out/'before_route'),'write_db '+tcl(out/'fixed_prewires_NOT_FROZEN.odb'),
          'set_routing_layers -signal metal2-metal10 -clock metal4-metal10',
          'if {![stage lower_global_route {global_route -guide_file '+tcl(out/'route.guide')+' -congestion_report_file '+tcl(out/'congestion.rpt')+'}]} {catch {write_db '+tcl(out/'failed_global.odb')+'};close $stages;exit 1}',
          'write_db '+tcl(out/'global.odb'),
          'if {![stage lower_detailed_route {detailed_route -output_drc '+tcl(out/'route.drc')+' -verbose 1;write_db '+tcl(out/'routed_NOT_FROZEN.odb')+'}]} {close $stages;exit 1}',
          'common_shared_snapshot '+tcl(out/'after.shared.tsv'),
          'parent_contract '+tcl(out/'after_route'),'source '+tcl(DRIVER/'export_access.tcl'),
          'report_wire_length -detailed_route -summary -file '+tcl(out/'wire_length.csv'),
          'stage final_VDD {check_power_grid -net VDD -error_file '+tcl(out/'final_VDD.rpt')+'}',
          'stage final_VSS {check_power_grid -net VSS -error_file '+tcl(out/'final_VSS.rpt')+'}','close $stages']
        script=out/'lower_route.tcl';script.write_text('\n'.join(routed)+'\n')
        rec['lower_route_returncode']=execute(common,script,out/'lower_route.log',env+',PINXY_ACCESS_ALL=1,PINXY_ACCESS_OUT='+str(out/'whole_access.tsv.gz'),threads=16)
        if (out/'before.shared.tsv').exists():
            actual=rows(out/'before.shared.tsv');expected={q['construction_pad']:q for q in shared}
            assert len(actual)==len(expected)==256
            for q in actual:
                p=expected[q['pad']];assert q['layer']=='metal10'
                assert all(int(q[k])==round(p[k+'_um']*2000) for k in ['x0','y0','x1','y1'])
            rec['actual_shared_fixed_M10_conductors']=256;rec['actual_shared_centerline_length_um']=8192.
            rec['shared_topology_and_budget_unchanged']=True
        if (out/'after.shared.tsv').exists():
            rec['shared_conductors_geometry_and_networks_exactly_preserved_through_DRT']=sha(out/'before.shared.tsv')==sha(out/'after.shared.tsv')
            rec['parent_invariants']={k:sha(out/('before_route.'+k+'.tsv'))==sha(out/('after_route.'+k+'.tsv')) for k in ['pins','pdn','instances']}
        if (out/'routed_NOT_FROZEN.odb').exists():
            fresh=out/'fresh.tcl';fresh.write_text('read_db '+tcl(out/'routed_NOT_FROZEN.odb')+'\nset_routing_layers -signal metal2-metal10 -clock metal4-metal10\ndrt::check_drc -output_file '+tcl(out/'independent.drc')+'\n')
            rec['fresh_DRC_returncode']=execute(common,fresh,out/'independent.log',threads=4)
            if rec['fresh_DRC_returncode']==0:rec['fresh_DRC_count']=len(re.findall(r'^violation type:',(out/'independent.drc').read_text(),re.M))
        if (out/'whole_access.tsv.gz').exists():rec['whole_signal_geometry']=check(out/'whole_access.tsv.gz',True)
        if (out/'after_route.endpoints.tsv').exists():verify_graph(inputs,out/'after_route.endpoints.tsv',out/'routed_graph_check.json')
        rec['status']='ACTUAL_LOWER_INTEGRATION_EXECUTED_READ_FAILURE_LEDGER_NOT_QUALIFIED'
    except Exception:
        rec['status']='ACTUAL_COMMON_INTEGRATION_FAILED_OR_INCOMPLETE_NOT_FROZEN';rec['actual_failure']=traceback.format_exc();traceback.print_exc()
    rec['all_sources_unchanged']=all(sha(Path(p))==v for p,v in rec['source_SHA'].items())
    rec['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    rec['files']={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in out.iterdir() if p.is_file()}
    (out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n');print(rec['status'],flush=True)
    return 0 if rec.get('lower_route_returncode')==0 and rec.get('fresh_DRC_count')==0 and rec['all_sources_unchanged'] else 1


if __name__=='__main__':sys.exit(run(*sys.argv[1:3]))
