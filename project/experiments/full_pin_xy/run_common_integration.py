"""Actual six-resource lower-layer integration trial, explicitly NOT a qualified base.

Reuse the compiled full bit graph and finite 256-conductor topology. Matching
real extracted leaf views are required, including the explicitly failed four-
DRC LL SYSTEM diagnostic source. No routing-only capacitance stubs are used.
Construction access ports remain until a separately verified mode lowering;
this trial cannot be frozen or called a complete functional implementation.
"""
from pathlib import Path
from collections import Counter
import csv,datetime,json,math,os,re,subprocess,sys,traceback
from run_exports import ROOT,sha
from run_parent_trial import tcl
from run_escape_fixture import execute
from lef_view_contract import verify,parse as parse_lef
from verify_common_native import verify as verify_graph
from check_access import check

DRIVER=Path(__file__).resolve().parent
CASES=['act','mxu','opentpu_aux','gemm','vector','llaccel_aux']
COUNTS={'act':860,'mxu':2172,'opentpu_aux':2229,'gemm':3753,'vector':2246,'llaccel_aux':13507}
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


def source_view(case,scheme,source_profile='original'):
    assert source_profile in ['original','latest_access_tips','deadline_current','matched_perimeter']
    if source_profile=='matched_perimeter':
        from matched_perimeter_source import select
        return select(case,scheme,source_view)
    if source_profile=='deadline_current':
        assert scheme=='C'
        expected=json.loads((DRIVER/'deadline_current_sources.json').read_text())[case]
        if case=='act':
            value=source_view(case,scheme,'original');assert sha(value['ODB'])==expected['ODB_SHA256'];value['source_profile']=source_profile;return value
        paths={'mxu':'mxu_actual_tip_views/r01/mxu-C','opentpu_aux':'system_stacked_via_views/r01/opentpu_aux-C','gemm':'diode_views/r01/gemm-C','vector':'vector_current_views/r01/vector-C','llaccel_aux':'llsys_owned_restored_views/r01/llaccel_aux-C'}
        folder=ROOT/paths[case];rp=folder/'execution.json';current=json.loads(rp.read_text())
        assert current.get('completed_utc') and current['native_export_returncode']==current['fresh_model_read_returncode']==0
        assert current['source_native_DRC']==0 and current['matching_all_signal_model_pins']==COUNTS[case] and current['SPEF_replay_matches_source']
        assert current['all_sources_and_pre_RCX_geometry_unchanged'] and current['all_original_signal_and_PG_pins_and_size_exactly_preserved']
        assert current['source_geometry_sha256']==expected['ODB_SHA256']
        for name in ['clean.odb','abstract.lef','detailed.lef','timing.lib','pins.tsv']:assert sha(folder/name)==current['files'][name]['sha256']
        old=source_view(case,scheme,'original');a,b=parse_lef(old['directory']/'abstract.lef'),parse_lef(folder/'abstract.lef')
        assert a[0]==b[0] and set(a[1])==set(b[1]);changes=[]
        for name in a[1]:
            x,y=a[1][name],b[1][name]
            assert [v for v in x if not v.startswith('RECT ')]==[v for v in y if not v.startswith('RECT ')],(case,name,'Pin layer/function/direction/USE changed')
            if x!=y:
                assert not any(v in x for v in ['USE POWER ;','USE GROUND ;'])
                for lines in [x,y]:
                    boxes=[list(map(float,v.split()[1:5])) for v in lines if v.startswith('RECT ')];assert len(boxes)==1
                    assert abs(boxes[0][2]-boxes[0][0]-.14)<1e-7 and abs(boxes[0][3]-boxes[0][1]-.14)<1e-7
                changes.append(name)
        return {'directory':folder,'receipt':rp,'ODB':folder/'clean.odb','model':folder/'timing.lib','model_receipt':rp,'native_DRC':0,'complete_rules':'NOT_QUALIFIED','RTL_equivalence':'NOT_EXECUTED','source_profile':source_profile,'actual_pin_XY_changes_against_original_common_source':changes,'all_original_pin_function_direction_use_layer_size_and_PG_preserved':True,'source_view_export_job':current['scheduler_job']}
    if source_profile=='latest_access_tips' and case in ['mxu','llaccel_aux']:
        assert scheme=='C'
        relative={'mxu':'mxu_actual_tip_views/r01/mxu-C','llaccel_aux':'llsys_parent_tip_views/r01/llaccel_aux-C'}[case]
        folder=ROOT/relative;p=folder/'execution.json';q=json.loads(p.read_text())
        assert q.get('completed_utc') and q['native_export_returncode']==q['fresh_model_read_returncode']==0
        assert q['source_native_DRC']==0 and q['matching_all_signal_model_pins']==COUNTS[case]
        assert q['all_original_signal_and_PG_pins_and_size_exactly_preserved'] and q['SPEF_replay_matches_source'] and q['all_sources_and_pre_RCX_geometry_unchanged']
        for name in ['clean.odb','abstract.lef','detailed.lef','timing.lib','pins.tsv']:
            assert sha(folder/name)==q['files'][name]['sha256']
        assert sha(folder/'clean.odb')==q['source_geometry_sha256']
        old=source_view(case,scheme,'original');a,b=parse_lef(old['directory']/'abstract.lef'),parse_lef(folder/'abstract.lef')
        assert a[0]==b[0] and set(a[1])==set(b[1])
        changed=[]
        for name in a[1]:
            x,y=a[1][name],b[1][name]
            assert [s for s in x if not s.startswith('RECT ')]==[s for s in y if not s.startswith('RECT ')],(case,name,'Pin function/direction/use/layer changed')
            if x==y:continue
            assert not any(s in x for s in ['USE POWER ;','USE GROUND ;']),(case,name,'Original PG changed')
            r=[list(map(float,s.split()[1:5])) for s in x if s.startswith('RECT ')]
            t=[list(map(float,s.split()[1:5])) for s in y if s.startswith('RECT ')]
            assert len(r)==len(t)==1
            assert all(abs(v-.14)<1e-7 for z in [r[0],t[0]] for v in [z[2]-z[0],z[3]-z[1]])
            changed.append(name.replace('\\',''))
        assert changed,(case,'No actual pin correction against previous common source')
        return {'directory':folder,'receipt':p,'ODB':folder/'clean.odb','model':folder/'timing.lib','model_receipt':p,
          'native_DRC':0,'complete_rules':'NOT_QUALIFIED','RTL_equivalence':'NOT_EXECUTED',
          'source_profile':source_profile,'old_common_source_receipt':old['receipt'],
          'old_common_source_ODB':old['ODB'],'actual_pin_XY_changes_against_original_common_source':changed,
          'all_original_pin_function_direction_use_layer_size_and_PG_preserved':True}
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


def actual_boundary_pins(path,case,scheme):
    size,pins,_=parse_lef(path);parts=size.split();width,height=float(parts[1]),float(parts[3]);result=[]
    for name,lines in pins.items():
        if any(s in lines for s in ['USE POWER ;','USE GROUND ;']):continue
        layer=None;rectangles=[];direction=None;use=None
        for line in lines:
            if line.startswith('LAYER '):layer=line.split()[1]
            elif line.startswith('DIRECTION '):direction=line.split()[1]
            elif line.startswith('USE '):use=line.split()[1]
            elif line.startswith('RECT '):rectangles.append((layer,list(map(float,line.split()[1:5]))))
        assert len(rectangles)==1,(case,name,'Unexpected original signal pin shape')
        layer,box=rectangles[0];assert layer in ['metal5','metal6']
        x0,y0,x1,y1=box
        edge=min(abs(x0),abs(y0),abs(width-x1),abs(height-y1))<=.0050001
        if scheme=='Aopt':assert edge,(case,name,'Optimized-perimeter baseline contains interior pin')
        result.append({'case':case,'scheme':scheme,'pin':name.replace('\\',''),'direction':direction,'use':use,'layer':layer,
          'x0_um':x0,'y0_um':y0,'x1_um':x1,'y1_um':y1,'touches_block_edge_within_5nm':edge})
    assert len(result)==COUNTS[case] and len({r['pin'] for r in result})==len(result)
    return result


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
        for i in range(int((width-2*inset)/pitch)):boundary.append((.07+round((inset+i*pitch-.07)/.28)*.28,y,'metal6'))
    for x in [inset,width-inset]:
        for i in range(int((height-2*inset)/pitch)):boundary.append((x,.07+round((inset+i*pitch-.07)/.28)*.28,'metal5'))
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


def run(scheme,revision,route_engine='FastRoute',source_profile='original'):
    assert route_engine in ['FastRoute','CuGR'];native_threads=8 if route_engine=='CuGR' else 16
    assert int(os.environ['SLURM_CPUS_PER_TASK'])>=native_threads
    assert scheme in ['Aopt','C'] and source_profile in ['original','latest_access_tips','deadline_current','matched_perimeter']
    assert source_profile=='original' or scheme==('Aopt' if source_profile=='matched_perimeter' else 'C')
    out=ROOT/'common_integration'/revision/scheme;out.mkdir(parents=True,exist_ok=False)
    inputs=ROOT/'inputs/common-topology-r02';prep=ROOT/'inputs/common-base-preparation-r04'
    assert prep.exists(),str(prep)
    plan=json.loads((prep/'preparation_contract.json').read_text());assert not plan['frozen']
    assert json.loads((inputs/'topology_proof.json').read_text())['all_original_signal_pins']==24767
    assert json.loads((inputs/'topology_proof.json').read_text())['source_preparation_SHA']==sha(prep/'preparation_contract.json')
    common=['singularity','exec','--cleanenv','--bind',str(ROOT/'tmp')+':/tmp','--home',str(ROOT/'home'),'--pwd',str(out)]
    rec={'scope':'UNQUALIFIED_SIX_RESOURCE_ACTUAL_COMMON_INTEGRATION_TRIAL_NOT_FROZEN_BASE',
      'scheme':scheme,'source_profile':source_profile,'unqualified_integration_trial':True,'full_qualification':False,'frozen':False,
      'two_complete_M11_M12_functions':'NOT_IMPLEMENTED','construction_port_lowering':'NOT_YET_EXECUTED',
      'historical_targets':'PARTIAL_OR_UNKNOWN; new controlled policy separately indexed',
      'views':{},'source_SHA':{},'scheduler_job':os.environ['SLURM_JOB_ID'],
      'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    rec.update({'global_route_engine':route_engine,'native_threads':native_threads,
      'shared_BPin_container_compatibility_fix_before_routing':route_engine=='CuGR',
      'same_compiled_topology_resource_instances_frame_and_preconnect_budget':True,
      'fairness_limit':'Early integration trial. Original selected Aopt/C leaf epochs and all differing ECO/STA/rule costs remain separately indexed; not final pure-XY PPA or system comparison.'})
    try:
        source_pin_rows=[];low_envelopes=[]
        tech=ROOT/'upper_layer_probe/r01/model/research12.tech.lef';model=json.loads((tech.parent/'model.json').read_text())
        assert model['original_M1_M10_and_via1_via9_layer_blocks_identical'] and sha(tech)==model['files'][tech.name]['sha256']
        lines=['read_lef '+tcl(tech),'read_lef /OpenROAD-flow-scripts/flow/platforms/nangate45/lef/NangateOpenCellLibrary.macro.mod.lef',
               'read_liberty /OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib'];liblines=lines[-1:]
        for case in CASES:
            v=source_view(case,scheme,source_profile);folder=v['directory'];detail=folder/'detailed.lef'
            if not detail.exists():
                detail=out/(case+'.actual_detail.lef');script=out/(case+'.export.tcl')
                script.write_text('read_db '+tcl(v['ODB'])+'\nwrite_abstract_lef -bloat_factor 0 '+tcl(detail)+'\n')
                assert execute(common,script,out/(case+'.export.log'),threads=1)==0
            contract=verify(folder/'abstract.lef',detail)
            source_pin_rows+=actual_boundary_pins(folder/'abstract.lef',case,scheme)
            master=None
            with (folder/'abstract.lef').open() as f:
                for line in f:
                    m=re.match(r'^MACRO\s+(\S+)',line)
                    if m:master=m[1];break
            assert master;alias='p126_'+case;dest=out/(alias+'.lef')
            parent_detail=detail
            if source_profile=='matched_perimeter':
                from coarsen_parent_low_obs import coarsen
                parent_detail=out/(case+'.parent_low.lef')
                abstraction=coarsen(detail,parent_detail,requested=('metal1','metal2','metal3'))
                for ly,box in abstraction['original_OBS_envelope_DBU'].items():
                    low_envelopes.append(('u_'+case,ly)+tuple(box))
                rec.setdefault('parent_low_OBS',{})[case]=abstraction
                for p in [v['resource_match_inventory']]:rec['source_SHA'][str(p)]=sha(p)
            alias_stream(parent_detail,dest,master,alias)
            text=v['model'].read_text();text,n=re.subn(r'cell\s*\(\s*"?'+re.escape(master)+r'"?\s*\)','cell ("'+alias+'")',text);assert n==1
            lib=out/(alias+'.lib');lib.write_text(text);lines+=['read_lef '+tcl(dest),'read_liberty '+tcl(lib)];liblines+=['read_liberty '+tcl(lib)]
            leaf_receipt=json.loads(v['receipt'].read_text())
            rec['views'][case]={'source_physical':str(folder),'receipt_SHA':sha(v['receipt']),'source_ODB_SHA':sha(v['ODB']),
              'model_SHA':sha(v['model']),'model_receipt_SHA':sha(v['model_receipt']),'inherited_native_DRC':v['native_DRC'],
              'alias_LEF_SHA':sha(dest),'alias_model_SHA':sha(lib),'OBS_contract':contract,'full_qualification':False,
              'inherited_separate_cell_ECO_cost':leaf_receipt.get('separate_cell_ECO_cost'),
              'current_658_M6_tip_SYSTEM_bit1025_sources_not_selected_here':source_profile=='original',
              'actual_tip_source_selected':v.get('source_profile')=='latest_access_tips',
              'actual_pin_XY_changes_against_original_common_source':v.get('actual_pin_XY_changes_against_original_common_source',[]),
              'unselected_newer_sources':'GEMM658 and openTPU stacked-via source not selected in this access-only integration'}
            for p in [v['receipt'],v['ODB'],v['model'],v['model_receipt'],folder/'abstract.lef',detail]:rec['source_SHA'][str(p)]=sha(p)
            for key in ['old_common_source_receipt','old_common_source_ODB']:
                if key in v:rec['source_SHA'][str(v[key])]=sha(v[key])
        assert len(source_pin_rows)==24767
        with (out/'all24767_actual_source_pins.csv').open('w',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=list(source_pin_rows[0]),lineterminator='\n');writer.writeheader();writer.writerows(source_pin_rows)
        rec['actual_source_signal_pin_coverage']={'all_signal_pins':len(source_pin_rows),
          'all_on_block_edges':all(r['touches_block_edge_within_5nm'] for r in source_pin_rows),
          'per_block':dict(Counter(r['case'] for r in source_pin_rows)),'geometry_source':'Actual source LEFs, not names or report colors'}
        if source_profile=='matched_perimeter':
            assert rec['actual_source_signal_pin_coverage']['all_on_block_edges']
            rec['fairness_limit']='All six Aopt sources match selected C cells/connections/poses/PG/die/SDC; unchanged topology/placement/frame/256-conductor budget. Actual common routing still a trial; not two complete functions or qualified PPA.'
        rec['source_SHA'].update({str(p):sha(p) for p in [tech,prep/'preparation_contract.json',prep/'shared_prewire_geometry.csv']+list(p for p in inputs.iterdir() if p.is_file())})
        helpers=(DRIVER/'parent_trial.tcl').read_text().split('if {![stage load {',1)[0]
        place_helpers=helpers.replace('$out/stages.tsv','$out/placement_PG_stages.tsv')
        lines=[place_helpers]+lines+['read_verilog '+tcl(inputs/'base_construction.v'),'link_design hpy_common_base_construction',
          'initialize_floorplan -die_area {'+' '.join(map(str,plan['frame_um']))+'} -core_area {10 10 '+str(plan['frame_um'][2]-10)+' '+str(plan['frame_um'][3]-10)+'} -site FreePDK45_38x28_10R_NP_162NW_34O','make_tracks']
        for m in plan['instances']:lines+=['place_macro -macro_name '+tcl(m['instance'])+' -location {'+str(m['x_um'])+' '+str(m['y_um'])+'} -orientation R0 -exact']
        lines+=['cut_rows -halo_width_x 2 -halo_width_y 2',
          'set b [ord::get_db_block];set row [lindex [$b getRows] 0];lassign [$row getOrigin] ix iy;set sw [[$row getSite] getWidth];foreach i [$b getInsts] {if {[[$i getMaster] getType] eq "BLOCK"} {continue};$i setOrient [$row getOrient];$i setLocation $ix $iy;$i setPlacementStatus FIRM;set ix [expr {$ix+int(ceil(double([[$i getMaster] getWidth])/$sw))*$sw+4*$sw}]}',
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
        rec['placement_PG_returncode']=execute(common,script,out/'place_PG.log',env,threads=native_threads)
        if rec['placement_PG_returncode']!=0:raise RuntimeError('Actual placement/PDN failed; checkpoint and original rules retained')
        if source_profile=='matched_perimeter':
            audit=DRIVER/'check_parent_low_obs_pg.tcl';rec['source_SHA'][str(audit)]=sha(audit)
            body='read_db '+tcl(out/'placed_PG_NOT_FROZEN.odb')+'\nset conservative_low_obstruction_envelopes {'+' '.join('{'+tcl(e[0])+' '+tcl(e[1])+' '+' '.join(map(str,e[2:]))+'}' for e in low_envelopes)+'}\nsource '+tcl(audit)+'\nclose $stages\n'
            script=out/'PG_OBS.tcl';script.write_text(place_helpers.replace('placement_PG_stages.tsv','PG_OBS_stages.tsv')+'\n'+body)
            rec['actual_parent_PG_conservative_OBS_returncode']=execute(common,script,out/'PG_OBS.log',env,threads=1)
            assert rec['actual_parent_PG_conservative_OBS_returncode']==0
        verify_graph(inputs,out/'placed.endpoints.tsv',out/'placed_graph_check.json')
        padcommands=screen_pads(out,prep,inputs)
        shared=json.loads((out/'actual_shared_conductors.json').read_text())
        routed=[helpers,SHARED_SNAPSHOT,'set common_shared_pads {'+' '.join(q['construction_pad'] for q in shared)+'}']+liblines+['read_db '+tcl(out/'placed_PG_NOT_FROZEN.odb'),'set b [ord::get_db_block];set m10 [[ord::get_db_tech] findLayer metal10]']+padcommands
        if route_engine=='CuGR':
            routed+=['parent_contract '+tcl(out/'before_BPin_container_fix'),
              'if {![stage shared_construction_BPin_containers {set count 0;foreach pad $common_shared_pads {set bt [$b findBTerm $pad];if {$bt eq "NULL"} {error "Missing original construction pad"};set bps [$bt getBPins];if {[llength $bps]!=2} {error "Not the expected two-BPin case"};set keep [lindex $bps 0];set drop [lindex $bps 1];if {[llength [$keep getBoxes]]!=1 || [llength [$drop getBoxes]]!=1} {error "Unexpected original boxes"};set box [lindex [$drop getBoxes] 0];odb::dbBox_create $keep [$box getTechLayer] [$box xMin] [$box yMin] [$box xMax] [$box yMax];odb::dbBPin_destroy $drop;if {[llength [$bt getBPins]]!=1 || [llength [$keep getBoxes]]!=2} {error "BPin regrouping failed"};incr count};if {$count!=256} {error "Incomplete fixed-conductor coverage"}}]} {close $stages;exit 1}']
        routed+=['common_shared_snapshot '+tcl(out/'before.shared.tsv'),
          'parent_contract '+tcl(out/'before_route'),'write_db '+tcl(out/'fixed_prewires_NOT_FROZEN.odb'),
          'set_routing_layers -signal metal2-metal10 -clock metal4-metal10',
          'if {![stage lower_global_route {global_route '+('-use_cugr -verbose ' if route_engine=='CuGR' else '')+'-guide_file '+tcl(out/'route.guide')+' -congestion_report_file '+tcl(out/'congestion.rpt')+'}]} {catch {write_db '+tcl(out/'failed_global.odb')+'};close $stages;exit 1}',
          'write_db '+tcl(out/'global.odb'),
          'if {![stage lower_detailed_route {detailed_route -output_drc '+tcl(out/'route.drc')+' -verbose 1;write_db '+tcl(out/'routed_NOT_FROZEN.odb')+';write_def '+tcl(out/'routed.def')+'}]} {close $stages;exit 1}',
          'common_shared_snapshot '+tcl(out/'after.shared.tsv'),
          'parent_contract '+tcl(out/'after_route'),'source '+tcl(DRIVER/'export_access.tcl'),
          'report_wire_length -detailed_route -summary -file '+tcl(out/'wire_length.csv'),
          'stage final_VDD {check_power_grid -net VDD -error_file '+tcl(out/'final_VDD.rpt')+'}',
          'stage final_VSS {check_power_grid -net VSS -error_file '+tcl(out/'final_VSS.rpt')+'}','close $stages']
        script=out/'lower_route.tcl';script.write_text('\n'.join(routed)+'\n')
        rec['lower_route_returncode']=execute(common,script,out/'lower_route.log',env+',PINXY_ACCESS_ALL=1,PINXY_ACCESS_OUT='+str(out/'whole_access.tsv.gz'),threads=native_threads)
        if route_engine=='CuGR' and (out/'before_route.pins.tsv').exists():
            a=(out/'before_BPin_container_fix.pins.tsv').read_text().splitlines();b=(out/'before_route.pins.tsv').read_text().splitlines()
            rec['flat_pin_geometry_exact_multiset_preserved_by_BPin_regrouping']=Counter(a)==Counter(b)
            assert rec['flat_pin_geometry_exact_multiset_preserved_by_BPin_regrouping']
            assert all(sha(out/('before_BPin_container_fix.'+k+'.tsv'))==sha(out/('before_route.'+k+'.tsv')) for k in ['pdn','instances'])
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
        if (out/'routed.def').exists():
            rec['all_256_native_FIXED_status_paths_retained']=len(re.findall(r'\+\s+FIXED\s+metal10\b',(out/'routed.def').read_text()))==256
            assert rec['all_256_native_FIXED_status_paths_retained']
        if (out/'stages.tsv').exists():
            with (out/'stages.tsv').open() as f:rec['native_final_stage_status']={r['stage']:r['status'] for r in csv.DictReader(f,delimiter='\t')}
        rec['status']='ACTUAL_LOWER_INTEGRATION_EXECUTED_READ_FAILURE_LEDGER_NOT_QUALIFIED'
    except Exception:
        rec['status']='ACTUAL_COMMON_INTEGRATION_FAILED_OR_INCOMPLETE_NOT_FROZEN';rec['actual_failure']=traceback.format_exc();traceback.print_exc()
    rec['all_sources_unchanged']=all(sha(Path(p))==v for p,v in rec['source_SHA'].items())
    rec['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    rec['files']={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in out.iterdir() if p.is_file()}
    (out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n');print(rec['status'],flush=True)
    return 0 if rec.get('lower_route_returncode')==0 and rec.get('fresh_DRC_count')==0 and rec['all_sources_unchanged'] and rec.get('whole_signal_geometry',{}).get('pass') and rec.get('shared_conductors_geometry_and_networks_exactly_preserved_through_DRT') and rec.get('all_256_native_FIXED_status_paths_retained') and all(rec.get('parent_invariants',{}).get(k) for k in ['pins','pdn','instances']) and all(rec.get('native_final_stage_status',{}).get(k)=='EXECUTED' for k in ['final_VDD','final_VSS']) else 1


if __name__=='__main__':sys.exit(run(*sys.argv[1:5]))
